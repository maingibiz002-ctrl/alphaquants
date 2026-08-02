import asyncio
import os
from dotenv import load_dotenv
import ccxt.async_support as ccxt

load_dotenv()

API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
API_SECRET = os.getenv("BINANCE_TESTNET_SECRET")

if not API_KEY or not API_SECRET:
    raise ValueError("❌ Missing API credentials. Check your .env file!")

class BinanceFuturesBot:
    def __init__(self, api_key: str, api_secret: str):
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Target USDT-M Futures
            }
        })
        
        # 🔑 UPDATE HERE: Use enable_demo_trading instead of set_sandbox_mode
        self.exchange.enable_demo_trading(True)

    async def run_diagnostics(self, symbol: str = "BTC/USDT"):
        try:
            print("🔄 Connecting to Binance Demo Trading...")
            
            # Fetch Balance
            balance = await self.exchange.fetch_balance()
            usdt_free = balance['free'].get('USDT', 0.0)
            print(f"💰 Available Demo Balance: ${usdt_free:,.2f} USDT")

            # Fetch Funding Rate Info
            funding_info = await self.exchange.fetch_funding_rate(symbol)
            funding_rate = funding_info.get('fundingRate', 0.0)
            apy = funding_rate * 3 * 365 * 100

            print(f"\n📊 {symbol} Market Metrics:")
            print(f"  • Current 8-Hour Funding Rate: {funding_rate * 100:.4f}%")
            print(f"  • Projected Annualized APY:   {apy:.2f}%")

            # Execute Test Market Short Order
            if usdt_free > 10:
                amount = 0.001  # ~0.001 BTC
                print(f"\n🚀 Executing Test Short Order ({amount} {symbol.split('/')[0]})...")
                
                order = await self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side='sell',
                    amount=amount,
                    params={'leverage': 1}
                )
                print(f"✅ Trade Executed! Order ID: {order['id']}")
            else:
                print("\n⚠️ Insufficient demo USDT balance to open position.")

        except Exception as e:
            print(f"\n❌ Execution Error: {e}")
        finally:
            await self.exchange.close()

async def main():
    bot = BinanceFuturesBot(API_KEY, API_SECRET)
    await bot.run_diagnostics(symbol="BTC/USDT")

if __name__ == "__main__":
    asyncio.run(main())