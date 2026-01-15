import pandas as pd

# Load your data with header
df = pd.read_csv('AUDUSD_quotes.csv')

# Convert timestamp (milliseconds) to datetime
df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

# Compute derived fields
df['mid_price'] = (df['bid'] + df['ask']) / 2
df['spread'] = df['ask'] - df['bid']
df['imbalance'] = (df['bid_size'] - df['ask_size']) / (df['bid_size'] + df['ask_size'])


df['mid_change'] = df['mid_price'].diff()
df['imbalance_flip'] = df['imbalance'].diff().abs() > 0.1  # not useful here, but good practice

# Count how many quote updates had ZERO price change
no_move = df[df['mid_change'] == 0]
print(f"Quote updates with no price change: {len(no_move)} / {len(df)}")

# df.to_csv('AUDUSD_quotes_enhanced.csv', index=False)
