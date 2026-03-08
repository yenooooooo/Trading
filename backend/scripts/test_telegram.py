"""
텔레그램 알림 테스트 스크립트
- 모든 알림 유형을 순차적으로 발송
- 실행: python scripts/test_telegram.py
"""

import asyncio
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.notification.telegram_notifier import TelegramNotifier


async def main():
    notifier = TelegramNotifier(paper_mode=True)

    if not notifier._enabled:
        print("ERROR: 텔레그램 설정 없음 (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
        return

    print("=== 텔레그램 알림 테스트 시작 ===\n")

    # 1) 시스템 시작
    print("1. 시스템 시작 알림...")
    await notifier.notify_system_start()
    print("   -> 전송 완료")
    await asyncio.sleep(1)

    # 2) 포지션 진입
    print("2. 포지션 진입 알림...")
    await notifier.notify_trade_open({
        "symbol": "BTC/USDT",
        "side": "short",
        "entry_price": "67,500.00",
        "leverage": 5,
        "amount_pct": 30,
        "sl": "68,175.00",
        "tp": "66,487.50",
        "funding_rate": "0.0350",
        "next_funding_minutes": 45,
        "reason": "펀딩비 수확: +0.0350% (숏=수취)",
    })
    print("   -> 전송 완료")
    await asyncio.sleep(1)

    # 3) 포지션 청산
    print("3. 포지션 청산 알림...")
    await notifier.notify_trade_close({
        "symbol": "BTC/USDT",
        "side": "short",
        "entry_price": "67,500.00",
        "exit_price": "67,320.00",
        "pnl_pct": 0.27,
        "fee": 2.03,
        "funding_income": 3.38,
        "net_pnl": 1.62,
        "hold_duration": "8.2시간",
        "reason": "펀딩비 정산 후 청산",
    })
    print("   -> 전송 완료")
    await asyncio.sleep(1)

    # 4) 리스크 경고
    print("4. 리스크 경고 알림...")
    await notifier.notify_risk_alert({
        "alert_type": "일일 손실 한도",
        "message": "일일 손실 -2.8% (한도 -3.0%)",
        "details": "연속 2회 손절 발생",
    })
    print("   -> 전송 완료")
    await asyncio.sleep(1)

    # 5) 일일 리포트
    print("5. 일일 리포트 알림...")
    await notifier.notify_daily_report({
        "date": "2026-03-08",
        "trade_count": 4,
        "win_count": 3,
        "loss_count": 1,
        "gross_pnl": 5.20,
        "funding_income": 8.50,
        "total_fee": 3.10,
        "net_pnl": 10.60,
        "balance": 1010.60,
        "cumulative_return_pct": 1.06,
    })
    print("   -> 전송 완료")
    await asyncio.sleep(1)

    # 6) 시스템 에러
    print("6. 시스템 에러 알림...")
    await notifier.notify_system_error(
        "WebSocket 연결 끊김",
        "ConnectionResetError: [WinError 10054]"
    )
    print("   -> 전송 완료")
    await asyncio.sleep(1)

    # 7) 시스템 종료
    print("7. 시스템 종료 알림...")
    await notifier.notify_system_stop("테스트 완료")
    print("   -> 전송 완료")

    print("\n=== 텔레그램 알림 테스트 완료 (7개 메시지) ===")
    print("텔레그램 앱에서 메시지 수신 확인해주세요.")


if __name__ == "__main__":
    asyncio.run(main())
