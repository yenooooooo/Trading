"""
텔레그램 알림 서비스
- 매매 진입/청산 알림
- 리스크 경고
- 일일 리포트
- 시스템 에러 알림
- 모의매매 모드 표시
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
_TG_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    """텔레그램 봇을 통한 트레이딩 알림"""

    def __init__(self, paper_mode: bool = True):
        settings = get_settings()
        self._token = settings.telegram_bot_token
        self._chat_id = settings.telegram_chat_id
        self._paper = paper_mode
        self._enabled = bool(self._token and self._chat_id)
        if not self._enabled:
            logger.warning("텔레그램 알림 비활성: bot_token 또는 chat_id 미설정")

    # ── 공개 메서드 ──────────────────────────────────────

    async def notify_trade_open(self, info: dict) -> None:
        """포지션 진입 알림

        info keys:
            symbol, side, entry_price, leverage, sl, tp,
            funding_rate, next_funding_minutes, amount_pct, reason
        """
        side_emoji = "🔴 숏" if info.get("side") == "short" else "🟢 롱"
        lines = [
            self._header("포지션 진입"),
            f"{side_emoji}  {info.get('symbol', '?')}",
            f"진입가: {info.get('entry_price', '-')}",
            f"레버리지: {info.get('leverage', '-')}x",
            f"비중: {info.get('amount_pct', '-')}%",
            f"SL: {info.get('sl', '-')}  |  TP: {info.get('tp', '-')}",
            f"펀딩비: {info.get('funding_rate', '-')}%",
            f"다음 정산: {info.get('next_funding_minutes', '?')}분 후",
            f"사유: {info.get('reason', '-')}",
        ]
        await self._send("\n".join(lines))

    async def notify_trade_close(self, info: dict) -> None:
        """포지션 청산 알림

        info keys:
            symbol, side, entry_price, exit_price, pnl_pct,
            fee, funding_income, net_pnl, hold_duration, reason
        """
        result = "✅ 수익" if info.get("pnl_pct", 0) >= 0 else "❌ 손실"
        lines = [
            self._header("포지션 청산"),
            f"{result}  {info.get('symbol', '?')}",
            f"방향: {'숏' if info.get('side') == 'short' else '롱'}",
            f"진입 → 청산: {info.get('entry_price', '-')} → {info.get('exit_price', '-')}",
            f"수익률: {info.get('pnl_pct', 0):+.2f}%",
            f"수수료: {info.get('fee', 0):.4f} USDT",
            f"펀딩수입: {info.get('funding_income', 0):+.4f} USDT",
            f"순이익: {info.get('net_pnl', 0):+.4f} USDT",
            f"보유시간: {info.get('hold_duration', '-')}",
            f"사유: {info.get('reason', '-')}",
        ]
        await self._send("\n".join(lines))

    async def notify_risk_alert(self, info: dict) -> None:
        """리스크 경고 알림

        info keys:
            alert_type, message, details
        """
        lines = [
            self._header("⚠️ 리스크 경고"),
            f"유형: {info.get('alert_type', '-')}",
            f"내용: {info.get('message', '-')}",
        ]
        if info.get("details"):
            lines.append(f"상세: {info['details']}")
        await self._send("\n".join(lines))

    async def notify_daily_report(self, report: dict) -> None:
        """일일 리포트 (UTC 00:00)

        report keys:
            date, trade_count, win_count, loss_count,
            gross_pnl, funding_income, total_fee, net_pnl,
            balance, cumulative_return_pct
        """
        lines = [
            self._header("📊 일일 리포트"),
            f"날짜: {report.get('date', '-')}",
            "",
            f"매매 횟수: {report.get('trade_count', 0)}회"
            f"  (승 {report.get('win_count', 0)} / 패 {report.get('loss_count', 0)})",
            f"매매 손익: {report.get('gross_pnl', 0):+.4f} USDT",
            f"펀딩 수입: {report.get('funding_income', 0):+.4f} USDT",
            f"수수료: -{report.get('total_fee', 0):.4f} USDT",
            f"순이익: {report.get('net_pnl', 0):+.4f} USDT",
            "",
            f"잔고: {report.get('balance', 0):,.2f} USDT",
            f"누적 수익률: {report.get('cumulative_return_pct', 0):+.2f}%",
        ]
        await self._send("\n".join(lines))

    async def notify_system_error(self, error: str, detail: str = "") -> None:
        """시스템 에러 알림"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            self._header("🚨 시스템 에러"),
            f"시각: {now}",
            f"에러: {error}",
        ]
        if detail:
            lines.append(f"상세: {detail[:500]}")
        await self._send("\n".join(lines))

    async def notify_system_start(self) -> None:
        """시스템 시작 알림"""
        mode = "모의매매" if self._paper else "실전매매"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            self._header("🚀 시스템 시작"),
            f"모드: {mode}",
            f"시각: {now}",
        ]
        await self._send("\n".join(lines))

    async def notify_system_stop(self, reason: str = "수동 종료") -> None:
        """시스템 종료 알림"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            self._header("🛑 시스템 종료"),
            f"사유: {reason}",
            f"시각: {now}",
        ]
        await self._send("\n".join(lines))

    # ── 내부 메서드 ──────────────────────────────────────

    def _header(self, title: str) -> str:
        prefix = "[모의매매] " if self._paper else ""
        return f"{'=' * 20}\n{prefix}{title}\n{'=' * 20}"

    async def _send(self, text: str) -> None:
        if not self._enabled:
            logger.debug("텔레그램 비활성 - 메시지 스킵: %s", text[:80])
            return

        url = _TG_API.format(token=self._token)
        payload = {
            "chat_id": self._chat_id,
            "text": text,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error("텔레그램 전송 실패 [%d]: %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("텔레그램 전송 에러: %s", e)
