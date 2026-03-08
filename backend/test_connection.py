"""
Exchange connection test script
- .env에서 API 키를 읽어서 테스트
- binanceusdm 선물 심볼 형식: BTC/USDT:USDT
"""

import asyncio
import sys
import io
import os
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()

from app.services.exchange.binance import BinanceFuturesConnector


async def main():
    api_key = os.getenv("BINANCE_API_KEY", "")
    secret_key = os.getenv("BINANCE_SECRET_KEY", "")

    if not api_key or not secret_key:
        print("ERROR: BINANCE_API_KEY / BINANCE_SECRET_KEY not found in .env")
        return

    connector = BinanceFuturesConnector(
        api_key=api_key,
        secret_key=secret_key,
        testnet=False,
    )

    print("=" * 50)
    print("BINANCE FUTURES CONNECTION TEST (REAL - READ ONLY)")
    print("=" * 50)

    # 1. Connect
    print("\n1. Connecting...")
    connected = await connector.connect()
    print(f"   Status: {'OK' if connected else 'FAILED'}")

    if not connected:
        print("   Connection failed")
        await connector.disconnect()
        return

    # 2. BTC Ticker
    print("\n2. BTC/USDT:USDT Ticker...")
    ticker = await connector.get_ticker("BTC/USDT:USDT")
    print(f"   Price:    ${ticker.price}")
    print(f"   24h:      {ticker.change_24h:.2f}%")
    print(f"   Volume:   {ticker.volume_24h} USDT")

    # 3. ETH Ticker
    print("\n3. ETH/USDT:USDT Ticker...")
    ticker_eth = await connector.get_ticker("ETH/USDT:USDT")
    print(f"   Price:    ${ticker_eth.price}")

    # 4. Candles
    print("\n4. BTC 1h Candles (last 3)...")
    candles = await connector.get_klines("BTC/USDT:USDT", "1h", limit=3)
    for c in candles:
        print(f"   O:{c.open} H:{c.high} L:{c.low} C:{c.close}")

    # 5. Balance
    print("\n5. Balance...")
    try:
        balance = await connector.get_balance()
        print(f"   Total:     {balance.total} USDT")
        print(f"   Available: {balance.available} USDT")
    except Exception as e:
        print(f"   Balance check skipped: {e}")

    # 6. Positions
    print("\n6. Active Positions...")
    try:
        positions = await connector.get_all_positions()
        if positions:
            for p in positions:
                print(f"   {p.symbol} {p.side} x{p.leverage}")
        else:
            print("   No active positions")
    except Exception as e:
        print(f"   Position check skipped: {e}")

    await connector.disconnect()
    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(main())
