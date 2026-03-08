"""
설정 API 엔드포인트
- 현재 설정 조회 (민감 값 마스킹)
- 설정 변경 (.env 파일 업데이트 + 런타임 반영)
- 텔레그램 / 거래소 연결 테스트
- 사용처: /dashboard/settings 페이지
"""

import os
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.common import success_response

logger = logging.getLogger(__name__)
router = APIRouter()

# .env 파일 경로
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


# ── 요청/응답 스키마 ──────────────────────────────

class UpdateSettingsRequest(BaseModel):
    binance_api_key: str | None = None
    binance_secret_key: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    trading_mode: str | None = None  # "paper" | "live"


# ── 유틸 ──────────────────────────────────────

def _mask(value: str, show: int = 4) -> str:
    """민감한 값을 마스킹 (앞 4자리만 표시)"""
    if not value or len(value) <= show:
        return "****"
    return value[:show] + "*" * (len(value) - show)


def _update_env_file(updates: dict[str, str]) -> None:
    """
    .env 파일의 특정 키들을 업데이트.
    키가 없으면 추가, 있으면 값만 교체.
    """
    lines: list[str] = []
    updated_keys: set[str] = set()

    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                # 빈 줄이나 주석은 유지
                if not stripped or stripped.startswith("#"):
                    lines.append(line)
                    continue

                key = stripped.split("=", 1)[0].strip()
                if key in updates:
                    lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                else:
                    lines.append(line)

    # 파일에 없던 키는 끝에 추가
    for key, value in updates.items():
        if key not in updated_keys:
            lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _reload_settings() -> None:
    """lru_cache를 클리어해서 다음 호출 시 새 설정 로드"""
    get_settings.cache_clear()


# ── 엔드포인트 ──────────────────────────────────

@router.get("")
async def get_current_settings():
    """현재 설정 조회 (민감 값 마스킹)"""
    s = get_settings()

    return success_response({
        "exchange": {
            "binance_api_key": _mask(s.binance_api_key),
            "binance_secret_key": _mask(s.binance_secret_key),
            "has_api_key": bool(s.binance_api_key),
        },
        "telegram": {
            "bot_token": _mask(s.telegram_bot_token),
            "chat_id": s.telegram_chat_id,  # chat_id는 민감하지 않음
            "enabled": bool(s.telegram_bot_token and s.telegram_chat_id),
        },
        "trading": {
            "mode": s.trading_mode,
            "cors_origins": s.cors_origins,
            "debug": s.debug,
            "backend_url": s.backend_url,
        },
    })


@router.put("")
async def update_settings(body: UpdateSettingsRequest):
    """설정 업데이트 (.env 파일 + 런타임)"""
    env_updates: dict[str, str] = {}

    if body.binance_api_key is not None:
        env_updates["BINANCE_API_KEY"] = body.binance_api_key
    if body.binance_secret_key is not None:
        env_updates["BINANCE_SECRET_KEY"] = body.binance_secret_key
    if body.telegram_bot_token is not None:
        env_updates["TELEGRAM_BOT_TOKEN"] = body.telegram_bot_token
    if body.telegram_chat_id is not None:
        env_updates["TELEGRAM_CHAT_ID"] = body.telegram_chat_id
    if body.trading_mode is not None:
        if body.trading_mode not in ("paper", "live"):
            raise HTTPException(400, "trading_mode는 'paper' 또는 'live'만 가능합니다")
        env_updates["TRADING_MODE"] = body.trading_mode

    if not env_updates:
        raise HTTPException(400, "변경할 설정이 없습니다")

    try:
        _update_env_file(env_updates)
        _reload_settings()

        # 환경변수도 즉시 반영 (현재 프로세스)
        for k, v in env_updates.items():
            os.environ[k] = v

        logger.info("설정 업데이트 완료: %s", list(env_updates.keys()))
    except Exception as e:
        logger.error("설정 업데이트 실패: %s", e)
        raise HTTPException(500, f"설정 저장 실패: {e}")

    # 업데이트 후 새 설정 반환
    s = get_settings()
    return success_response({
        "updated_keys": list(env_updates.keys()),
        "trading_mode": s.trading_mode,
    })


@router.post("/test-telegram")
async def test_telegram():
    """텔레그램 연결 테스트"""
    s = get_settings()

    if not s.telegram_bot_token or not s.telegram_chat_id:
        raise HTTPException(400, "텔레그램 봇 토큰 또는 채팅 ID가 설정되지 않았습니다")

    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": s.telegram_chat_id,
        "text": "✅ 텔레그램 연결 테스트 성공!\n설정 페이지에서 전송된 테스트 메시지입니다.",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return success_response({"status": "success", "message": "테스트 메시지 전송 완료"})
            else:
                detail = resp.json().get("description", resp.text)
                raise HTTPException(400, f"텔레그램 API 오류: {detail}")
    except httpx.TimeoutException:
        raise HTTPException(504, "텔레그램 API 응답 시간 초과")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"텔레그램 테스트 실패: {e}")


@router.post("/test-exchange")
async def test_exchange():
    """거래소 연결 테스트 (잔고 조회)"""
    s = get_settings()

    if not s.binance_api_key or not s.binance_secret_key:
        raise HTTPException(400, "바이낸스 API 키가 설정되지 않았습니다")

    try:
        from app.services.exchange.binance import BinanceFuturesConnector

        connector = BinanceFuturesConnector(
            api_key=s.binance_api_key,
            secret_key=s.binance_secret_key,
        )
        connected = await connector.connect()
        if not connected:
            raise HTTPException(400, "거래소 연결 실패")

        balance = await connector.get_balance()
        await connector.disconnect()

        return success_response({
            "status": "success",
            "balance": {
                "total": str(balance.total),
                "available": str(balance.available),
            },
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"거래소 테스트 실패: {e}")
