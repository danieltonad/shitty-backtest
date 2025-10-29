from capital_com.api import save_ohlc_data
import asyncio


async def main():
    await save_ohlc_data("GOLD", resolution="MINUTE", n=1_000)



asyncio.run(main())