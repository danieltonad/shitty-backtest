import requests

# url = "https://www.reddit.com/r/stocks/hot.json"
# headers = {"User-Agent": "my_script_v1"}
# response = requests.get(url, headers=headers)
# data = response.json()
# print(f"Total posts fetched: {len(data['data']['children'])}")
# for post in data["data"]["children"]:
#     p = post["data"]
#     # print(f"Title: {p['title']}")
#     # print(f"Upvotes: {p['ups']}")
#     print(f"URL: {p['url']}")




res = requests.get("https://www.reddit.com/r/stocks/comments/1otfr53/rstocks_daily_discussion_monday_nov_10_2025/")
print(res.text)

with open("reddit_post.html", "w", encoding="utf-8") as f:
    f.write(res.text)
