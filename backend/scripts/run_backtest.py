"""
백테스트 실행 스크립트 (v5)
- 변동성 돌파: BTC+ETH, 90일, 1시간봉, $200 시드, 3x
- 추세추종: BTC+ETH, 365일(최대 가능), 4시간봉, $200 시드, 3x
- 펀딩비 수확: 이미 검증 완료 (재실행 불필요)

실행: cd backend && python scripts/run_backtest.py
"""

import sys
import os
import io
import asyncio

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from collections import defaultdict
from decimal import Decimal
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
import ccxt.async_support as ccxt
from app.services.exchange.base import Candle
from app.services.strategy.base_strategy import MarketContext
from app.services.strategy.registry import get_strategy
from app.services.backtest.backtest_engine import BacktestEngine, BacktestResult


SEED_USD = 200.0
SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT"]

STRATEGY_NAMES = {
    "funding_rate": "펀딩비 수확",
    "volatility_breakout": "변동성 돌파",
    "trend_following": "추세추종",
}


# --- 데이터 수집 ---

async def fetch_candles(exchange, symbol: str, timeframe: str, days: int) -> list[Candle]:
    all_ohlcv = []
    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    limit = 1000

    while True:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1
        if len(ohlcv) < limit:
            break
        await asyncio.sleep(0.1)

    seen = set()
    unique = []
    for c in all_ohlcv:
        if c[0] not in seen:
            seen.add(c[0])
            unique.append(c)
    unique.sort(key=lambda x: x[0])

    return [
        Candle(
            timestamp=int(c[0]),
            open=Decimal(str(c[1])),
            high=Decimal(str(c[2])),
            low=Decimal(str(c[3])),
            close=Decimal(str(c[4])),
            volume=Decimal(str(c[5])),
        )
        for c in unique
    ]


async def fetch_funding_rates(exchange, symbol: str, candles: list[Candle]) -> list[float]:
    since = candles[0].timestamp
    all_funding = []
    limit = 1000

    try:
        while True:
            raw = await exchange.fetch_funding_rate_history(symbol, since=since, limit=limit)
            if not raw:
                break
            all_funding.extend(raw)
            since = raw[-1]["timestamp"] + 1
            if len(raw) < limit:
                break
            await asyncio.sleep(0.2)
    except Exception:
        return [0.0] * len(candles)

    funding_map = {}
    for f in all_funding:
        rate = f.get("fundingRate", 0) or 0
        funding_map[f["timestamp"]] = float(rate) * 100

    funding_timestamps = sorted(funding_map.keys())
    funding_rates = []
    for candle in candles:
        ct = candle.timestamp
        rate = 0.0
        for ft in reversed(funding_timestamps):
            if ft <= ct:
                rate = funding_map[ft]
                break
        funding_rates.append(rate)

    return funding_rates


# --- 백테스트 실행 ---

async def run_single_backtest(strategy_name, candles, funding_rates, timeframe, leverage):
    strategy = get_strategy(strategy_name)
    engine = BacktestEngine(
        strategy=strategy,
        initial_balance=SEED_USD,
        fee_rate_taker=0.0004,
        fee_rate_maker=0.0002,
        slippage_pct=0.03,
        leverage=leverage,
    )

    def build_context(candle_window, idx, fr_list):
        fr = fr_list[idx] if fr_list and idx < len(fr_list) else 0.0
        vol_ratio = 1.0
        if len(candle_window) >= 21:
            vols = [float(c.volume) for c in candle_window]
            avg_vol = sum(vols[-21:-1]) / 20
            if avg_vol > 0:
                vol_ratio = vols[-1] / avg_vol
        return MarketContext(
            candles=candle_window,
            funding_rate=fr,
            predicted_funding=fr,
            volume_ratio=vol_ratio,
            spread_pct=0.01,
            open_interest_change=0.0,
            long_short_ratio=1.0,
        )

    result = await engine.run(
        candles=candles,
        symbol=candles[0].timestamp if candles else "UNKNOWN",
        timeframe=timeframe,
        funding_rates=funding_rates,
        context_builder=build_context,
    )
    return result


# --- PnL 분리 계산 ---

def calc_pnl_breakdown(r: BacktestResult) -> dict:
    gross_pnl = sum(t.pnl_gross for t in r.trades)
    funding_pnl = -sum(t.funding_paid for t in r.trades)
    fee_pnl = sum(t.fee_paid for t in r.trades)
    slippage_pnl = sum(t.slippage_cost for t in r.trades)
    net_pnl = sum(t.pnl_net for t in r.trades)

    return {
        "gross_pnl": gross_pnl,
        "funding_pnl": funding_pnl,
        "fee_pnl": fee_pnl,
        "slippage_pnl": slippage_pnl,
        "net_pnl": net_pnl,
        "gross_return": (gross_pnl / SEED_USD * 100) if SEED_USD > 0 else 0,
        "funding_return": (funding_pnl / SEED_USD * 100) if SEED_USD > 0 else 0,
        "fee_return": (fee_pnl / SEED_USD * 100) if SEED_USD > 0 else 0,
        "net_return": (net_pnl / SEED_USD * 100) if SEED_USD > 0 else 0,
        "fee_to_gross_ratio": (fee_pnl / gross_pnl * 100) if gross_pnl > 0 else 999.9,
    }


def calc_monthly_returns(result: BacktestResult) -> dict[str, float]:
    monthly = defaultdict(float)
    for t in result.trades:
        dt = datetime.fromtimestamp(t.exit_time / 1000, tz=timezone.utc)
        key = dt.strftime("%Y-%m")
        monthly[key] += t.pnl_net
    return dict(sorted(monthly.items()))


# --- 결과 출력 ---

def print_result(name: str, symbol: str, r: BacktestResult, config: str = ""):
    monthly = calc_monthly_returns(r)
    pnl = calc_pnl_breakdown(r)

    print(f"\n{'='*60}")
    print(f"  {name} | {symbol} {config}")
    print(f"{'='*60}")
    print(f"  {'시드':>20}: ${SEED_USD:.2f}")
    print(f"  {'최종 잔고':>20}: ${r.final_balance:.2f}")

    print(f"\n  --- PnL 분리 ---")
    print(f"  {'매매 손익 (gross)':>20}: ${pnl['gross_pnl']:>+8.2f} ({pnl['gross_return']:>+6.2f}%)")
    print(f"  {'펀딩비 손익':>20}: ${pnl['funding_pnl']:>+8.2f} ({pnl['funding_return']:>+6.2f}%)")
    print(f"  {'수수료 (차감)':>20}: ${pnl['fee_pnl']:>8.2f} ({pnl['fee_return']:>6.2f}%)")
    print(f"  {'슬리피지':>20}: ${pnl['slippage_pnl']:>8.2f}")
    print(f"  {'순수익 (net)':>20}: ${pnl['net_pnl']:>+8.2f} ({pnl['net_return']:>+6.2f}%)")
    print(f"  {'수수료/매매수익':>20}: {pnl['fee_to_gross_ratio']:.1f}%")

    if pnl['gross_pnl'] < 0:
        print(f"  {'':>20}  [!] 매매 자체 손실")
    elif pnl['gross_pnl'] > 0 and pnl['funding_pnl'] > pnl['gross_pnl']:
        print(f"  {'':>20}  [!] 펀딩비 의존")

    print(f"\n  --- 거래 통계 ---")
    print(f"  {'승률':>20}: {r.win_rate:.1f}%")
    print(f"  {'총 거래':>20}: {r.total_trades}회 (승 {r.winning_trades} / 패 {r.losing_trades})")
    print(f"  {'MDD':>20}: {r.max_drawdown:.1f}% (${r.max_drawdown_usd:.2f})")
    print(f"  {'샤프 비율':>20}: {r.sharpe_ratio:.2f}")
    print(f"  {'Profit Factor':>20}: {r.profit_factor:.2f}")
    print(f"  {'평균 보유':>20}: {r.avg_holding_bars:.1f} 캔들")

    if r.trades:
        best = max(r.trades, key=lambda t: t.pnl_net)
        worst = min(r.trades, key=lambda t: t.pnl_net)
        print(f"\n  {'최대 수익 거래':>20}: ${best.pnl_net:.2f} ({best.return_pct:+.1f}%) [{best.side}] {best.holding_bars}봉")
        print(f"  {'최대 손실 거래':>20}: ${worst.pnl_net:.2f} ({worst.return_pct:+.1f}%) [{worst.side}] {worst.holding_bars}봉")

    if monthly:
        print(f"\n  월별 수익:")
        for month, pnl_m in monthly.items():
            pct = pnl_m / SEED_USD * 100
            bar = "+" * min(int(abs(pct)), 50) if pct > 0 else "-" * min(int(abs(pct)), 50)
            print(f"    {month}: ${pnl_m:>8.2f} ({pct:>+6.2f}%) {bar}")

    if r.warnings:
        print(f"\n  [경고]")
        for w in r.warnings:
            print(f"    - {w}")

    verdict = judge_strategy(r)
    print(f"\n  {'판단':>20}: {verdict['emoji']} {verdict['verdict']}")
    for reason in verdict["reasons"]:
        print(f"    - {reason}")


def judge_strategy(r: BacktestResult) -> dict:
    pnl = calc_pnl_breakdown(r)
    reasons = []

    net_ret = pnl["net_return"]
    reasons.append(f"순수익률 {net_ret:+.1f}%")
    if pnl["gross_pnl"] > 0:
        reasons.append(f"매매 손익 ${pnl['gross_pnl']:+.2f} (매매 실력 있음)")
    else:
        reasons.append(f"매매 손익 ${pnl['gross_pnl']:+.2f} (매매 손실)")
    reasons.append(f"MDD {r.max_drawdown:.1f}%")
    reasons.append(f"샤프 {r.sharpe_ratio:.2f}")
    reasons.append(f"거래 {r.total_trades}회 / 승률 {r.win_rate:.0f}%")

    if pnl["net_pnl"] <= 0:
        return {"verdict": "비권장", "emoji": "[X]", "reasons": reasons}
    if pnl["gross_pnl"] > 0 and r.max_drawdown < 25 and r.sharpe_ratio > 0.8:
        return {"verdict": "실전 투입 가능", "emoji": "[O]", "reasons": reasons}
    return {"verdict": "조건부 가능", "emoji": "[~]", "reasons": reasons}


# --- 메인 ---

async def main():
    print("=" * 70)
    print("  백테스트 v5 - 전략별 맞춤 조건")
    print("  변동성 돌파: 90일, 1h, 3x | 추세추종: 365일, 4h, 3x")
    print(f"  시드: ${SEED_USD:.2f}")
    print("=" * 70)

    session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    )
    exchange = ccxt.binanceusdm({
        "enableRateLimit": True,
        "session": session,
    })

    all_results = {}

    try:
        await exchange.load_markets()

        # === 변동성 돌파: 90일, 1시간봉, 3x ===
        print(f"\n{'='*50}")
        print("  [변동성 돌파] 90일, 1시간봉, 3x 레버리지")
        print(f"{'='*50}")

        for symbol in SYMBOLS:
            short = symbol.split("/")[0]
            print(f"\n  [{short}] 데이터 수집 중 (90일, 1h)...")
            candles = await fetch_candles(exchange, symbol, "1h", 90)
            funding = await fetch_funding_rates(exchange, symbol, candles)
            print(f"  [{short}] {len(candles)}개 캔들")

            print(f"  [{short}/volatility_breakout] 실행 중...")
            try:
                result = await run_single_backtest("volatility_breakout", candles, funding, "1h", 3)
                all_results[("volatility_breakout", symbol)] = result
                print(f"  [{short}/volatility_breakout] 완료 - {result.total_trades}회 거래")
            except Exception as e:
                print(f"  [{short}/volatility_breakout] 실패: {e}")
                import traceback
                traceback.print_exc()

        # === 추세추종: 365일, 4시간봉, 3x ===
        print(f"\n{'='*50}")
        print("  [추세추종] 365일, 4시간봉, 3x 레버리지")
        print(f"{'='*50}")

        for symbol in SYMBOLS:
            short = symbol.split("/")[0]
            print(f"\n  [{short}] 데이터 수집 중 (365일, 4h)...")
            candles = await fetch_candles(exchange, symbol, "4h", 365)
            funding = await fetch_funding_rates(exchange, symbol, candles)
            actual_days = 0
            if candles:
                actual_days = (candles[-1].timestamp - candles[0].timestamp) / (1000 * 86400)
            print(f"  [{short}] {len(candles)}개 캔들 ({actual_days:.0f}일)")

            print(f"  [{short}/trend_following] 실행 중...")
            try:
                result = await run_single_backtest("trend_following", candles, funding, "4h", 3)
                all_results[("trend_following", symbol)] = result
                print(f"  [{short}/trend_following] 완료 - {result.total_trades}회 거래")
            except Exception as e:
                print(f"  [{short}/trend_following] 실패: {e}")
                import traceback
                traceback.print_exc()

        # --- 개별 결과 출력 ---
        for (strat_name, symbol), result in all_results.items():
            short = symbol.split("/")[0]
            if strat_name == "volatility_breakout":
                config = "(90일, 1h, 3x)"
            else:
                config = "(365일, 4h, 3x)"
            print_result(STRATEGY_NAMES[strat_name], short, result, config)

        # --- 종합 요약 ---
        print(f"\n{'='*110}")
        print("  종합 요약 (v5)")
        print(f"{'='*110}")
        print(f"  {'전략':<14} {'종목':>5} {'기간':>5} "
              f"{'매매PnL':>9} {'펀딩PnL':>9} {'수수료':>8} {'순PnL':>9} "
              f"{'순수익률':>8} {'MDD':>6} {'승률':>5} {'거래':>4} {'보유':>5} {'샤프':>5} {'수/매':>5}")
        print(f"  {'-'*107}")

        # 펀딩비 수확 (v4 결과 참조)
        print(f"  {'펀딩비 수확':<14} {'BTC':>5} {'90일':>5} "
              f"$  +2.70 $ +12.05 $  0.91 $ +14.29  +7.14%   0.9%  100%   9    5h  2.78   34% [T] (v4)")
        print(f"  {'펀딩비 수확':<14} {'ETH':>5} {'90일':>5} "
              f"$ +10.52 $ +27.77 $  1.70 $ +37.43 +18.72%   1.4%   81%  16    3h  3.00   16% [T] (v4)")

        for (strat_name, symbol), result in all_results.items():
            sn = STRATEGY_NAMES[strat_name][:7]
            short = symbol.split("/")[0]
            pnl = calc_pnl_breakdown(result)
            trade_mark = "T" if pnl["gross_pnl"] > 0 else "F" if pnl["gross_pnl"] < 0 else "-"
            period = "90일" if strat_name == "volatility_breakout" else "365일"

            print(
                f"  {sn:<14} {short:>5} {period:>5} "
                f"${pnl['gross_pnl']:>+7.2f} "
                f"${pnl['funding_pnl']:>+7.2f} "
                f"${pnl['fee_pnl']:>6.2f} "
                f"${pnl['net_pnl']:>+7.2f} "
                f"{pnl['net_return']:>+7.2f}% "
                f"{result.max_drawdown:>5.1f}% "
                f"{result.win_rate:>4.0f}% "
                f"{result.total_trades:>3} "
                f"{result.avg_holding_bars:>4.0f}h "
                f"{result.sharpe_ratio:>5.2f} "
                f"{pnl['fee_to_gross_ratio']:>4.0f}% "
                f"[{trade_mark}]"
            )

        print(f"\n  [T] = 매매 자체 수익  [F] = 매매 손실  [-] = 거래 없음")
        print(f"\n  === 최종 판단 기준 ===")
        print(f"  [O] 실전 투입 가능 = gross PnL 양수 + MDD < 25% + 샤프 > 0.8")
        print(f"  [~] 조건부 가능   = net PnL 양수이나 일부 미충족")
        print(f"  [X] 비권장        = net PnL 음수")

    finally:
        await exchange.close()
        if not session.closed:
            await session.close()

    print()


if __name__ == "__main__":
    asyncio.run(main())
