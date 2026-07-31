import requests
from bs4 import BeautifulSoup

def fetch_nse_market_data():
    """
    Scrapes live equities data for Nairobi Securities Exchange.
    """
    url = "https://afx.kwayisi.org/nse/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    stocks = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select('table tr')
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    ticker = cols[0].text.strip()
                    name = cols[1].text.strip()
                    raw_volume = cols[2].text.strip().replace(',', '')
                    raw_price = cols[3].text.strip().replace(',', '')
                    raw_change = cols[4].text.strip().replace('%', '').replace('+', '')

                    try:
                        price = float(raw_price)
                        change = float(raw_change)
                        volume = int(raw_volume) if raw_volume else 0

                        stocks.append({
                            'ticker': ticker,
                            'name': name,
                            'price': price,
                            'change': change,
                            'volume': volume
                        })
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error fetching NSE stock data: {e}")

    return stocks