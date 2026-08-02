import os
import ccxt
from dotenv import load_dotenv

# Load environment variables from your project's .env file
load_dotenv()

class RealTimeArbitrageExecutor:
    def __init__(self, symbol, amount_usd=50.0):
        self.symbol = symbol  # e.g. 'BTC/USDT'
        self.amount_usd = amount_usd
        
        # Pull keys securely from environment variables
        api_key = os.getenv('BINANCE_API_KEY')
        secret_key = os.getenv('BINANCE_SECRET_KEY')

        # Initialize exchange with environment credentials
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        # Enable Binance Demo Trading mode to route requests to demo.binance.com
        self.exchange.enableDemoTrading(True)

    def execute_live_legs(self):
        logs = []
        try:
            logs.append(f"[System] Initialized demo execution pipeline for {self.symbol}...")
            
            # Fetch current ticker price to calculate quantities
            ticker = self.exchange.fetch_ticker(self.symbol)
            mark_price = ticker['last']
            quantity = self.amount_usd / mark_price
            
            logs.append(f"[Market] Current price for {self.symbol}: ${mark_price}. Calculated size: {quantity:.4f}")

            # --- LEG 1: Spot Market Order ---
            self.exchange.options['defaultType'] = 'spot'
            logs.append(f"[Leg 1] Dispatching BUY market order on Spot for {quantity:.4f} {self.symbol.split('/')[0]}...")
            
            spot_order = self.exchange.create_market_buy_order(self.symbol, quantity)
            logs.append(f"[Leg 1 Success] Spot Order ID: {spot_order.get('id')} filled at ${spot_order.get('average', mark_price)}")

            # --- LEG 2: Perpetual Futures Short Order ---
            self.exchange.options['defaultType'] = 'future'
            logs.append(f"[Leg 2] Dispatching SELL (Short) market order on Futures for {quantity:.4f} {self.symbol}...")
            
            futures_order = self.exchange.create_market_sell_order(self.symbol, quantity)
            logs.append(f"[Leg 2 Success] Futures Order ID: {futures_order.get('id')} filled at ${futures_order.get('average', mark_price)}")

            logs.append(f"[Complete] Delta-neutral arbitrage position successfully locked on demo exchange!")

        except Exception as e:
            logs.append(f"[Error] Execution failed: {str(e)}")

        return logs

if __name__ == '__main__':
    print("--- TESTING ARBITRAGE EXECUTION ENGINE ---")
    engine = RealTimeArbitrageExecutor(symbol='BTC/USDT', amount_usd=55.0)
    
    logs = engine.execute_live_legs()
    print("\nExecution Results:")
    for log in logs:
        print(log)