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




async def new_order(epic: str, direction: SignalType, entry: float, tp: float, sl: float):
    from .memory import memory
    try:
        ask, bid = memory.get_last_price(epic)
        current_price = ask if direction == SignalType.BUY else bid
        in_trade: bool = False  # Placeholder for trade check logic

        if current_price <= entry and direction == SignalType.BUY or \
           current_price >= entry and direction == SignalType.SELL:
            start = int(time.time())
            in_trade = True
            print(f"Entered {direction.value} trade on {epic} at {entry} TP: {tp} SL: {sl}")
            while in_trade:
                ask, bid = memory.get_last_price(epic)
                current_price = ask if direction == SignalType.BUY else bid
                duration = int(time.time()) - start
            
                if direction == SignalType.BUY:
                    if current_price >= tp:
                        pnl = tp - entry
                        await log_trade(epic, direction, pnl, "TP", duration)
                        in_trade = False
                    elif current_price <= sl:
                        pnl = sl - entry
                        await log_trade(epic, direction, pnl, "SL", duration)
                        in_trade = False

                elif direction == SignalType.SELL:
                    if current_price <= tp:
                        pnl = entry - tp  # reversed for sell
                        await log_trade(epic, direction, pnl, "TP", duration)
                        in_trade = False
                    elif current_price >= sl:
                        pnl = entry - sl  # reversed for sell
                        await log_trade(epic, direction, pnl, "SL", duration)
                        in_trade = False


                await asyncio.sleep(4)
        
        else:
            await asyncio.sleep(5)
            await new_order(epic, direction, entry, tp, sl)  # Retry until entry price is met

    except Exception as e:
        print(f"Error in new_order for {epic}: {e}")