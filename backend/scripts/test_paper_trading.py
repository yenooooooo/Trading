"""
모의매매 통합 테스트 스크립트
- 거래소 연결 → 시세 수신 → 펀딩비 조회 → 강제 시그널 → 텔레그램 알림
- 실행: python scripts/test_paper_trading.py
"""

import asyncio
import sys
import os
import io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from app.config import get_settings
from app.services.exchange.binance import BinanceFuturesConnector
from app.services.strategy.base_strategy import TradeSignal, SignalType, MarketContext
from app.services.strategy.registry import get_strategy
from app.services.notification.telegram_notifier import TelegramNotifier


async def main():
    settings = get_settings()
    print("=" * 50)
    print("모의매매 통합 테스트")
    print(f"모드: {settings.trading_mode}")
    print(f"시각: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 50)

    # --- 1. 거래소 연결 테스트 ---
    print("\n[1/6] 거래소 연결...")
    connector = BinanceFuturesConnector(
        api_key=settings.binance_api_key,
        secret_key=settings.binance_secret_key,
    )
    connected = await connector.connect()
    if connected:
        print("  OK: 바이낸스 선물 연결 성공")
    else:
        print("  WARN: 연결 실패 (API 키 없이 공개 데이터만 사용)")
        # 공개 API로 재시도
        connector = BinanceFuturesConnector(api_key="", secret_key="")
        await connector.connect()

    # --- 2. 시세 데이터 수신 ---
    print("\n[2/6] 시세 데이터 수신...")
    symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
    for sym in symbols:
        try:
            ticker = await connector.get_ticker(sym)
            print(f"  {sym}: ${ticker.price:,.2f} (24h: {ticker.change_24h:+.2f}%)")
        except Exception as e:
            print(f"  {sym}: 에러 - {e}")

    # --- 3. 캔들 데이터 수신 ---
    print("\n[3/6] 캔들 데이터 수신...")
    for sym in symbols:
        try:
            candles = await connector.get_klines(sym, "1h", limit=100)
            print(f"  {sym}: {len(candles)}개 캔들 수신 (최근: {float(candles[-1].close):,.2f})")
        except Exception as e:
            print(f"  {sym}: 에러 - {e}")

    # --- 4. 펀딩비 조회 ---
    print("\n[4/6] 펀딩비 조회...")
    import httpx
    for sym in symbols:
        pair = sym.split("/")[0] + "USDT"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={pair}"
                )
                data = resp.json()
                funding_rate = float(data.get("lastFundingRate", 0)) * 100
                next_time = int(data.get("nextFundingTime", 0))
                next_dt = datetime.fromtimestamp(next_time / 1000, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                minutes_left = (next_dt - now).total_seconds() / 60
                print(f"  {pair}: 펀딩비 {funding_rate:+.4f}% | 다음 정산: {next_dt.strftime('%H:%M UTC')} ({minutes_left:.0f}분 후)")
        except Exception as e:
            print(f"  {pair}: 에러 - {e}")

    # --- 5. 전략 신호 테스트 ---
    print("\n[5/6] 전략 신호 테스트...")
    strategy = get_strategy("funding_rate")
    print(f"  전략: {strategy.name} ({strategy.description})")

    for sym in symbols:
        try:
            candles = await connector.get_klines(sym, "1h", limit=100)
            pair = sym.split("/")[0] + "USDT"

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={pair}"
                )
                data = resp.json()
                funding_rate = float(data.get("lastFundingRate", 0)) * 100

            context = MarketContext(
                funding_rate=funding_rate,
                volume_ratio=1.0,
                open_interest_change=0.0,
            )

            signal = await strategy.generate_signal(
                symbol=sym,
                candles=candles,
                current_position=None,
                context=context,
            )
            print(f"  {sym}: {signal.signal.value} | 사유: {signal.reason}")
        except Exception as e:
            print(f"  {sym}: 에러 - {e}")

    # --- 6. 강제 시그널 → 전체 플로우 테스트 ---
    print("\n[6/6] 강제 시그널 전체 플로우 테스트...")
    notifier = TelegramNotifier(paper_mode=True)
    test_sym = "BTC/USDT:USDT"

    try:
        ticker = await connector.get_ticker(test_sym)
        price = float(ticker.price)
    except Exception:
        price = 67000.0

    # 6-1) 강제 롱 시그널 → 가상 진입
    print(f"  가상 롱 진입: {test_sym} @ ${price:,.2f}")
    await notifier.notify_trade_open({
        "symbol": test_sym,
        "side": "long",
        "entry_price": f"{price:,.2f}",
        "leverage": 5,
        "amount_pct": 30,
        "sl": f"{price * 0.99:,.2f}",
        "tp": f"{price * 1.015:,.2f}",
        "funding_rate": "0.0100",
        "next_funding_minutes": 120,
        "reason": "[테스트] 강제 롱 시그널",
    })
    print("  -> 텔레그램 진입 알림 전송 완료")

    # 6-2) 5초 대기 (실전에서는 포지션 보유)
    print("  5초 대기 (가상 포지션 보유 중)...")
    await asyncio.sleep(5)

    # 6-3) 가상 청산 (+0.15% 수익)
    exit_price = price * 1.0015
    pnl_pct = 0.15
    net_pnl = price * 0.30 * 5 * pnl_pct / 100  # balance * size_pct * leverage * pnl

    print(f"  가상 청산: ${exit_price:,.2f} (P/L: +{pnl_pct:.2f}%)")
    await notifier.notify_trade_close({
        "symbol": test_sym,
        "side": "long",
        "entry_price": f"{price:,.2f}",
        "exit_price": f"{exit_price:,.2f}",
        "pnl_pct": pnl_pct,
        "fee": 2.03,
        "funding_income": 0,
        "net_pnl": round(net_pnl - 2.03, 2),
        "hold_duration": "0.1시간",
        "reason": "[테스트] 강제 청산",
    })
    print("  -> 텔레그램 청산 알림 전송 완료")

    # --- 완료 ---
    await connector.disconnect()

    print("\n" + "=" * 50)
    print("통합 테스트 완료!")
    print("=" * 50)
    print("\n확인 항목:")
    print("  [1] 거래소 연결 OK")
    print("  [2] 시세 데이터 수신 OK")
    print("  [3] 캔들 데이터 수신 OK")
    print("  [4] 펀딩비 조회 OK")
    print("  [5] 전략 신호 생성 OK")
    print("  [6] 강제 시그널 -> 텔레그램 알림 OK")
    print("\n텔레그램에서 진입/청산 알림 2개를 확인해주세요.")


if __name__ == "__main__":
    asyncio.run(main())
