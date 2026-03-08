"""
기술적 지표 계산 모듈
- RSI, MACD, 볼린저밴드, EMA, ATR 등 공통 지표
- 순수 Python 계산 (numpy 의존 최소화)
- 사용처: 내장 전략에서 import하여 사용
"""

from decimal import Decimal
from app.services.exchange.base import Candle


def highs(candles: list[Candle]) -> list[float]:
    """캔들에서 고가 리스트 추출"""
    return [float(c.high) for c in candles]


def lows(candles: list[Candle]) -> list[float]:
    """캔들에서 저가 리스트 추출"""
    return [float(c.low) for c in candles]


def volumes(candles: list[Candle]) -> list[float]:
    """캔들에서 거래량 리스트 추출"""
    return [float(c.volume) for c in candles]


def closes(candles: list[Candle]) -> list[float]:
    """캔들에서 종가 리스트 추출"""
    return [float(c.close) for c in candles]


# --- 이동평균 ---

def sma(values: list[float], period: int) -> list[float]:
    """단순 이동평균 (Simple Moving Average)"""
    result = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(0.0)
        else:
            result.append(sum(values[i - period + 1: i + 1]) / period)
    return result


def ema(values: list[float], period: int) -> list[float]:
    """지수 이동평균 (Exponential Moving Average)"""
    if not values:
        return []
    multiplier = 2 / (period + 1)
    result = [values[0]]
    for i in range(1, len(values)):
        val = (values[i] - result[-1]) * multiplier + result[-1]
        result.append(val)
    return result


# --- RSI ---

def rsi(values: list[float], period: int = 14) -> list[float]:
    """RSI (Relative Strength Index)"""
    if len(values) < period + 1:
        return [50.0] * len(values)

    result = [50.0] * period
    gains = []
    losses = []

    # 초기 평균 계산
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100 - (100 / (1 + rs)))

    # 이후 Wilder's smoothing
    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))

    return result


# --- MACD ---

def macd(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    """MACD (macd_line, signal_line, histogram)"""
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)

    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal_period)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]

    return macd_line, signal_line, histogram


# --- 볼린저 밴드 ---

def bollinger_bands(
    values: list[float], period: int = 20, std_dev: float = 2.0
) -> tuple[list[float], list[float], list[float]]:
    """볼린저 밴드 (upper, middle, lower)"""
    middle = sma(values, period)
    upper = []
    lower = []

    for i in range(len(values)):
        if i < period - 1:
            upper.append(0.0)
            lower.append(0.0)
        else:
            window = values[i - period + 1: i + 1]
            mean = middle[i]
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance ** 0.5
            upper.append(mean + std_dev * std)
            lower.append(mean - std_dev * std)

    return upper, middle, lower


# --- ATR (Average True Range) ---

def atr(candles: list[Candle], period: int = 14) -> list[float]:
    """ATR — 변동성 측정 (손절/익절 계산용)"""
    if len(candles) < 2:
        return [0.0] * len(candles)

    # True Range 계산
    tr_list = [float(candles[0].high - candles[0].low)]
    for i in range(1, len(candles)):
        h = float(candles[i].high)
        l = float(candles[i].low)
        prev_c = float(candles[i - 1].close)
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        tr_list.append(tr)

    # ATR = TR의 EMA (Wilder's smoothing)
    if len(tr_list) < period:
        return tr_list

    result = [0.0] * (period - 1)
    avg = sum(tr_list[:period]) / period
    result.append(avg)

    for i in range(period, len(tr_list)):
        avg = (avg * (period - 1) + tr_list[i]) / period
        result.append(avg)

    return result


# --- 거래량 비율 ---

def volume_ratio(candles: list[Candle], period: int = 20) -> float:
    """현재 거래량 / 평균 거래량 비율"""
    if len(candles) < period + 1:
        return 1.0
    vols = volumes(candles)
    avg_vol = sum(vols[-period - 1:-1]) / period
    if avg_vol == 0:
        return 1.0
    return vols[-1] / avg_vol
