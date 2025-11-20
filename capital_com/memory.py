from .api import get_auth_header
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

class Memory:
    def __init__(self, bar_seconds=11):
        self.capital_auth_header: dict = {}
        self.tick_history: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=1000))
        self.bars: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=500))  # store 100 bars
        self.bar_seconds = bar_seconds
        self.current_bar: Dict[str, dict] = {}
        self.last_price: Dict[str, Tuple[float, float]] = {}

    async def update_auth_header(self):
        self.capital_auth_header = await get_auth_header()

    def get_last_price(self, epic: str) -> Tuple[float, float]:
        return self.last_price[epic]

    async def append_tick_data(self, epic: str, ask: float, bid: float, timestamp: int):
        # Store last price
        self.last_price[epic] = (ask, bid)

        # Normalize timestamp to seconds if in ms
        if timestamp > 1e12:  # likely milliseconds
            ts_sec = timestamp / 1000.0
        else:
            ts_sec = float(timestamp)

        mid = (ask + bid) / 2.0
        spread = ask - bid

        # Initialize current bar if needed
        if epic not in self.current_bar:
            self.current_bar[epic] = {
                "open": mid,
                "high": ask,
                "low": bid,
                "close": mid,
                "start_time": ts_sec,
                "spread_sum": spread,
                "tick_count": 1
            }
        else:
            cb = self.current_bar[epic]
            cb["high"] = max(cb["high"], ask)
            cb["low"] = min(cb["low"], bid)
            cb["close"] = mid
            cb["spread_sum"] += spread
            cb["tick_count"] += 1

            # Close bar if duration exceeded
            if ts_sec - cb["start_time"] >= self.bar_seconds:
                bar = {
                    "open": cb["open"],
                    "high": cb["high"],
                    "low": cb["low"],
                    "close": cb["close"],
                    "start_time": cb["start_time"],
                    "end_time": ts_sec,
                    "avg_spread": cb["spread_sum"] / cb["tick_count"]
                }
                self.bars[epic].append(bar)
                
                # Check for trading signals
                from .event import strategies
                await strategies(epic)

                # Start new bar
                self.current_bar[epic] = {
                    "open": mid,
                    "high": ask,
                    "low": bid,
                    "close": mid,
                    "start_time": ts_sec,
                    "spread_sum": spread,
                    "tick_count": 1
                }

        self.tick_history[epic].append({"ask": ask, "bid": bid, "timestamp": timestamp})






memory = Memory()