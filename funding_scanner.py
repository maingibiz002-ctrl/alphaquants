import ccxt
import pandas as pd
import requests  # Required for sending data to your API


def fetch_binance_funding_rates(min_apr: float = 5.0):
    """Fetches funding rates for all USDT-M perpetual pairs and filters by minimum APR %."""
    exchange = ccxt.binance(
        {"enableRateLimit": True, "options": {"defaultType": "future"}}
    )

    print("Loading markets from Binance Futures...")
    exchange.load_markets()

    print("Fetching funding rates...")
    funding_data = exchange.fetch_funding_rates()

    opportunities = []

    for symbol, data in funding_data.items():
        # CCXT futures symbols typically end with ':USDT' or use standard linear formatting
        if not (symbol.endswith("/USDT:USDT") or symbol.endswith(":USDT")):
            continue

        raw_rate = data.get("fundingRate")
        if raw_rate is None:
            continue

        apr = raw_rate * 3 * 365 * 100
        strategy = (
            "Buy Spot / Short Perp" if raw_rate > 0 else "Long Perp / Sell Spot"
        )

        if abs(apr) >= min_apr:
            # Clean up symbol string for display (e.g., 'BTC/USDT:USDT' -> 'BTC/USDT')
            clean_symbol = symbol.split(":")[0]

            opportunities.append(
                {
                    "symbol": clean_symbol,
                    "funding_rate_8h_%": round(raw_rate * 100, 4),
                    "annualized_apr_%": round(apr, 2),
                    "next_funding_time": data.get("datetime"),
                    "recommended_strategy": strategy,
                }
            )

    df = pd.DataFrame(opportunities)
    if not df.empty:
        df = df.sort_values(
            by="annualized_apr_%", ascending=False
        ).reset_index(drop=True)
        return df.to_dict(orient="records")

    return []


def push_to_api(opportunities):
    api_url = "http://127.0.0.1:8000/api/arbitrage-data/"
    try:
        print(f"Attempting to push {len(opportunities)} items to {api_url}...")
        response = requests.post(api_url, json=opportunities)
        print(f"Server replied with Status Code: {response.status_code}")
        print(f"Server response body: {response.text}")
    except Exception as e:
        print(f"CRITICAL: Failed to connect to Django API: {e}")

if __name__ == "__main__":
    opps = fetch_binance_funding_rates(min_apr=5.0)
    if opps:
        print(f"Found {len(opps)} opportunities. Sending to backend...")
        push_to_api(opps)
    else:
        print("No opportunities found to send.")