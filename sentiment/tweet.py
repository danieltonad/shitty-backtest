from httpx import AsyncClient
import os, asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

BEARER_TOKEN = os.getenv("X_API_KEY")

print(BEARER_TOKEN)

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "User-Agent": "StockSearchApp"
}

url = "https://api.x.com/2/tweets/search/recent"




async def fetch_tweets(query: str):
    params = {
        "query": query,
        "max_results": 100,  # between 10–100
        "tweet.fields": "author_id,created_at,lang,public_metrics"
    }

    async with AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    
def save_tweets_to_file(tweets, filename="tweets.json"):
    import json
    with open(filename, "w") as f:
        json.dump(tweets, f, indent=4)
    print(f"Saved {len(tweets.get('data', []))} tweets to {filename}")

async def main():
    query = '("market crash" OR "market rally" OR "stocks are up" OR "stocks are down" OR "wall street" OR "fed meeting" OR "interest rates" OR "inflation data" OR "economic data" OR "CPI" OR "FOMC" OR "unemployment report" OR "earnings report" OR "earnings season" OR "IPO" OR "short squeeze" OR "analyst upgrade" OR "stock market news" OR "financial markets" OR "trading day")'
    tweets = await fetch_tweets(query)
    for tweet in tweets.get("data", []):
        print(f"{tweet['created_at']} - {tweet['text']}\n")
    save_tweets_to_file(tweets)



if __name__ == "__main__":
    asyncio.run(main())