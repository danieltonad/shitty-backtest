from capital_com.api import save_ohlc_data

from capital_com.socket import capital_socket, memory
import asyncio


async def main():
    # await save_ohlc_data("GOLD", resolution="MINUTE", n=1_000)

    await memory.update_auth_header()
    await capital_socket.connect_websocket()
    await capital_socket.subscribe_to_epic("GOLD")
    await capital_socket.subscribe_to_epic("US100")
    await capital_socket.subscribe_to_epic("EURUSD")
    await capital_socket.subscribe_to_epic("BTCUSD")
    # await capital_socket.subscribe_to_epic("GBPUSD")

    while True:
        await asyncio.sleep(5 * 60)
        await memory.update_auth_header()
        await capital_socket.ping_socket()


asyncio.run(main())