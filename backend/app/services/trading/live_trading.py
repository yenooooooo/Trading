"""
실시간 트레이딩 루프
- 펀딩비 정산 스케줄 기반 매매 (00:00/08:00/16:00 UTC)
- 정산 1시간 전 신호 체크, 정산 후 청산 모니터링
- 모의매매(paper) / 실전매매(live) 모드 지원
- WebSocket 실시간 데이터 연동
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.config import get_settings
from app.services.exchange.binance import BinanceFuturesConnector
from app.services.exchange.binance_ws import BinanceWebSocketManager
from app.services.exchange.base import Candle, PositionInfo
from app.services.strategy.base_strategy import TradeSignal, SignalType, MarketContext
from app.services.strategy.registry import get_strategy
from app.services.trading.trading_engine import TradingEngine
from app.services.notification.telegram_notifier import TelegramNotifier

logger = logging.getLogger(__name__)

# 펀딩비 정산 시각 (UTC)
FUNDING_HOURS = [0, 8, 16]
# 정산 전 신호 체크 시작 (분)
PRE_FUNDING_MINUTES = 60
# 메인 루프 틱 간격 (초)
TICK_INTERVAL = 30


class LiveTradingEngine:
    """실시간 트레이딩 엔진"""

    def __init__(
        self,
        symbols: list[str] | None = None,
        leverage: int = 5,
        paper_balance: float = 1000.0,
    ):
        settings = get_settings()
        self._paper_mode = settings.trading_mode != "live"
        self._symbols: list[str] = symbols or ["BTC/USDT:USDT"]
        self._leverage = leverage
        self._interval = "1h"

        # 컴포넌트
        self._connector = BinanceFuturesConnector(
            api_key=settings.binance_api_key,
            secret_key=settings.binance_secret_key,
        )
        self._ws = BinanceWebSocketManager(
            api_key=settings.binance_api_key,
            secret_key=settings.binance_secret_key,
        )
        self._engine = TradingEngine(connector=self._connector)
        self._notifier = TelegramNotifier(paper_mode=self._paper_mode)
        self._strategy = get_strategy("funding_rate")

        # 상태
        self._running = False
        self._task: asyncio.Task | None = None
        self._current_mark_price: dict[str, float] = {}
        self._current_funding_rate: dict[str, float] = {}
        self._last_signal_check: datetime | None = None
        self._last_daily_report_date: str = ""

        # 모의매매 가상 포지션
        self._paper_position: dict[str, dict] = {}
        self._paper_balance: float = paper_balance

    # ── 시작 / 종료 ──────────────────────────────────

    async def start(self, symbols: list[str] | None = None) -> None:
        """트레이딩 시작"""
        if self._running:
            logger.warning("이미 실행 중")
            return

        if symbols:
            self._symbols = symbols

        self._running = True

        # 거래소 연결 (paper 모드에서도 시세 데이터용으로 연결)
        connected = await self._connector.connect()
        if not connected and not self._paper_mode:
            await self._notifier.notify_system_error("거래소 연결 실패")
            self._running = False
            return

        # WebSocket 시작
        ws_streams = []
        for sym in self._symbols:
            pair = sym.replace("/", "").replace(":USDT", "").lower()
            ws_streams.append(f"{pair}@markPrice@1s")
            ws_streams.append(f"{pair}@kline_{self._interval}")

        self._ws.on("userData", self._on_user_data)
        for stream in ws_streams:
            if "markPrice" in stream:
                self._ws.on(stream, self._on_mark_price)

        asyncio.create_task(self._ws.start(ws_streams, user_data=not self._paper_mode))

        await self._notifier.notify_system_start()
        logger.info("트레이딩 시작 (모드=%s, 심볼=%s)",
                     "paper" if self._paper_mode else "live", self._symbols)

        # 메인 루프 시작
        self._task = asyncio.create_task(self._main_loop())

    async def stop(self, reason: str = "수동 종료") -> None:
        """트레이딩 종료"""
        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self._ws.stop()
        await self._connector.disconnect()
        await self._notifier.notify_system_stop(reason)
        logger.info("트레이딩 종료: %s", reason)

    async def emergency_stop(self) -> None:
        """긴급 정지: 모든 포지션 청산 후 종료"""
        logger.warning("긴급 정지!")

        if not self._paper_mode:
            for sym in self._symbols:
                try:
                    await self._engine._close_position(sym)
                except Exception as e:
                    logger.error("긴급 청산 실패 [%s]: %s", sym, e)

        await self._notifier.notify_risk_alert({
            "alert_type": "긴급 정지",
            "message": "모든 포지션 청산 후 시스템 종료",
        })

        await self.stop(reason="긴급 정지")

    # ── 메인 루프 ──────────────────────────────────────

    async def _main_loop(self) -> None:
        """펀딩비 스케줄 기반 메인 루프"""
        try:
            while self._running:
                now = datetime.now(timezone.utc)

                # 다음 펀딩 정산까지 남은 시간
                minutes_to_funding = self._minutes_to_next_funding(now)

                # 1) 정산 전 1시간: 신호 체크
                if minutes_to_funding <= PRE_FUNDING_MINUTES:
                    await self._check_signals()

                # 2) 포지션 보유 중: 청산 조건 체크
                await self._monitor_positions()

                # 3) 일일 리셋 (UTC 00:00 ~ 00:01 사이 1회)
                today_str = now.strftime("%Y-%m-%d")
                if now.hour == 0 and now.minute < 2 and self._last_daily_report_date != today_str:
                    self._last_daily_report_date = today_str
                    await self._send_daily_report()
                    self._engine.reset_daily()

                    # 주간 리셋 (월요일)
                    if now.weekday() == 0:
                        self._engine.reset_weekly()

                await asyncio.sleep(TICK_INTERVAL)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("메인 루프 에러: %s", e)
            await self._notifier.notify_system_error("메인 루프 크래시", str(e))

    # ── 신호 체크 ──────────────────────────────────────

    async def _check_signals(self) -> None:
        """전략 신호 확인 및 실행"""
        now = datetime.now(timezone.utc)

        # 중복 체크 방지 (같은 정산 주기에 1번만)
        if self._last_signal_check:
            elapsed = (now - self._last_signal_check).total_seconds()
            if elapsed < 3600:  # 1시간 이내 재체크 방지
                return

        self._last_signal_check = now

        for symbol in self._symbols:
            try:
                # 캔들 데이터 조회
                candles = await self._connector.get_klines(
                    symbol, self._interval, limit=100
                )
                if not candles:
                    continue

                # 현재 포지션
                current_position = None
                if self._paper_mode:
                    pp = self._paper_position.get(symbol)
                    current_position = pp["side"] if pp else None
                else:
                    pos = await self._connector.get_position(symbol)
                    current_position = pos.side if pos else None

                # 펀딩비
                pair = symbol.replace("/", "").replace(":USDT", "").lower()
                funding_rate = self._current_funding_rate.get(pair, 0.0)

                # MarketContext 생성
                context = MarketContext(
                    funding_rate=funding_rate,
                    volume_ratio=1.0,
                    open_interest_change=0.0,
                )

                # 신호 생성
                signal = await self._strategy.generate_signal(
                    symbol=symbol,
                    candles=candles,
                    current_position=current_position,
                    context=context,
                )

                if signal.signal == SignalType.HOLD:
                    continue

                logger.info("신호 감지: %s %s (%s)", symbol, signal.signal.value, signal.reason)

                # 실행
                await self._execute_signal(symbol, signal)

            except Exception as e:
                logger.error("신호 체크 에러 [%s]: %s", symbol, e)
                await self._notifier.notify_system_error(
                    f"신호 체크 실패: {symbol}", str(e)
                )

    async def _execute_signal(self, symbol: str, signal: TradeSignal) -> None:
        """신호 실행 (paper/live 분기)"""
        if signal.signal == SignalType.CLOSE:
            await self._close_position(symbol, signal)
        elif signal.signal in (SignalType.LONG, SignalType.SHORT):
            await self._open_position(symbol, signal)

    async def _open_position(self, symbol: str, signal: TradeSignal) -> None:
        """포지션 진입"""
        side = "long" if signal.signal == SignalType.LONG else "short"

        if self._paper_mode:
            pair = symbol.replace("/", "").replace(":USDT", "").lower()
            price = self._current_mark_price.get(pair, 0)
            if not price:
                ticker = await self._connector.get_ticker(symbol)
                price = float(ticker.price)

            self._paper_position[symbol] = {
                "side": side,
                "entry_price": price,
                "entry_time": datetime.now(timezone.utc),
                "size_pct": signal.amount_pct,
            }
            logger.info("[PAPER] 포지션 진입: %s %s @ %.2f", symbol, side, price)
        else:
            result = await self._engine.execute_signal(
                signal=signal,
                leverage=self._leverage,
                max_position_pct=signal.amount_pct,
            )
            if not result:
                return
            price = float(result.price) if result.price else 0

        # 알림
        pair = symbol.replace("/", "").replace(":USDT", "").lower()
        minutes_to = self._minutes_to_next_funding(datetime.now(timezone.utc))
        await self._notifier.notify_trade_open({
            "symbol": symbol,
            "side": side,
            "entry_price": f"{price:,.2f}",
            "leverage": self._leverage,
            "amount_pct": signal.amount_pct * 100,
            "sl": str(signal.stop_loss) if signal.stop_loss else "-",
            "tp": str(signal.take_profit) if signal.take_profit else "-",
            "funding_rate": f"{self._current_funding_rate.get(pair, 0):.4f}",
            "next_funding_minutes": int(minutes_to),
            "reason": signal.reason,
        })

    async def _close_position(self, symbol: str, signal: TradeSignal) -> None:
        """포지션 청산"""
        if self._paper_mode:
            pp = self._paper_position.get(symbol)
            if not pp:
                return

            pair = symbol.replace("/", "").replace(":USDT", "").lower()
            exit_price = self._current_mark_price.get(pair, 0)
            if not exit_price:
                ticker = await self._connector.get_ticker(symbol)
                exit_price = float(ticker.price)

            entry_price = pp["entry_price"]
            side = pp["side"]
            if side == "long":
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - exit_price) / entry_price * 100

            hold_time = datetime.now(timezone.utc) - pp["entry_time"]
            hours = hold_time.total_seconds() / 3600

            self._engine.update_pnl(pnl_pct)
            del self._paper_position[symbol]

            logger.info("[PAPER] 포지션 청산: %s P/L %.2f%%", symbol, pnl_pct)

            await self._notifier.notify_trade_close({
                "symbol": symbol,
                "side": side,
                "entry_price": f"{entry_price:,.2f}",
                "exit_price": f"{exit_price:,.2f}",
                "pnl_pct": pnl_pct,
                "fee": 0,
                "funding_income": 0,
                "net_pnl": pnl_pct * self._paper_balance * pp["size_pct"] / 100,
                "hold_duration": f"{hours:.1f}시간",
                "reason": signal.reason,
            })
        else:
            result = await self._engine.execute_signal(signal=signal)
            if result:
                await self._notifier.notify_trade_close({
                    "symbol": symbol,
                    "side": "?",
                    "entry_price": "-",
                    "exit_price": str(result.price) if result.price else "-",
                    "pnl_pct": 0,
                    "fee": 0,
                    "funding_income": 0,
                    "net_pnl": 0,
                    "hold_duration": "-",
                    "reason": signal.reason,
                })

    # ── 포지션 모니터링 ──────────────────────────────────

    async def _monitor_positions(self) -> None:
        """보유 포지션 청산 조건 체크"""
        for symbol in self._symbols:
            try:
                has_position = False
                current_position = None

                if self._paper_mode:
                    pp = self._paper_position.get(symbol)
                    if pp:
                        has_position = True
                        current_position = pp["side"]
                else:
                    pos = await self._connector.get_position(symbol)
                    if pos:
                        has_position = True
                        current_position = pos.side

                if not has_position:
                    continue

                # 캔들 데이터로 청산 신호 체크
                candles = await self._connector.get_klines(
                    symbol, self._interval, limit=100
                )
                if not candles:
                    continue

                pair = symbol.replace("/", "").replace(":USDT", "").lower()
                funding_rate = self._current_funding_rate.get(pair, 0.0)

                context = MarketContext(
                    funding_rate=funding_rate,
                    volume_ratio=1.0,
                    open_interest_change=0.0,
                )

                signal = await self._strategy.generate_signal(
                    symbol=symbol,
                    candles=candles,
                    current_position=current_position,
                    context=context,
                )

                if signal.signal == SignalType.CLOSE:
                    await self._execute_signal(symbol, signal)

            except Exception as e:
                logger.error("포지션 모니터링 에러 [%s]: %s", symbol, e)

    # ── WebSocket 콜백 ──────────────────────────────────

    async def _on_mark_price(self, data: dict) -> None:
        """markPrice 스트림 콜백"""
        symbol = data.get("s", "").lower()
        if symbol:
            self._current_mark_price[symbol] = float(data.get("p", 0))
            self._current_funding_rate[symbol] = float(data.get("r", 0)) * 100  # → %

    async def _on_user_data(self, data: dict) -> None:
        """userData 스트림 콜백 (주문/포지션 업데이트)"""
        event = data.get("e", "")
        if event == "ORDER_TRADE_UPDATE":
            order = data.get("o", {})
            logger.info(
                "주문 업데이트: %s %s %s (%s)",
                order.get("s"), order.get("S"), order.get("X"), order.get("x"),
            )
        elif event == "ACCOUNT_UPDATE":
            logger.info("계정 업데이트 수신")

    # ── 유틸리티 ──────────────────────────────────────

    @staticmethod
    def _minutes_to_next_funding(now: datetime) -> float:
        """다음 펀딩 정산까지 남은 분"""
        for h in FUNDING_HOURS:
            target = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if target > now:
                return (target - now).total_seconds() / 60

        # 다음 날 00:00
        tomorrow = now + timedelta(days=1)
        target = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        return (target - now).total_seconds() / 60

    async def _send_daily_report(self) -> None:
        """일일 리포트 전송"""
        try:
            if not self._paper_mode:
                balance = await self._connector.get_balance()
                bal = float(balance.total)
            else:
                bal = self._paper_balance

            await self._notifier.notify_daily_report({
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "trade_count": len(self._engine._today_trades),
                "win_count": sum(1 for t in self._engine._recent_trades if t.get("pnl", 0) > 0),
                "loss_count": sum(1 for t in self._engine._recent_trades if t.get("pnl", 0) <= 0),
                "gross_pnl": self._engine._today_pnl,
                "funding_income": 0,
                "total_fee": 0,
                "net_pnl": self._engine._today_pnl,
                "balance": bal,
                "cumulative_return_pct": 0,
            })
        except Exception as e:
            logger.error("일일 리포트 전송 에러: %s", e)

    # ── 상태 조회 ──────────────────────────────────────

    def get_status(self) -> dict:
        """현재 상태 반환"""
        now = datetime.now(timezone.utc)
        minutes_to = self._minutes_to_next_funding(now)

        positions = []
        if self._paper_mode:
            for sym, pp in self._paper_position.items():
                pair = sym.replace("/", "").replace(":USDT", "").lower()
                mark = self._current_mark_price.get(pair, pp["entry_price"])
                entry = pp["entry_price"]
                if pp["side"] == "long":
                    pnl = (mark - entry) / entry * 100
                else:
                    pnl = (entry - mark) / entry * 100

                positions.append({
                    "symbol": sym,
                    "side": pp["side"],
                    "entry_price": entry,
                    "mark_price": mark,
                    "pnl_pct": round(pnl, 2),
                    "hold_minutes": (now - pp["entry_time"]).total_seconds() / 60,
                })

        return {
            "running": self._running,
            "mode": "paper" if self._paper_mode else "live",
            "symbols": self._symbols,
            "leverage": self._leverage,
            "next_funding_minutes": round(minutes_to, 1),
            "positions": positions,
            "today_pnl": round(self._engine._today_pnl, 4),
            "ws_connected": self._ws.is_connected,
        }
