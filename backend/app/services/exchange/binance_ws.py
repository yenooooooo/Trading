"""
바이낸스 선물 WebSocket 매니저
- markPrice@1s: 실시간 마크 가격 + 펀딩비
- kline_{interval}: 캔들 스트림
- userData: 포지션/주문 업데이트 (listenKey)
- 자동 재연결 (3초 간격, 최대 5회)
- ping/pong 30초 하트비트
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable, Coroutine
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# 바이낸스 선물 WebSocket/REST 엔드포인트
WS_BASE = "wss://fstream.binance.com"
WS_BASE_TESTNET = "wss://stream.binancefuture.com"
REST_BASE = "https://fapi.binance.com"
REST_BASE_TESTNET = "https://testnet.binancefuture.com"

Callback = Callable[[dict], Coroutine[Any, Any, None]]


class BinanceWebSocketManager:
    """바이낸스 USDT-M 선물 WebSocket 관리자"""

    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        testnet: bool = False,
    ):
        self._api_key = api_key
        self._secret_key = secret_key
        self._testnet = testnet

        self._ws_base = WS_BASE_TESTNET if testnet else WS_BASE
        self._rest_base = REST_BASE_TESTNET if testnet else REST_BASE

        # 콜백 등록: stream_name -> [callbacks]
        self._callbacks: dict[str, list[Callback]] = {}

        # WebSocket 상태
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._session: aiohttp.ClientSession | None = None
        self._running = False
        self._reconnect_count = 0
        self._max_reconnects = 5
        self._reconnect_delay = 3  # seconds

        # listenKey (userData stream)
        self._listen_key: str = ""
        self._listen_key_task: asyncio.Task | None = None

        # 구독 중인 스트림 목록
        self._streams: list[str] = []

    # ── 공개 API ──────────────────────────────────────

    def on(self, stream_name: str, callback: Callback) -> None:
        """스트림별 콜백 등록

        stream_name 예시:
            "btcusdt@markPrice@1s"
            "btcusdt@kline_1h"
            "userData"  (포지션/주문)
        """
        self._callbacks.setdefault(stream_name, []).append(callback)

    async def start(self, streams: list[str], user_data: bool = False) -> None:
        """WebSocket 연결 시작

        Args:
            streams: 구독할 스트림 목록 (e.g. ["btcusdt@markPrice@1s", "btcusdt@kline_1h"])
            user_data: True면 userData 스트림도 연결 (listenKey 필요)
        """
        self._streams = list(streams)
        self._running = True
        self._reconnect_count = 0

        if user_data and self._api_key:
            await self._create_listen_key()
            if self._listen_key:
                self._streams.append(self._listen_key)
                self._listen_key_task = asyncio.create_task(self._keepalive_listen_key())

        await self._connect()

    async def stop(self) -> None:
        """WebSocket 연결 종료"""
        self._running = False

        if self._listen_key_task and not self._listen_key_task.done():
            self._listen_key_task.cancel()
            try:
                await self._listen_key_task
            except asyncio.CancelledError:
                pass

        if self._ws and not self._ws.closed:
            await self._ws.close()

        if self._session and not self._session.closed:
            await self._session.close()

        logger.info("WebSocket 종료")

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    # ── 연결 관리 ──────────────────────────────────────

    async def _connect(self) -> None:
        """WebSocket 연결 및 메시지 수신 루프"""
        if not self._streams:
            logger.warning("구독할 스트림 없음")
            return

        stream_path = "/".join(self._streams)
        url = f"{self._ws_base}/stream?streams={stream_path}"

        while self._running:
            try:
                if not self._session or self._session.closed:
                    self._session = aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(
                            resolver=aiohttp.ThreadedResolver()
                        )
                    )

                logger.info("WebSocket 연결 시도: %s", url[:100])
                self._ws = await self._session.ws_connect(
                    url, heartbeat=30, timeout=aiohttp.ClientWSTimeout(ws_close=10)
                )
                self._reconnect_count = 0
                logger.info("WebSocket 연결 성공 (스트림 %d개)", len(self._streams))

                await self._recv_loop()

            except (aiohttp.WSServerHandshakeError, aiohttp.ClientError, OSError) as e:
                logger.error("WebSocket 연결 에러: %s", e)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("WebSocket 예외: %s", e)

            # 재연결
            if not self._running:
                break

            self._reconnect_count += 1
            if self._reconnect_count > self._max_reconnects:
                logger.error("WebSocket 최대 재연결 횟수 초과 (%d)", self._max_reconnects)
                break

            logger.info(
                "WebSocket 재연결 %d/%d (%.0fs 후)",
                self._reconnect_count, self._max_reconnects, self._reconnect_delay,
            )
            await asyncio.sleep(self._reconnect_delay)

    async def _recv_loop(self) -> None:
        """메시지 수신 루프"""
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    await self._dispatch(data)
                except json.JSONDecodeError:
                    logger.warning("JSON 파싱 실패: %s", msg.data[:200])

            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error("WebSocket 에러: %s", self._ws.exception())
                break

            elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSED):
                logger.info("WebSocket 닫힘")
                break

    async def _dispatch(self, data: dict) -> None:
        """수신 데이터를 등록된 콜백에 전달"""
        # combined stream format: {"stream": "...", "data": {...}}
        stream = data.get("stream", "")
        payload = data.get("data", data)

        # userData 이벤트 (listenKey 스트림)
        event_type = payload.get("e", "")
        if event_type in ("ORDER_TRADE_UPDATE", "ACCOUNT_UPDATE"):
            stream = "userData"

        callbacks = self._callbacks.get(stream, [])
        for cb in callbacks:
            try:
                await cb(payload)
            except Exception as e:
                logger.error("콜백 에러 [%s]: %s", stream, e)

    # ── listenKey 관리 ──────────────────────────────────

    async def _create_listen_key(self) -> None:
        """userData 스트림용 listenKey 생성"""
        url = f"{self._rest_base}/fapi/v1/listenKey"
        headers = {"X-MBX-APIKEY": self._api_key}

        try:
            if not self._session or self._session.closed:
                self._session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(
                        resolver=aiohttp.ThreadedResolver()
                    )
                )

            async with self._session.post(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._listen_key = data.get("listenKey", "")
                    logger.info("listenKey 생성 완료")
                else:
                    text = await resp.text()
                    logger.error("listenKey 생성 실패 [%d]: %s", resp.status, text)
        except Exception as e:
            logger.error("listenKey 요청 에러: %s", e)

    async def _keepalive_listen_key(self) -> None:
        """listenKey 30분마다 갱신 (60분 만료)"""
        url = f"{self._rest_base}/fapi/v1/listenKey"
        headers = {"X-MBX-APIKEY": self._api_key}

        while self._running:
            await asyncio.sleep(30 * 60)  # 30분
            try:
                if self._session and not self._session.closed:
                    async with self._session.put(url, headers=headers) as resp:
                        if resp.status == 200:
                            logger.debug("listenKey 갱신 완료")
                        else:
                            logger.warning("listenKey 갱신 실패 [%d]", resp.status)
                            await self._create_listen_key()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("listenKey 갱신 에러: %s", e)
