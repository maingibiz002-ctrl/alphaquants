import ccxt
import pandas as pd


def fetch_binance_funding_rates(min_apr: float = 10.0):
    """Fetches funding rates for all USDT-M perpetual pairs and filters by minimum APR %."""
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

    print("Fetching funding rates from Binance Futures...")
    funding_data = exchange.fetch_funding_rates()

    opportunities = []

    for symbol, data in funding_data.items():
        if not symbol.endswith(':USDT'):
            continue

        raw_rate = data.get('fundingRate')
        if raw_rate is None:
            continue

        apr = raw_rate * 3 * 365 * 100

        strategy = "Buy Spot / Short Perp" if raw_rate > 0 else "Long Perp / Sell Spot"

        if abs(apr) >= min_apr:
            opportunities.append({
                'symbol': symbol.split(':')[0],  # e.g., 'BTC/USDT'
                'funding_rate_8h_%': round(raw_rate * 100, 4),
                'annualized_apr_%': round(apr, 2),
                'next_funding_time': data.get('datetime'),
                'recommended_strategy': strategy,
            })

    df = pd.DataFrame(opportunities)
    if not df.empty:
        df = df.sort_values(by='annualized_apr_%', ascending=False).reset_index(drop=True)
        return df.to_dict(orient='records')

    return []


if __name__ == '__main__':
    opps = fetch_binance_funding_rates(min_apr=5.0)
    print("\n--- TOP FUNDING RATE ARBITRAGE OPPORTUNITIES ---")
    df_preview = pd.DataFrame(opps)
    if not df_preview.empty:
        print(df_preview.to_string(index=False))
    else:
        print("No opportunities found.")