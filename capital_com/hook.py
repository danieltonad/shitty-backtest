from httpx import AsyncClient
from .simulator import SignalType


async def send_hook(ticker: str,  hook_name: str, direction: SignalType, amount: int, profit: int, loss: int, trail_sl: int, session: AsyncClient, mkt_closed: bool = True, recalibrate: bool = True, strategy: bool = False):
    hook_name = hook_name.upper()        
    url = "http://127.0.0.1:3556/webhook/trading-view"
    payload = {
        "epic": ticker,
        "direction": direction.value,
        "amount": amount,
        "hook_name": hook_name,
        "profit": profit,
        "loss": loss,
        "trail_sl": trail_sl,
        "exit_criteria": [
            "TP", "SL"
        ]
    }
    if mkt_closed:
        payload["exit_criteria"].append("EOW_CLOSE")
    if recalibrate:
        payload["exit_criteria"].append("RECALIBRATE")
    if strategy:
        payload["exit_criteria"].append("STRATEGY")
    res = await session.post(url, json=payload)
    print(f"{hook_name} Hook | {ticker}: {res.status_code} -> {direction.value} | TP: ${profit} | SL: ${loss} | Trail: ${trail_sl}")

