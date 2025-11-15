from enum import Enum
import asyncio, os, time
from datetime import datetime

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"

async def log_trade(epic: str, direction: SignalType, pnl: float, exit: str, duration: int):
    import aiofiles
    file = f"{epic}.csv"
    print(f"Closing trade on {epic}: {direction.value} with PnL: {pnl} on {exit}")
    if file not in os.listdir():
        async with aiofiles.open(file, mode="w") as f:
            header = "date,epic,direction,pnl,exit,duration\n"
            await f.write(header)

    async with aiofiles.open(file, mode="a") as f:
        log_entry = f"{datetime.utcnow().isoformat()},{epic},{direction.value},{pnl},{exit},{duration}s\n"
        await f.write(log_entry)




async def new_order(
    epic: str,
    direction: SignalType,
    entry: float,
    tp: float,
    sl: float,
    trail_offset_factor: float = 0.7,   # % of TP distance to trail at (e.g., 0.7 = 70% of TP dist)
):
    from .memory import memory
    try:
        # Wait for entry price to be touched
        while True:
            ask, bid = memory.get_last_price(epic)
            current_price = ask if direction == SignalType.BUY else bid
            if (direction == SignalType.BUY and current_price >= entry) or \
               (direction == SignalType.SELL and current_price <= entry):
                break
            await asyncio.sleep(0.2)

        # Entry confirmed
        start = int(time.time())
        print(f"Entered {direction.value} on {epic} @ {entry:.3f} | TP: {tp:.3f} | SL: {sl:.3f}")

        # Compute trail offset (static % of TP distance — no activation delay)
        tp_distance = abs(tp - entry)
        trail_offset = tp_distance * trail_offset_factor  # e.g., 0.7 × TP range

        trail_sl = sl  # dynamic trailing SL
        is_trailing = True 

        while True:
            await asyncio.sleep(0.5)
            ask, bid = memory.get_last_price(epic)
            current_price = ask if direction == SignalType.BUY else bid
            duration = int(time.time()) - start

            # Update trailing SL continuously
            if direction == SignalType.BUY:
                new_sl = current_price - trail_offset
                if new_sl > trail_sl:
                    trail_sl = new_sl
            else:  # SELL
                new_sl = current_price + trail_offset
                if new_sl < trail_sl:
                    trail_sl = new_sl

            # Exit check
            exit_reason = None
            pnl = 0.0

            if direction == SignalType.BUY:
                if current_price >= tp:
                    exit_reason = "TP"
                    pnl = tp - entry
                elif current_price <= trail_sl:
                    exit_reason = "TrailSL" if trail_sl != sl else "SL"
                    pnl = trail_sl - entry
            else:  # SELL
                if current_price <= tp:
                    exit_reason = "TP"
                    pnl = entry - tp
                elif current_price >= trail_sl:
                    exit_reason = "TrailSL" if trail_sl != sl else "SL"
                    pnl = entry - trail_sl

            if exit_reason:
                await log_trade(epic, direction, pnl, exit_reason, duration)
                print(f"Exited {direction.value} on {epic} @ {current_price:.3f} | {exit_reason} | PnL: {pnl:.3f} | Dur: {duration}s")
                return

    except Exception as e:
        print(f"Error in new_order for {epic}: {e}")