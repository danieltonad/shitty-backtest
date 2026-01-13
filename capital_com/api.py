import os, json
from httpx import AsyncClient
from dotenv import load_dotenv

load_dotenv(override=True)

CAPITAL_IDENTITY = os.getenv("CAPITAL_IDENTITY")
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD")
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY")


CAPITAL_AUTH_HEADER = None


async def get_auth_header() -> None:
    global CAPITAL_AUTH_HEADER
    try:
        payload = json.dumps({
        "identifier": CAPITAL_IDENTITY,
        "password": CAPITAL_PASSWORD,
        "encryptedPassword": False
        })
        headers = {
            'X-CAP-API-KEY': CAPITAL_API_KEY,
            'Content-Type': 'application/json'
        }
        async with AsyncClient() as session:
            response = await session.post(f"https://demo-api-capital.backend-capital.com/api/v1/session", headers=headers, data=payload)
        # print(response.status_code ,response.json())
        header: dict = response.headers
        CST = header.get("CST")
        X_SECURITY_TOKEN = header.get("X-SECURITY-TOKEN")
        # print(CST, X_SECURITY_TOKEN)
        CAPITAL_AUTH_HEADER = {'X-SECURITY-TOKEN': X_SECURITY_TOKEN, 'CST': CST}
        return CAPITAL_AUTH_HEADER

    except Exception as e:
        print(f"Error during authentication: {e}")
        return CAPITAL_AUTH_HEADER
        



async def save_ohlc_data(epic: str, resolution: str = "MINUTE", n: int = 5000):
    """
    Fetch up to n OHLC bars using pagination.
    Capital.com allows max=1000 per page, so we loop until we get all.
    """
    await get_auth_header()
    try:
        headers = {
            "X-CAP-API-KEY": CAPITAL_API_KEY,
            "CST": CAPITAL_AUTH_HEADER.get("CST", ""),
            "X-SECURITY-TOKEN": CAPITAL_AUTH_HEADER.get("X-SECURITY-TOKEN", "")
        }

        all_prices = []
        per_page = 1000
        page = 1

        async with AsyncClient() as session:
            while len(all_prices) < n:
                url = (
                    f"https://api-capital.backend-capital.com/api/v1/prices/"
                    f"{epic}?resolution={resolution}&max={per_page}&pageNumber={page}"
                )
                resp = await session.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                prices = data.get("prices", [])
                if not prices:
                    break  # no more data

                all_prices.extend(prices)
                print(f"Fetched page {page} | Total so far: {len(all_prices)}", end="\r")

                if len(prices) < per_page:
                    break  # last page reached
                page += 1

        # Trim to requested n
        all_prices = all_prices[:n]
        all_prices.sort(key=lambda p: p["snapshotTimeUTC"])

        filename = f"./data/{epic}_{resolution}.csv"
        append_csv(filename, ["timestamp", "open", "high", "low", "close"])

        for i, p in enumerate(all_prices):
            try:
                t = p["snapshotTimeUTC"]
                o = float(p["openPrice"]["bid"])
                h = float(p["highPrice"]["bid"])
                l = float(p["lowPrice"]["bid"])
                c = float(p["closePrice"]["bid"])
            except (KeyError, TypeError, ValueError):
                continue

            append_csv(filename, [t, o, h, l, c])


    except Exception as e:
        print(f"Error fetching OHLC data: {e}")
        return []
    


def append_csv(filename: str, row: list):
    """Append a row to a CSV file."""
    import csv
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(row)