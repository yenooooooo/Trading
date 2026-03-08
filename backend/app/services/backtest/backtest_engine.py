"""
백테스트 엔진
- 이벤트 기반: on_candle -> generate_signal -> execute -> update
- 소액($50~400) 현실적 시뮬레이션: 수수료 + 슬리피지 + 펀딩비
- 사용처: 전략 검증, 파라미터 최적화
"""

import random
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import structlog

from app.services.exchange.base import Candle
from app.services.strategy.base_strategy import (
    BaseStrategy, TradeSignal, SignalType, MarketContext,
)
from app.services.strategy.fee_calculator import FeeCalculator

logger = structlog.get_logger()


# --- 백테스트 거래 기록 ---

@dataclass
class BacktestTrade:
    """개별 거래 기록"""
    trade_id: int = 0
    side: str = ""                    # 'long' | 'short'
    entry_time: int = 0               # 진입 타임스탬프
    exit_time: int = 0                # 청산 타임스탬프
    entry_price: float = 0.0
    exit_price: float = 0.0
    size_usdt: float = 0.0            # 포지션 명목 가치
    pnl_gross: float = 0.0            # 총수익
    pnl_net: float = 0.0              # 순수익 (수수료 차감)
    fee_paid: float = 0.0             # 왕복 수수료
    funding_paid: float = 0.0         # 펀딩비
    slippage_cost: float = 0.0        # 슬리피지 비용
    return_pct: float = 0.0           # 수익률 (%)
    holding_bars: int = 0             # 보유 캔들 수
    signal_strength: float = 0.0
    signal_reason: str = ""


# --- 백테스트 결과 ---

@dataclass
class BacktestResult:
    """백테스트 결과 (소액 핵심 지표 포함)"""
    # 기본 정보
    symbol: str = ""
    timeframe: str = ""
    period: str = ""
    initial_balance: float = 0.0
    final_balance: float = 0.0

    # 수익률
    total_return: float = 0.0                # 총수익률 (%)
    total_return_after_fees: float = 0.0     # 수수료 차감 후 순수익률 (%)

    # 소액 핵심 지표
    total_fees_paid: float = 0.0             # 총 수수료 ($)
    total_funding_paid: float = 0.0          # 총 펀딩비 ($)
    total_slippage_cost: float = 0.0         # 총 슬리피지 ($)
    fee_to_profit_ratio: float = 0.0         # 수수료/총수익 비율

    # 리스크 지표
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0                # MDD (%)
    max_drawdown_usd: float = 0.0            # MDD ($)

    # 거래 통계
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_holding_bars: float = 0.0

    # 상세 데이터
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """API 응답용 딕셔너리 변환"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "period": self.period,
            "initial_balance": self.initial_balance,
            "final_balance": round(self.final_balance, 2),
            "total_return": round(self.total_return, 2),
            "total_return_after_fees": round(self.total_return_after_fees, 2),
            "total_fees_paid": round(self.total_fees_paid, 2),
            "total_funding_paid": round(self.total_funding_paid, 2),
            "total_slippage_cost": round(self.total_slippage_cost, 2),
            "fee_to_profit_ratio": round(self.fee_to_profit_ratio, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "sortino_ratio": round(self.sortino_ratio, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "max_drawdown_usd": round(self.max_drawdown_usd, 2),
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "avg_holding_bars": round(self.avg_holding_bars, 1),
            "equity_curve": self.equity_curve,
            "warnings": self.warnings,
            "trades": [
                {
                    "id": t.trade_id,
                    "side": t.side,
                    "entry_time": t.entry_time,
                    "exit_time": t.exit_time,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "size_usdt": round(t.size_usdt, 2),
                    "pnl_net": round(t.pnl_net, 2),
                    "fee_paid": round(t.fee_paid, 4),
                    "return_pct": round(t.return_pct, 2),
                    "holding_bars": t.holding_bars,
                    "reason": t.signal_reason,
                }
                for t in self.trades
            ],
        }


# --- 내부 포지션 상태 ---

@dataclass
class _Position:
    """시뮬레이션 포지션"""
    side: str = ""               # 'long' | 'short'
    entry_price: float = 0.0
    size_usdt: float = 0.0       # 명목 가치
    entry_time: int = 0
    entry_bar: int = 0
    entry_fee: float = 0.0
    slippage_cost: float = 0.0
    funding_accumulated: float = 0.0
    signal_strength: float = 0.0
    signal_reason: str = ""


class BacktestEngine:
    """
    이벤트 기반 백테스트 엔진

    흐름: candle 순회 → 전략 신호 → 주문 시뮬 → 포지션 갱신
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_balance: float = 200.0,
        fee_rate_maker: float = 0.0002,
        fee_rate_taker: float = 0.0004,
        slippage_pct: float = 0.03,
        leverage: int = 3,
    ):
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.fee_maker = fee_rate_maker
        self.fee_taker = fee_rate_taker
        self.slippage_pct = slippage_pct    # 기본 0.03% (0.01~0.05 범위)
        self.leverage = leverage

        # 시뮬레이션 상태
        self.balance = initial_balance
        self.position: _Position | None = None
        self.trades: list[BacktestTrade] = []
        self.equity_curve: list[dict] = []
        self.trade_counter = 0

    # --- 메인 실행 ---

    async def run(
        self,
        candles: list[Candle],
        symbol: str = "BTC/USDT:USDT",
        timeframe: str = "1h",
        funding_rates: list[float] | None = None,
        context_builder: callable = None,
    ) -> BacktestResult:
        """
        백테스트 실행

        Args:
            candles: OHLCV 캔들 (과거→현재)
            symbol: 심볼
            timeframe: 타임프레임
            funding_rates: 캔들별 펀딩비 (없으면 0)
            context_builder: MarketContext 생성 함수 (커스텀)
        """
        if len(candles) < self.strategy.min_candles:
            logger.warning("insufficient_candles",
                           need=self.strategy.min_candles, got=len(candles))
            return BacktestResult(
                symbol=symbol, timeframe=timeframe,
                initial_balance=self.initial_balance,
                warnings=["캔들 수 부족"],
            )

        # 상태 초기화
        self.balance = self.initial_balance
        self.position = None
        self.trades = []
        self.equity_curve = []
        self.trade_counter = 0

        # 펀딩비 기본값
        if funding_rates is None:
            funding_rates = [0.0] * len(candles)

        # 펀딩비 적용 간격 (캔들 기준)
        funding_interval = self._calc_funding_interval(timeframe)

        # --- 캔들 순회 ---
        for i in range(self.strategy.min_candles, len(candles)):
            current_candle = candles[i]
            history = candles[:i + 1]

            # 1) 펀딩비 적용 (8시간마다)
            if self.position and funding_interval > 0 and i % funding_interval == 0:
                fr = funding_rates[i] if i < len(funding_rates) else 0.0
                self._apply_funding(fr)

            # 2) MarketContext 생성
            context = None
            if context_builder:
                context = context_builder(history, i, funding_rates)
            else:
                fr = funding_rates[i] if i < len(funding_rates) else 0.0
                context = MarketContext(
                    funding_rate=fr,
                    volume_ratio=self._calc_volume_ratio(history, 20),
                )

            # 3) 현재 포지션 상태
            current_pos = self.position.side if self.position else None

            # 4) 전략 신호 생성
            signal = await self.strategy.generate_signal(
                symbol=symbol,
                candles=history,
                current_position=current_pos,
                context=context,
            )

            # 5) 신호 실행
            self._execute_signal(signal, current_candle, i)

            # 6) 자산 곡선 기록
            equity = self._calc_equity(current_candle)
            self.equity_curve.append({
                "timestamp": current_candle.timestamp,
                "equity": round(equity, 2),
                "balance": round(self.balance, 2),
            })

        # --- 미청산 포지션 강제 청산 ---
        if self.position:
            last_candle = candles[-1]
            self._close_position(last_candle, len(candles) - 1, "백테스트 종료 강제 청산")

        # --- 결과 계산 ---
        return self._build_result(symbol, timeframe, candles)

    # --- 신호 실행 ---

    def _execute_signal(self, signal: TradeSignal, candle: Candle, bar_idx: int):
        """매매 신호 처리"""
        if signal.signal == SignalType.HOLD:
            return

        if signal.signal == SignalType.CLOSE:
            if self.position:
                self._close_position(candle, bar_idx, signal.reason)
            return

        if signal.signal in (SignalType.LONG, SignalType.SHORT):
            # 기존 포지션 청산 후 신규 진입
            if self.position:
                self._close_position(candle, bar_idx, "방향 전환")

            self._open_position(signal, candle, bar_idx)

    # --- 포지션 오픈 ---

    def _open_position(self, signal: TradeSignal, candle: Candle, bar_idx: int):
        """포지션 진입"""
        side = "long" if signal.signal == SignalType.LONG else "short"

        # 포지션 크기: 잔고 × 진입 비율 × 레버리지
        size_pct = min(signal.amount_pct, 1.0)
        size_usdt = self.balance * size_pct * self.leverage

        # 최소 $5 체크
        if size_usdt < 5.0:
            return

        # 증거금 체크
        margin_needed = size_usdt / self.leverage
        if margin_needed > self.balance * 0.95:
            size_usdt = self.balance * 0.95 * self.leverage

        # 슬리피지 적용
        entry_price = float(candle.close)
        slipped_price = self._apply_slippage(entry_price, side)
        slippage_cost = abs(slipped_price - entry_price) * (size_usdt / entry_price)

        # 진입 수수료 (시장가 = taker)
        entry_fee = size_usdt * self.fee_taker

        # 수수료 차감
        self.balance -= entry_fee

        self.position = _Position(
            side=side,
            entry_price=slipped_price,
            size_usdt=size_usdt,
            entry_time=candle.timestamp,
            entry_bar=bar_idx,
            entry_fee=entry_fee,
            slippage_cost=slippage_cost,
            signal_strength=signal.strength,
            signal_reason=signal.reason,
        )

    # --- 포지션 청산 ---

    def _close_position(self, candle: Candle, bar_idx: int, reason: str):
        """포지션 청산"""
        pos = self.position
        if not pos:
            return

        exit_price = float(candle.close)
        close_side = "sell" if pos.side == "long" else "buy"
        slipped_exit = self._apply_slippage(exit_price, close_side)

        # PnL 계산
        if pos.side == "long":
            pnl_gross = (slipped_exit - pos.entry_price) / pos.entry_price * pos.size_usdt
        else:
            pnl_gross = (pos.entry_price - slipped_exit) / pos.entry_price * pos.size_usdt

        # 청산 수수료 (taker)
        exit_fee = pos.size_usdt * self.fee_taker
        total_fee = pos.entry_fee + exit_fee

        # 슬리피지 비용 (양쪽)
        exit_slippage = abs(slipped_exit - exit_price) * (pos.size_usdt / exit_price)
        total_slippage = pos.slippage_cost + exit_slippage

        # 순수익 = 총수익 - 수수료 - 펀딩비
        pnl_net = pnl_gross - exit_fee - pos.funding_accumulated

        # 잔고 업데이트
        self.balance += pnl_net  # 진입 수수료는 이미 차감됨

        # 수익률
        margin = pos.size_usdt / self.leverage
        return_pct = (pnl_net / margin * 100) if margin > 0 else 0.0

        # 거래 기록
        self.trade_counter += 1
        trade = BacktestTrade(
            trade_id=self.trade_counter,
            side=pos.side,
            entry_time=pos.entry_time,
            exit_time=candle.timestamp,
            entry_price=pos.entry_price,
            exit_price=slipped_exit,
            size_usdt=pos.size_usdt,
            pnl_gross=pnl_gross,
            pnl_net=pnl_net,
            fee_paid=total_fee,
            funding_paid=pos.funding_accumulated,
            slippage_cost=total_slippage,
            return_pct=return_pct,
            holding_bars=bar_idx - pos.entry_bar,
            signal_strength=pos.signal_strength,
            signal_reason=reason,
        )
        self.trades.append(trade)
        self.position = None

    # --- 슬리피지 ---

    def _apply_slippage(self, price: float, side: str) -> float:
        """
        슬리피지 적용 (0.01~0.05% 랜덤)
        - buy → 가격 올림 (불리)
        - sell → 가격 내림 (불리)
        """
        slip = random.uniform(0.0001, self.slippage_pct / 100)
        if side in ("buy", "long"):
            return price * (1 + slip)
        else:
            return price * (1 - slip)

    # --- 수수료 ---

    def _apply_fee(self, size_usdt: float, order_type: str = "taker") -> float:
        """수수료 계산"""
        rate = self.fee_maker if order_type == "maker" else self.fee_taker
        return size_usdt * rate

    # --- 펀딩비 ---

    def _apply_funding(self, funding_rate: float):
        """
        펀딩비 적용
        - 롱: funding_rate > 0 → 지불, < 0 → 수취
        - 숏: funding_rate > 0 → 수취, < 0 → 지불
        """
        if not self.position or funding_rate == 0:
            return

        cost = self.position.size_usdt * funding_rate

        if self.position.side == "long":
            # 롱은 펀딩비 지불 (양수일 때)
            self.balance -= cost
            self.position.funding_accumulated += cost
        else:
            # 숏은 펀딩비 수취 (양수일 때)
            self.balance += cost
            self.position.funding_accumulated -= cost

    # --- 현재 자산 계산 ---

    def _calc_equity(self, candle: Candle) -> float:
        """미실현 손익 포함 자산 계산"""
        equity = self.balance
        if self.position:
            price = float(candle.close)
            if self.position.side == "long":
                unrealized = (price - self.position.entry_price) / self.position.entry_price * self.position.size_usdt
            else:
                unrealized = (self.position.entry_price - price) / self.position.entry_price * self.position.size_usdt
            equity += unrealized
        return equity

    # --- 거래량 비율 계산 ---

    def _calc_volume_ratio(self, candles: list[Candle], period: int) -> float:
        """현재 거래량 / 평균 거래량"""
        if len(candles) < period + 1:
            return 1.0
        vols = [float(c.volume) for c in candles]
        avg = sum(vols[-period - 1:-1]) / period
        if avg == 0:
            return 1.0
        return vols[-1] / avg

    # --- 펀딩 간격 계산 ---

    def _calc_funding_interval(self, timeframe: str) -> int:
        """타임프레임별 8시간에 해당하는 캔들 수"""
        tf_minutes = {
            "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "2h": 120, "4h": 240, "6h": 360,
            "8h": 480, "12h": 720, "1d": 1440,
        }
        minutes = tf_minutes.get(timeframe, 60)
        funding_minutes = 8 * 60  # 8시간
        interval = funding_minutes // minutes
        return max(interval, 1)

    # --- 결과 생성 ---

    def _build_result(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Candle],
    ) -> BacktestResult:
        """백테스트 결과 집계"""
        result = BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            initial_balance=self.initial_balance,
            final_balance=self.balance,
            trades=self.trades,
            equity_curve=self.equity_curve,
        )

        # 기간
        if candles:
            start_ts = candles[0].timestamp
            end_ts = candles[-1].timestamp
            start_dt = datetime.fromtimestamp(start_ts / 1000, tz=timezone.utc)
            end_dt = datetime.fromtimestamp(end_ts / 1000, tz=timezone.utc)
            result.period = f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}"

        if not self.trades:
            result.warnings.append("거래 없음 — 신호 조건을 완화해 보세요")
            return result

        # --- 수익률 ---
        gross_pnl = sum(t.pnl_gross for t in self.trades)
        total_fees = sum(t.fee_paid for t in self.trades)
        total_funding = sum(t.funding_paid for t in self.trades)
        total_slippage = sum(t.slippage_cost for t in self.trades)
        net_pnl = sum(t.pnl_net for t in self.trades)

        result.total_return = (gross_pnl / self.initial_balance) * 100
        result.total_return_after_fees = (net_pnl / self.initial_balance) * 100
        result.total_fees_paid = total_fees
        result.total_funding_paid = total_funding
        result.total_slippage_cost = total_slippage

        # 수수료/수익 비율
        if gross_pnl > 0:
            result.fee_to_profit_ratio = (total_fees / gross_pnl) * 100
        else:
            result.fee_to_profit_ratio = 100.0

        # --- 승률 / 손익비 ---
        winners = [t for t in self.trades if t.pnl_net > 0]
        losers = [t for t in self.trades if t.pnl_net <= 0]
        result.total_trades = len(self.trades)
        result.winning_trades = len(winners)
        result.losing_trades = len(losers)
        result.win_rate = (len(winners) / len(self.trades)) * 100

        if winners:
            result.avg_win = sum(t.pnl_net for t in winners) / len(winners)
        if losers:
            result.avg_loss = sum(t.pnl_net for t in losers) / len(losers)

        # 수익팩터
        total_wins = sum(t.pnl_net for t in winners) if winners else 0
        total_losses = abs(sum(t.pnl_net for t in losers)) if losers else 0
        result.profit_factor = (total_wins / total_losses) if total_losses > 0 else float("inf")

        # 평균 보유 기간
        result.avg_holding_bars = sum(t.holding_bars for t in self.trades) / len(self.trades)

        # --- MDD ---
        result.max_drawdown, result.max_drawdown_usd = self._calc_mdd()

        # --- 샤프 / 소르티노 ---
        result.sharpe_ratio = self._calc_sharpe()
        result.sortino_ratio = self._calc_sortino()

        # --- 소액 경고 ---
        result.warnings = self._generate_warnings(result, candles)

        return result

    # --- MDD 계산 ---

    def _calc_mdd(self) -> tuple[float, float]:
        """최대 낙폭 (%, $)"""
        if not self.equity_curve:
            return 0.0, 0.0

        peak = self.equity_curve[0]["equity"]
        max_dd_pct = 0.0
        max_dd_usd = 0.0

        for point in self.equity_curve:
            equity = point["equity"]
            if equity > peak:
                peak = equity
            dd_usd = peak - equity
            dd_pct = (dd_usd / peak * 100) if peak > 0 else 0
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
                max_dd_usd = dd_usd

        return max_dd_pct, max_dd_usd

    # --- 샤프 비율 ---

    def _calc_sharpe(self, risk_free_rate: float = 0.0) -> float:
        """일별 수익률 기반 샤프 비율 (연환산)"""
        if len(self.equity_curve) < 2:
            return 0.0

        returns = []
        for i in range(1, len(self.equity_curve)):
            prev = self.equity_curve[i - 1]["equity"]
            curr = self.equity_curve[i]["equity"]
            if prev > 0:
                returns.append((curr - prev) / prev)

        if not returns:
            return 0.0

        avg_ret = sum(returns) / len(returns)
        std_ret = (sum((r - avg_ret) ** 2 for r in returns) / len(returns)) ** 0.5

        if std_ret == 0:
            return 0.0

        # 연환산 (캔들 기반이므로 대략적)
        sharpe = (avg_ret - risk_free_rate) / std_ret * math.sqrt(len(returns))
        return sharpe

    # --- 소르티노 비율 ---

    def _calc_sortino(self, risk_free_rate: float = 0.0) -> float:
        """하방 변동성만 사용하는 소르티노 비율"""
        if len(self.equity_curve) < 2:
            return 0.0

        returns = []
        for i in range(1, len(self.equity_curve)):
            prev = self.equity_curve[i - 1]["equity"]
            curr = self.equity_curve[i]["equity"]
            if prev > 0:
                returns.append((curr - prev) / prev)

        if not returns:
            return 0.0

        avg_ret = sum(returns) / len(returns)
        downside = [r for r in returns if r < 0]

        if not downside:
            return float("inf") if avg_ret > 0 else 0.0

        down_std = (sum(r ** 2 for r in downside) / len(downside)) ** 0.5

        if down_std == 0:
            return 0.0

        sortino = (avg_ret - risk_free_rate) / down_std * math.sqrt(len(returns))
        return sortino

    # --- 소액 경고 생성 ---

    def _generate_warnings(
        self, result: BacktestResult, candles: list[Candle]
    ) -> list[str]:
        """소액 트레이딩 경고"""
        warnings = []

        # 수수료 비중 경고
        if result.fee_to_profit_ratio > 50:
            warnings.append(
                f"수수료가 수익의 {result.fee_to_profit_ratio:.0f}% — 거래 빈도를 줄이세요"
            )

        # 과다 거래 경고
        if candles:
            # 대략적 거래일 수 계산
            duration_ms = candles[-1].timestamp - candles[0].timestamp
            days = max(duration_ms / (1000 * 86400), 1)
            trades_per_day = result.total_trades / days
            if trades_per_day > 3:
                warnings.append(
                    f"일 평균 {trades_per_day:.1f}회 거래 — 소액에서 수수료 부담 과중"
                )

        # MDD 경고
        if result.max_drawdown > 30:
            warnings.append(
                f"MDD {result.max_drawdown:.1f}% — 소액에서 복구 어려움"
            )

        # 샤프 비율 경고
        if result.sharpe_ratio < 0.5 and result.total_trades >= 5:
            warnings.append(
                f"샤프 비율 {result.sharpe_ratio:.2f} — 리스크 대비 수익 부족"
            )

        # 순수익률 마이너스
        if result.total_return_after_fees < 0:
            warnings.append(
                f"순수익률 {result.total_return_after_fees:.1f}% — 수수료 차감 시 손실"
            )

        return warnings
