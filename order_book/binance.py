import asyncio
import websockets
import json

async def stream_binance_orderbook():
    uri = "wss://stream.binance.com:9443/ws/btcusdt@depth"
    async with websockets.connect(uri) as ws:
        while True:
            data = json.loads(await ws.recv())
            print("Top bid:", data['b'][0], "Top ask:", data['a'][0])

asyncio.run(stream_binance_orderbook())
