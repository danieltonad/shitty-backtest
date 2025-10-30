import pandas as pd
import numpy as np

# === Sharpe Calculation ===
def calc_sharpe(returns):
    """Compute Sharpe ratio assuming zero risk-free rate."""
    if returns.std() == 0:
        return np.nan
    return returns.mean() / returns.std() * np.sqrt(len(returns))

def analyze_backtest(csv_path):
    df = pd.read_csv(csv_path)

    # Clean column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Ensure numeric types
    for col in ["pnl", "entry_price", "exit_price", "size", "spread_cost"]:
        df[col] = df[col].astype(float)

    # Compute margin used
    # For backtest we assume BTCUSD etc have leverage = 20 by default
    leverage = 20
    df["margin_used"] = (df["entry_price"] * df["size"]) / leverage

    # Return on equity
    df["return_on_equity"] = df["pnl"] / df["margin_used"]

    # === Sharpe ratios ===
    overall_sharpe = calc_sharpe(df["return_on_equity"])
    sharpe_by_strategy = df.groupby("hook_name")["return_on_equity"].apply(calc_sharpe)
    sharpe_by_direction = df.groupby("direction")["return_on_equity"].apply(calc_sharpe)
    sharpe_by_exit = df.groupby("exit_type")["return_on_equity"].apply(calc_sharpe)

    # === Print Results ===
    print("\n=== Sharpe Ratios ===")
    print(f"Overall: {overall_sharpe:.3f}")

    print("\nBy Strategy:")
    print(sharpe_by_strategy)

    print("\nBy Direction:")
    print(sharpe_by_direction)

    print("\nBy Exit Type:")
    print(sharpe_by_exit)

    # print("\n=== Trade Summary ===")
    # print(df[["epic", "direction", "exit_type", "pnl", "return_on_equity", "spread_cost"]])

    return df, overall_sharpe, sharpe_by_strategy, sharpe_by_direction, sharpe_by_exit


if __name__ == "__main__":
    # Example: run on your BTC trades CSV
    csv_path = "./data/AAPL_atr_breakout_trades.csv"
    analyze_backtest(csv_path)
