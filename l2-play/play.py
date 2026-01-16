import pandas as pd

df = pd.read_csv('BTCUSD-trades-2026-01-13.csv')

# Convert timestamp from microseconds to datetime
df['datetime'] = pd.to_datetime(df['timestamp'], unit='us')

# Classify trade direction
df['side'] = df['is_buyer_maker'].map({True: 'sell', False: 'buy'})

# Compute trade value in quote currency (already have quote_quantity)
df['value_usdt'] = df['quote_quantity']

# Add tick direction (for price impact)
df['price_change'] = df['price'].diff()








# Group by side and look at average price change AFTER trade
df['next_price'] = df['price'].shift(-1)
df['delta'] = df['next_price'] - df['price']

buy_impact = df[df['side'] == 'buy']['delta'].mean()
sell_impact = df[df['side'] == 'sell']['delta'].mean()

print(f"Average price move after BUY:  {buy_impact:+.6f}")
print(f"Average price move after SELL: {sell_impact:+.6f}")




# Define "large" as top 10% by quantity
threshold = df['quantity'].quantile(0.90)
df['is_large'] = df['quantity'] >= threshold

# See if large buys lead to sustained upward moves
large_buys = df[(df['side'] == 'buy') & (df['is_large'])]
print(f"Large buy avg next delta: {large_buys['delta'].mean():+.6f}")






