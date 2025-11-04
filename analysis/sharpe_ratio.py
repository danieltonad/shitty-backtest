import pandas as pd
import numpy as np
from enum import Enum


# === CONFIG ===
class EpicInstrument(Enum):
    CRYPTO = "crypto"
    STOCKS = "stocks"        # indices, ETFs
    INDICES = "indices"  # treated as stocks
    COMMODITIES = "commodities"
    CURRENCIES = "currencies"  # forex

LEVERAGE = {
    EpicInstrument.CRYPTO: 20,
    EpicInstrument.CURRENCIES: 100,
    EpicInstrument.STOCKS: 20,
    EpicInstrument.COMMODITIES: 100,
    EpicInstrument.INDICES: 100
}


def get_leverage(epic: str) -> EpicInstrument:
    epic = epic.upper()

    # Group definitions
    forex_pairs = {
        "EURUSD", "USDJPY", "GBPUSD", "USDCAD", "AUDUSD",
        "USDCHF", "USDCNY", "USDMXN", "GBPAUD", "CADJPY",
        "USDZAR", "USDTRY", "AUDJPY", "NZDJPY"
    }
    cryptos = {"BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "AVAXUSD", "DOGEUSD", "SHIBUSD", "ADAUSD", "XRPUSD", "LTCUSD", "LINKUSD", "NEARUSD", "TONUSD", "TAOUSD", "BCHUSD", "PEPEUSD", "AAVEUSD", "TRXUSD"}
    indices = {"QQQ", "SPY", "IWM", "VOO", "US100", "US500", "US30", "VIX", "DXY"}
    commodities = {"GOLD", "SILVER", "OIL_CRUDE", "OIL_BRENT", "NATGAS"}

    if epic in forex_pairs:
        return EpicInstrument.CURRENCIES
    if epic in cryptos:
        return EpicInstrument.CRYPTO
    if epic in indices:
        return EpicInstrument.INDICES
    if epic in commodities:
        return EpicInstrument.COMMODITIES
    return EpicInstrument.STOCKS

def calc_spread(row):
    """Compute spread cost for each trade."""
    leverage = LEVERAGE[get_leverage(row["epic"])]
    # print(row["exit_price"], row["entry_price"], row["size"], leverage, row["epic"])
    return abs(float(str(row["exit_price"]).replace(",","")) - float(str(row["entry_price"]).replace(",",""))) * (float(row["size"]) / leverage)

def calc_sharpe(returns):
    """Sharpe ratio assuming zero risk-free rate."""
    if returns.std() == 0:
        return np.nan
    return returns.mean() / returns.std() * np.sqrt(len(returns))

# === MAIN ===
def analyze_trades(csv_path: str | list):
    if isinstance(csv_path, list):
        df_list = [pd.read_csv(p) for p in csv_path]
        df = pd.concat(df_list, ignore_index=True)
    else:
        df = pd.read_csv(csv_path)

    # Clean column names
    df.columns = [c.strip().lower() for c in df.columns]

    # --- CLEAN NUMERIC FIELDS ---
    numeric_cols = ["entry_price", "exit_price", "size", "pnl", "pnl_percentage"]
    for col in numeric_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.strip()
        )

    # Convert to floats
    df["entry_price"] = df["entry_price"].astype(float)
    df["exit_price"] = df["exit_price"].astype(float)
    df["size"] = df["size"].astype(float)
    df["pnl"] = df["pnl"].astype(float)
    df["pnl_percentage"] = df["pnl_percentage"].astype(float)

    # --- CALCULATIONS ---
    df["spread_cost"] = df.apply(calc_spread, axis=1)
    df["adj_pnl"] = df["pnl"] - df["spread_cost"]

    # Compute return on margin
    df["margin_used"] = (
        (df["entry_price"] * df["size"])
        / df["epic"].apply(lambda e: LEVERAGE[get_leverage(e)])
    )
    df["return_on_equity"] = df["adj_pnl"] / df["margin_used"]

    # --- SHARPE CALCULATIONS ---
    overall_sharpe = calc_sharpe(df["return_on_equity"])
    sharpe_by_strategy = df.groupby("hook_name")["return_on_equity"].apply(calc_sharpe)
    sharpe_by_side = df.groupby("direction")["return_on_equity"].apply(calc_sharpe)

    print("\n=== Sharpe Ratios ===")
    print(f"Overall: {overall_sharpe:.3f}")
    print("\nBy Strategy:")
    print(sharpe_by_strategy)
    print("\nBy Direction:")
    print(sharpe_by_side)

    # print("\n=== Summary ===")
    # print(df[["epic", "hook_name", "direction", "adj_pnl", "return_on_equity"]])

    return df, overall_sharpe, sharpe_by_strategy, sharpe_by_side



if __name__ == "__main__":
    trades = [ r"C:\Users\msiso\Downloads\27-31-oct-trades.csv"]
    df, overall, by_strategy, by_side = analyze_trades(trades)

# epic, size, pnl, direction, entry_price, exit_price, opened_at, closed_at, hook_name, spread_cost

