from httpx import AsyncClient
from datetime import datetime, time
from typing import Tuple


def get_scalp_rr(epic: str, risk_usd: float = 25.0) -> Tuple[int, int, int]:
    from .memory import memory
    # Minimal viable bars
    bars = list(memory.bars[epic])[-15:]
    if len(bars) < 5:
        return 50, 25, 15  # conservative fallback

    # Price & spread
    try:
        ask, bid = memory.get_last_price(epic)
        entry = (ask + bid) / 2.0
        spread = ask - bid
    except:
        entry = bars[-1]["close"]
        spread = 0.5

    # ATR (5-bar for speed)
    trs = []
    for i in range(1, len(bars)):
        h, l, c_prev = bars[i]["high"], bars[i]["low"], bars[i-1]["close"]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    atr_val = max(3.0, sum(trs) / len(trs)) if trs else 4.0

    # Spread stress: if spread > 0.6, widen SL
    spread_mult = 1.0 + max(0.0, (spread - 0.5) / 0.5)  # 0.5→1.0: +0% to +100%
    spread_mult = min(2.0, spread_mult)

    # SL = 0.4 × ATR, widened by spread
    sl_dist = 0.4 * atr_val * spread_mult
    tp_dist = 0.9 * atr_val * spread_mult  # ~2.25:1 RR

    # Size position to risk $risk_usd
    oz = risk_usd / sl_dist
    oz = max(0.05, min(1.0, round(oz, 2)))  # realistic min/max

    tp_pnl = oz * tp_dist
    sl_pnl = oz * sl_dist
    trail_pnl = oz * (sl_dist * 0.6)

    return (
        int(round(tp_pnl)),
        int(round(sl_pnl)),
        int(round(trail_pnl))
    )


def is_trading_session() -> bool:
    now = datetime.utcnow()
    t = now.time()
    # Exclude high-impact news minutes (simpler: use a quiet window)
    # Ideal: 12:30–15:00 UTC (avoid open rush & 16:30 close rush)
    if not (time(12, 30) <= t <= time(15, 0)):
        return False
    # Avoid first/last 15 min of session
    return True


async def strategies(epic: str):
    # rr
    leverage =  100
    amount = 50
    trend_period = 200

    profit, loss, trail = 100, 25, 20 #get_scalp_rr(epic=epic, risk_usd=amount)
    # print(f"Scalp RR for {epic}: TP=${profit}, SL=${loss}, Trail=${trail}")
    
    if not is_trading_session():
        return
    
    from .hook import send_hook
    from .momentum import momentum_punch_signal
    from .signals import get_ema_signal_from_bars, order_block_signal


    async with AsyncClient() as session:
        # momentum punch
        momentum_signal = momentum_punch_signal(epic)
        if momentum_signal:
            await send_hook(ticker=epic, hook_name="momentum", direction=momentum_signal, amount=amount, profit=profit, loss=loss, trail_sl=loss, session=session, strategy=True)


        # 10/20/300 EMA
        # ema_signal = get_ema_signal_from_bars(epic=epic, fast_period=10, slow_period=20, trend_period=trend_period)
        # if ema_signal:
        #     await send_hook(ticker=epic, hook_name=f"10/20/{trend_period}", direction=ema_signal, amount=amount, profit=profit, loss=loss, trail_sl=loss, session=session, strategy=True)


        # order block
        ob_signal  = order_block_signal(epic=epic, trend_period=trend_period, structure_lookback=25)
        if ob_signal:
            await send_hook(ticker=epic, hook_name="order block", direction=ob_signal, amount=amount, profit=profit, loss=loss, trail_sl=loss, session=session, strategy=True)