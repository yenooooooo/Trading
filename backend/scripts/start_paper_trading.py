"""
모의매매 상시 실행 스크립트

설정:
  - 전략: 펀딩비 수확 (funding_rate)
  - 심볼: BTC/USDT + ETH/USDT
  - 시드: $200, 레버리지: 2x
  - 모드: paper (TRADING_MODE=paper)

실행:
  cd backend && python scripts/start_paper_trading.py

종료:
  Ctrl+C

백그라운드 실행 (Windows):
  PowerShell:
    Start-Process -NoNewWindow python -ArgumentList "scripts/start_paper_trading.py" -RedirectStandardOutput "logs/paper.log" -RedirectStandardError "logs/paper_err.log"

  또는 nssm 서비스 등록 (권장):
    nssm install PaperTrading python scripts/start_paper_trading.py
"""

import asyncio
import io
import logging
import os
import signal
import sys
from datetime import datetime, timezone

# UTF-8 출력 (Windows cp949 문제 방지)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 프로젝트 루트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.trading.live_trading import LiveTradingEngine
from app.services.notification.telegram_notifier import TelegramNotifier

# --- 로깅 설정 ---
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(LOG_DIR, "paper_trading.log"),
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("paper_trading")

# --- 설정 ---
SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
LEVERAGE = 2
PAPER_BALANCE = 200.0  # $200 시드
MAX_RESTARTS = 3


async def run_engine() -> None:
    """엔진 실행 (Ctrl+C로 종료)"""
    engine = LiveTradingEngine(
        symbols=SYMBOLS,
        leverage=LEVERAGE,
        paper_balance=PAPER_BALANCE,
    )

    # Ctrl+C 핸들링
    shutdown_event = asyncio.Event()

    def on_shutdown():
        logger.info("종료 신호 수신 (Ctrl+C)")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGINT, on_shutdown)
        loop.add_signal_handler(signal.SIGTERM, on_shutdown)
    except NotImplementedError:
        # Windows에서는 add_signal_handler 미지원 → 별도 처리
        pass

    # 시작
    await engine.start(symbols=SYMBOLS)

    logger.info(
        "모의매매 실행 중 - 심볼: %s | 시드: $%.0f | 레버리지: %dx",
        SYMBOLS, PAPER_BALANCE, LEVERAGE,
    )
    logger.info("종료하려면 Ctrl+C를 누르세요.")

    # 메인 대기 루프
    try:
        while engine._running:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        if engine._running:
            await engine.stop(reason="Ctrl+C 종료")


async def main() -> None:
    """자동 재시작 래퍼"""
    notifier = TelegramNotifier(paper_mode=True)
    restart_count = 0

    while restart_count <= MAX_RESTARTS:
        try:
            if restart_count > 0:
                logger.warning("재시작 %d/%d...", restart_count, MAX_RESTARTS)
                await notifier.notify_risk_alert({
                    "alert_type": "자동 재시작",
                    "message": f"시스템 자동 재시작 ({restart_count}/{MAX_RESTARTS})",
                })
                await asyncio.sleep(5)  # 재시작 전 대기

            await run_engine()
            break  # 정상 종료 (Ctrl+C)

        except KeyboardInterrupt:
            break

        except Exception as e:
            restart_count += 1
            logger.error("엔진 크래시: %s", e, exc_info=True)
            await notifier.notify_system_error(
                f"엔진 크래시 (재시작 {restart_count}/{MAX_RESTARTS})",
                str(e),
            )

            if restart_count > MAX_RESTARTS:
                logger.critical("최대 재시작 횟수 초과 - 종료")
                await notifier.notify_system_error(
                    "최대 재시작 횟수 초과 - 시스템 종료",
                    f"마지막 에러: {e}",
                )
                break

    logger.info("모의매매 스크립트 종료")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n종료됨.")
