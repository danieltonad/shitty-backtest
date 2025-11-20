from typing import Optional
from enum import Enum
from .memory import memory

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


def compute_ema(prices, period: int) -> float:
    """
    Simple EMA implementation for bar closes.
    Assumes prices is a list of floats (oldest → newest).
    """
    if len(prices) < period:
        return None

    k = 2 / (period + 1)
    ema = prices[0]

    for p in prices[1:]:
        ema = p * k + ema * (1 - k)

    return ema


def get_ema_signal_from_bars(
    epic: str,
    fast_period: int = 9,
    slow_period: int = 21,
    trend_period: int = 50
) -> Optional[SignalType]:
    """
    Uses memory.bars[epic] to compute EMAs and return a strict EMA crossover signal.
    Returns: SignalType or None
    """

    bars = memory.bars[epic]
    if len(bars) < trend_period + 2:
        return None

    # Extract close prices
    closes = [b["close"] for b in bars]

    fast = compute_ema(closes, fast_period)
    slow = compute_ema(closes, slow_period)
    trend = compute_ema(closes, trend_period)

    if fast is None or slow is None or trend is None:
        return None

    # Trend context
    uptrend = slow > trend
    downtrend = slow < trend

    # Crossovers based on the *latest fully closed bar*
    bullish_cross = fast > slow
    bearish_cross = fast < slow

    # Strict signals
    if bullish_cross and uptrend:
        return SignalType.BUY

    if bearish_cross and downtrend:
        return SignalType.SELL

    return None














def order_block_signal(
    epic: str,
    trend_period: int = 50,
    structure_lookback: int = 10
) -> Optional[SignalType]:

    bars = memory.bars[epic]
    if len(bars) < trend_period + structure_lookback + 3:
        return None

    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows  = [b["low"] for b in bars]

    slow_trend = compute_ema(closes, trend_period)
    current = bars[-1]
    prev = bars[-2]
    prev2 = bars[-3]

    # ---- Trend filter ----
    uptrend = closes[-1] > slow_trend
    downtrend = closes[-1] < slow_trend

    # ---- 1. Displacement detection ----
    # We identify a structural break:
    recent_high = max(highs[-structure_lookback-3:-3])
    recent_low = min(lows[-structure_lookback-3:-3])

    broke_up = prev2["close"] > recent_high
    broke_down = prev2["close"] < recent_low

    # ---- 2. Order block candle ----
    # The "last opposite candle" before displacement.
    # We use prev3 (bars[-4]) as the candidate.
    if len(bars) < 4:
        return None

    block_candle = bars[-4]

    # Long OB: last bearish candle before upward displacement
    valid_long_block = (
        block_candle["close"] < block_candle["open"]  # bearish candle
        and broke_up
    )

    # Short OB: last bullish candle before downward displacement
    valid_short_block = (
        block_candle["close"] > block_candle["open"]  # bullish candle
        and broke_down
    )

    # Define block boundaries
    block_high = block_candle["high"]
    block_low = block_candle["low"]

    # ---- 3. Mitigation test ----
    tapped_long = prev["low"] <= block_high and prev["low"] >= block_low
    tapped_short = prev["high"] >= block_low and prev["high"] <= block_high

    # ---- 4. Continuation (confirmation bar) ----
    long_continue = current["close"] > prev["high"]
    short_continue = current["close"] < prev["low"]

    # ---- 5. Combine logic with trend filter ----
    if valid_long_block and tapped_long and long_continue and uptrend:
        return SignalType.BUY

    if valid_short_block and tapped_short and short_continue and downtrend:
        return SignalType.SELL

    return None

