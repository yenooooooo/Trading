"""
알림 API 엔드포인트
- 알림 규칙 ON/OFF, 히스토리 조회
- 텔레그램 연동 상태
- 사용처: 알림 페이지
"""

import os
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.common import success_response
from app.config import get_settings

router = APIRouter()

# --- 알림 규칙 (인메모리, 서버 재시작 시 초기화) ---
_alert_rules = [
    {
        "id": "position_open",
        "name": "포지션 진입 알림",
        "description": "새 포지션이 열릴 때 텔레그램 알림",
        "enabled": True,
        "category": "trading",
    },
    {
        "id": "position_close",
        "name": "포지션 청산 알림",
        "description": "포지션이 청산될 때 손익과 함께 알림",
        "enabled": True,
        "category": "trading",
    },
    {
        "id": "daily_loss_limit",
        "name": "일일 손실 한도 초과",
        "description": "일일 손실이 설정 한도를 초과할 때 경고",
        "enabled": True,
        "category": "risk",
    },
    {
        "id": "consecutive_loss",
        "name": "연속 손실 경고",
        "description": "연속 손실이 임계치에 도달할 때 알림",
        "enabled": True,
        "category": "risk",
    },
    {
        "id": "system_error",
        "name": "시스템 에러 알림",
        "description": "WebSocket 끊김, API 에러 등 시스템 문제 발생 시 알림",
        "enabled": True,
        "category": "system",
    },
    {
        "id": "daily_report",
        "name": "일일 리포트",
        "description": "매일 09:00 KST 전일 거래 요약 발송",
        "enabled": False,
        "category": "report",
    },
]

# --- 알림 히스토리 (인메모리) ---
_alert_history: list[dict] = []
MAX_HISTORY = 100


def add_alert_history(alert_type: str, title: str, message: str):
    """알림 히스토리 추가 (다른 모듈에서 호출)"""
    _alert_history.insert(0, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": alert_type,
        "title": title,
        "message": message,
        "sent_via": "telegram",
    })
    if len(_alert_history) > MAX_HISTORY:
        _alert_history.pop()


# --- API 엔드포인트 ---

@router.get("/rules")
async def get_alert_rules():
    """알림 규칙 목록"""
    return success_response(_alert_rules)


class ToggleRequest(BaseModel):
    enabled: bool


@router.put("/rules/{rule_id}")
async def toggle_alert_rule(rule_id: str, body: ToggleRequest):
    """알림 규칙 ON/OFF"""
    for rule in _alert_rules:
        if rule["id"] == rule_id:
            rule["enabled"] = body.enabled
            return success_response(rule)
    return success_response({"error": "규칙을 찾을 수 없습니다"})


@router.get("/history")
async def get_alert_history():
    """알림 히스토리 (최근 100건)"""
    return success_response(_alert_history)


@router.get("/status")
async def get_alert_status():
    """알림 시스템 상태 요약"""
    settings = get_settings()

    # 텔레그램 연결 확인
    tg_token = settings.telegram_bot_token or ""
    tg_chat_id = settings.telegram_chat_id or ""
    tg_connected = bool(tg_token and tg_chat_id)

    # 활성 규칙 수
    active_rules = sum(1 for r in _alert_rules if r["enabled"])

    # 오늘 발송 건수
    today = datetime.now(timezone.utc).date().isoformat()
    today_sent = sum(
        1 for h in _alert_history
        if h["timestamp"].startswith(today)
    )

    return success_response({
        "active_rules": active_rules,
        "total_rules": len(_alert_rules),
        "today_sent": today_sent,
        "telegram_connected": tg_connected,
        "telegram_bot_token_masked": f"****{tg_token[-4:]}" if len(tg_token) > 4 else "미설정",
        "telegram_chat_id": tg_chat_id or "미설정",
    })
