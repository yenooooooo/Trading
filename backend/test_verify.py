"""프롬프트3 전체 파일 검증"""
import asyncio
from decimal import Decimal
from app.services.risk.risk_manager import (
    SmallAccountRiskManager, RiskCheckResult, RiskConfig,
)
from app.services.trading.trading_engine import TradingEngine

passed = 0
failed = 0

def ok(name, cond=True, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [OK] {name}" + (f" -> {detail}" if detail else ""))
    else:
        failed += 1
        print(f"  [FAIL] {name}" + (f" -> {detail}" if detail else ""))

async def main():
    rm = SmallAccountRiskManager()

    # ========== 1. risk_manager.py 클래스 구조 ==========
    print("=" * 55)
    print("  1/8  risk_manager.py 클래스 구조")
    print("=" * 55)
    ok("SmallAccountRiskManager", isinstance(rm, SmallAccountRiskManager))
    ok("RiskCheckResult", hasattr(RiskCheckResult, "approved"))
    ok("RiskConfig", hasattr(RiskConfig, "max_leverage"))

    for attr in ["config", "fee_calc"]:
        ok(f"rm.{attr}", hasattr(rm, attr))

    for method in ["validate_order", "check_daily_limit", "check_weekly_limit",
                    "check_consecutive_losses", "check_fee_worthiness",
                    "get_adjusted_position_size"]:
        ok(f"method: {method}", hasattr(rm, method))

    # ========== 2. RiskConfig 기본값 ==========
    print()
    print("=" * 55)
    print("  2/8  RiskConfig 기본값")
    print("=" * 55)
    c = rm.config
    ok("max_risk 5%", c.max_risk_per_trade == 0.05)
    ok("min_risk 3%", c.min_risk_per_trade == 0.03)
    ok("daily_loss 8%", c.daily_loss_limit == 0.08)
    ok("weekly_loss 15%", c.weekly_loss_limit == 0.15)
    ok("max_leverage 5x", c.max_leverage == 5)
    ok("max_pos_small 1", c.max_positions_small == 1)
    ok("max_pos_medium 2", c.max_positions_medium == 2)
    ok("max_daily_trades 3", c.max_daily_trades == 3)
    ok("consec_reduce 3", c.consecutive_loss_reduce == 3)
    ok("consec_stop 5", c.consecutive_loss_stop == 5)
    ok("reduce_factor 0.5", c.reduce_factor == 0.5)
    ok("min_profit_fee 2.0", c.min_profit_fee_ratio == 2.0)

    # ========== 3. validate_order 승인 ==========
    print()
    print("=" * 55)
    print("  3/8  validate_order 승인")
    print("=" * 55)
    base = dict(balance=Decimal("200"), position_size_usdt=Decimal("300"),
                leverage=3, side="long", expected_profit_pct=0.5,
                open_positions=[], today_trades=[], today_pnl=0.0,
                week_pnl=0.0, recent_trades=[])
    r = await rm.validate_order(**base)
    ok("approved", r.approved)
    ok("reason OK", r.reason == "OK")
    ok("warnings list", isinstance(r.warnings, list))
    ok("adjusted_size None", r.adjusted_size is None)

    # ========== 4. 거부 케이스 ==========
    print()
    print("=" * 55)
    print("  4/8  거부 케이스 (8가지)")
    print("=" * 55)

    # 4-1) 레버리지 초과
    r = await rm.validate_order(**{**base, "leverage": 7})
    ok("lev>5 rejected", not r.approved, r.reason[:30])

    # 4-2) 일일 손실
    r = await rm.validate_order(**{**base, "today_pnl": -20.0})
    ok("daily loss rejected", not r.approved, r.reason[:30])

    # 4-3) 주간 손실
    r = await rm.validate_order(**{**base, "week_pnl": -35.0})
    ok("weekly loss rejected", not r.approved, r.reason[:30])

    # 4-4) 일일 거래 횟수
    r = await rm.validate_order(**{**base, "today_trades": [1, 2, 3]})
    ok("daily trades rejected", not r.approved, r.reason[:30])

    # 4-5) 동시 포지션 ($100)
    r = await rm.validate_order(**{**base, "balance": Decimal("100"), "open_positions": ["a"]})
    ok("pos limit rejected", not r.approved, r.reason[:30])

    # 4-6) 5연패
    r = await rm.validate_order(**{**base, "recent_trades": [{"pnl": -i} for i in range(1, 6)]})
    ok("5 losses rejected", not r.approved, r.reason[:30])

    # 4-7) 수수료 수익 부족
    r = await rm.validate_order(**{**base, "expected_profit_pct": 0.1})
    ok("fee unworthy rejected", not r.approved, r.reason[:30])

    # 4-8) 잔고 부족
    r = await rm.validate_order(**{**base, "balance": Decimal("10"), "position_size_usdt": Decimal("100")})
    ok("balance insuf rejected", not r.approved, r.reason[:30])

    # ========== 5. check_daily_limit ==========
    print()
    print("=" * 55)
    print("  5/8  check_daily_limit")
    print("=" * 55)
    ok("profit -> pass", await rm.check_daily_limit(200.0, 10.0))
    ok("-$10 < 8% -> pass", await rm.check_daily_limit(200.0, -10.0))
    ok("-$16 = 8% -> pass", await rm.check_daily_limit(200.0, -15.9))
    ok("-$20 > 8% -> fail", not await rm.check_daily_limit(200.0, -20.0))
    ok("$0 -> pass", await rm.check_daily_limit(200.0, 0.0))

    # ========== 6. check_consecutive_losses ==========
    print()
    print("=" * 55)
    print("  6/8  check_consecutive_losses")
    print("=" * 55)
    ok("empty", (await rm.check_consecutive_losses([]))["action"] == "none")
    ok("0 loss", (await rm.check_consecutive_losses([{"pnl": 5}]))["action"] == "none")
    ok("1 loss", (await rm.check_consecutive_losses([{"pnl": -1}]))["action"] == "none")
    ok("2 loss", (await rm.check_consecutive_losses([{"pnl": -1}, {"pnl": -2}]))["action"] == "none")
    ok("3 loss -> reduce", (await rm.check_consecutive_losses([{"pnl": -1}, {"pnl": -2}, {"pnl": -3}]))["action"] == "reduce")
    ok("4 loss -> reduce", (await rm.check_consecutive_losses([{"pnl": -i} for i in range(1, 5)]))["action"] == "reduce")
    ok("5 loss -> stop", (await rm.check_consecutive_losses([{"pnl": -i} for i in range(1, 6)]))["action"] == "stop")
    ok("win resets", (await rm.check_consecutive_losses([{"pnl": -3}, {"pnl": -2}, {"pnl": 5}, {"pnl": -1}]))["count"] == 1)

    # 3연패 → 포지션 축소 반영
    r = await rm.validate_order(**{**base, "recent_trades": [{"pnl": -5}, {"pnl": -3}, {"pnl": -2}]})
    ok("3loss approved", r.approved)
    ok("adjusted_size set", r.adjusted_size is not None, f"${r.adjusted_size}")
    ok("adjusted = 50%", r.adjusted_size == Decimal("150.00"))
    ok("warning has reduce", any("축소" in w for w in r.warnings))

    # get_adjusted_position_size 직접
    ok("adjust 3loss", rm.get_adjusted_position_size(Decimal("400"), 3) == Decimal("200.00"))
    ok("adjust 4loss", rm.get_adjusted_position_size(Decimal("400"), 4) == Decimal("200.00"))
    ok("no adjust 2loss", rm.get_adjusted_position_size(Decimal("400"), 2) == Decimal("400"))

    # ========== 7. check_fee_worthiness ==========
    print()
    print("=" * 55)
    print("  7/8  check_fee_worthiness")
    print("=" * 55)
    ok("0.5% worthy", await rm.check_fee_worthiness(0.5, 1000, 3))
    ok("0.2% worthy", await rm.check_fee_worthiness(0.2, 1000, 3))
    ok("0.16% worthy", await rm.check_fee_worthiness(0.16, 1000, 3))
    ok("0.15% not worthy", not await rm.check_fee_worthiness(0.15, 1000, 3))
    ok("0.1% not worthy", not await rm.check_fee_worthiness(0.1, 1000, 3))
    ok("0.01% not worthy", not await rm.check_fee_worthiness(0.01, 1000, 1))

    # ========== 8. trading_engine.py 구조 ==========
    print()
    print("=" * 55)
    print("  8/8  trading_engine.py 구조")
    print("=" * 55)
    ok("TradingEngine import", TradingEngine is not None)

    # 필수 메서드
    for method in ["execute_signal", "get_position", "get_all_positions",
                    "update_pnl", "reset_daily", "reset_weekly"]:
        ok(f"method: {method}", hasattr(TradingEngine, method))

    # 내부 메서드
    for method in ["_open_position", "_close_position"]:
        ok(f"internal: {method}", hasattr(TradingEngine, method))

    # risk_manager 통합 확인 (소스 코드에 risk_manager 참조)
    import inspect
    src = inspect.getsource(TradingEngine._open_position)
    ok("risk_manager in _open_position", "risk_manager" in src or "validate_order" in src)
    ok("adjusted_size in _open_position", "adjusted_size" in src)
    ok("risk_result in _open_position", "risk_result" in src)

    # update_pnl 동작
    class FakeConnector:
        pass
    eng = TradingEngine(connector=FakeConnector())
    ok("initial pnl 0", eng._today_pnl == 0.0)
    eng.update_pnl(-5.0)
    ok("pnl after loss", eng._today_pnl == -5.0)
    ok("week pnl", eng._week_pnl == -5.0)
    ok("recent_trades", len(eng._recent_trades) == 1)
    eng.update_pnl(10.0)
    ok("pnl after win", eng._today_pnl == 5.0)
    eng.reset_daily()
    ok("reset daily", eng._today_pnl == 0.0 and len(eng._today_trades) == 0)
    ok("week pnl kept", eng._week_pnl == 5.0)
    eng.reset_weekly()
    ok("reset weekly", eng._week_pnl == 0.0)

    print()
    print("=" * 55)
    print(f"  RESULT: {passed} PASSED / {failed} FAILED")
    print("=" * 55)

asyncio.run(main())
