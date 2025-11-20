from httpx import AsyncClient
from datetime import datetime, time


def is_trading_session() -> bool:
    """Only trade during high-liquidity windows (UTC)."""
    now = datetime.utcnow().time()
    # Primary: London–NY overlap
    return time(12, 0) <= now <= time(16, 30)


async def strategies(epic: str):
    # if not is_trading_session():
    #     return
    
    from .hook import send_hook
    from .momentum import momentum_punch_signal
    from .signals import get_ema_signal_from_bars, order_block_signal

    # rr
    leverage =  100
    margin = 50
    profit = margin * 5
    loss = margin
    trend_period = 150

    async with AsyncClient() as session:
        # momentum punch
        momentum_signal = momentum_punch_signal(epic)
        if momentum_signal:
            await send_hook(ticker=epic, hook_name="momentum", direction=momentum_signal, amount=margin, profit=profit, loss=loss, trail_sl=loss, session=session, strategy=True)


        # 10/20/300 EMA
        ema_signal = get_ema_signal_from_bars(epic=epic, fast_period=5, slow_period=10, trend_period=trend_period)
        if ema_signal:
            await send_hook(ticker=epic, hook_name="5/10/150", direction=ema_signal, amount=margin, profit=profit, loss=loss, trail_sl=loss, session=session, strategy=True)


        # order block
        ob_signal  = order_block_signal(epic=epic, trend_period=trend_period, structure_lookback=25)
        if ob_signal:
            await send_hook(ticker=epic, hook_name="order block", direction=ob_signal, amount=margin, profit=profit, loss=loss, trail_sl=loss, session=session, strategy=True)