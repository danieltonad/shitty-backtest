import yfinance as yf
import pandas as pd
import numpy as np

def atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def get_levels(entry_price, atr_val, atr_mult=2.0, rr=4.0, notional=1000.0):
    """Return take-profit and stop-loss PnL targets (in $ terms)."""
    sl_dist = atr_mult * atr_val
    tp_dist = sl_dist * rr
    sl_pnl = max(notional * (sl_dist / entry_price), 20)  # min $20 SL
    tp_pnl = notional * (tp_dist / entry_price)
    return tp_pnl, sl_pnl

def signal_atr_breakout(df, i, atr_period=20, atr_mult=1.0):
    """Return BUY/SELL signal based on ATR breakout."""
    if i < atr_period + 1:
        return None
    prev = df.iloc[i - 1]
    last = df.iloc[i]
    vol = df['ATR'].iloc[i]
    if last['Close'] > prev['High'] + atr_mult * vol:
        return "BUY"
    elif last['Close'] < prev['Low'] - atr_mult * vol:
        return "SELL"
    return None

def backtest_atr_breakout(
    ticker,
    interval="1d",
    period="6mo",
    notional=1000.0,
    leverage=20,
    atr_period=20,
    atr_mult=1.0,
    rr=4.0,
    trade_max_duration=5,
):
    df = yf.Ticker(ticker).history(interval=interval, period=period)
    df.reset_index(inplace=True)
    df['ATR'] = atr(df, atr_period)

    trades = []
    for i in range(len(df)):
        side = signal_atr_breakout(df, i, atr_period, atr_mult)
        if side is None:
            continue

        entry_row = df.iloc[i]
        entry_price = entry_row['Close']
        atr_val = entry_row['ATR']
        tp_pnl_d, sl_pnl_d = get_levels(entry_price, atr_val, atr_mult, rr, notional)

        size = notional / entry_price
        max_exit_index = min(i + trade_max_duration, len(df) - 1)
        exit_index, exit_price, exit_type = None, None, "EOW_CLOSE"

        for j in range(i + 1, max_exit_index + 1):
            high, low = df.iloc[j][['High', 'Low']]

            if side == "BUY":
                tp_price = entry_price + (tp_pnl_d / notional) * entry_price
                sl_price = entry_price - (sl_pnl_d / notional) * entry_price
                if high >= tp_price:
                    exit_index = j
                    exit_price = tp_price
                    exit_type = "TP"
                    break
                elif low <= sl_price:
                    exit_index = j
                    exit_price = sl_price
                    exit_type = "SL"
                    break

            elif side == "SELL":
                tp_price = entry_price - (tp_pnl_d / notional) * entry_price
                sl_price = entry_price + (sl_pnl_d / notional) * entry_price
                if low <= tp_price:
                    exit_index = j
                    exit_price = tp_price
                    exit_type = "TP"
                    break
                elif high >= sl_price:
                    exit_index = j
                    exit_price = sl_price
                    exit_type = "SL"
                    break

        if exit_index is None:
            exit_index = max_exit_index
            exit_price = df.iloc[exit_index]['Close']
            exit_type = "EOW_CLOSE"

        spread_cost = abs(exit_price - entry_price) * (size / leverage)
        pnl = (exit_price - entry_price) * size * (1 if side == "BUY" else -1)
        pnl_adj = pnl - spread_cost

        trades.append({
            "epic": ticker,
            "size": size,
            "pnl": pnl_adj,
            "direction": side,
            "exit_type": exit_type,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "opened_at": entry_row["Date"],
            "closed_at": df.iloc[exit_index]["Date"],
            "hook_name": "ATR BRK OUT",
            "spread_cost": spread_cost
        })

    trades_df = pd.DataFrame(trades)
    trades_df.to_csv(f"./data/{ticker}_atr_breakout_trades.csv", index=False)
    print(f"Backtest complete: {len(trades_df)} trades logged → {ticker}_atr_breakout_trades.csv")
    return trades_df



if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "META", "NVDA", "TSLA", "GOOGL", "GOOG", "ORCL" ,"BTC-USD", "ETH-USD"]
    for ticker in tickers:
        backtest_atr_breakout(ticker, interval="1d", period="3mo")
