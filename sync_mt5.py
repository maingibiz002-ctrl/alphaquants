import os
import sys
import time
import django

# 1. Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alpha_quant_trades.settings')
django.setup()

import MetaTrader5 as mt5
from django.contrib.auth.models import User
from tradelog.models import Trade

# 2. Configuration
DJANGO_USERNAME = "admin"  # User to assign trades to

def sync_trades():
    # Initialize MT5 connection
    if not mt5.initialize():
        print("Failed to initialize MT5 terminal, error code:", mt5.last_error())
        return

    print("Connected to MT5 successfully!")
    user = User.objects.filter(username=DJANGO_USERNAME).first()
    
    if not user:
        print(f"User '{DJANGO_USERNAME}' not found in Django database.")
        return

    # Fetch all open positions in MT5
    positions = mt5.positions_get()
    
    if positions is None:
        print("No open positions found or failed to fetch.")
    else:
        print(f"Found {len(positions)} active position(s). Syncing...")
        
        for pos in positions:
            action_type = "BUY" if pos.type == 0 else "SELL"
            
            # Create or update trade directly in Django database
            trade, created = Trade.objects.update_or_create(
                ticket=pos.ticket,
                defaults={
                    'user': user,
                    'symbol': pos.symbol,
                    'action': action_type,
                    'lot_size': pos.volume,
                    'entry_price': pos.price_open,
                    'profit_loss': pos.profit,
                    'status': 'OPEN',
                    'exit_price': 0.0,
                }
            )
            
            status_msg = "Created" if created else "Updated"
            print(f"[{status_msg}] Ticket #{pos.ticket} | {pos.symbol} {action_type} | Profit: ${pos.profit:.2f}")

    mt5.shutdown()

if __name__ == "__main__":
    # Run sync once (or put in a loop with time.sleep for live polling)
    sync_trades()