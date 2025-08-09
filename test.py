
# ========== Load Config ==========
from datetime import datetime
import json
import os
import traceback

import ccxt
import dotenv
import main

dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
EXCHANGE_NAME = os.getenv("EXCHANGE", "xt").lower()
SYMBOL = os.getenv("SYMBOL", "BTC/USDT:USDT")
LEVERAGE = float(os.getenv("LEVERAGE", 1))
MARGIN_PERCENT = float(os.getenv("MARGIN_PERCENT", 50))
MIN_POSITION_SIZE = float(os.getenv("MIN_POSITION_SIZE", 100))
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

# ========== Exchange Setup ==========
exchange_class = getattr(ccxt, EXCHANGE_NAME)
exchange = exchange_class({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})
def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")
def pretty_json(msg: dict) -> str:
    return json.dumps(msg, sort_keys=True, indent=2)

def check_position_profit():
    positions = exchange.fetch_positions([SYMBOL])
    for pos in positions:
        if float(pos['contracts']) > 0:
            entry_price = float(pos['entryPrice'])
            mark_price = float(pos.get('markPrice') or exchange.fetch_ticker(SYMBOL)['last'])
            side = pos['side'].lower()  # 'long' or 'short'
            # pnl = float(pos.get('unrealizedPnl', 0))
            profit = mark_price > entry_price if side == 'long' else mark_price < entry_price

            print(f"--- Position Info ---")
            print(f"Side       : {side.upper()}")
            print(f"Entry Price: {entry_price}")
            print(f"Mark Price : {mark_price}")
            # print(f"Unrealized PnL: {pnl}")
            print(f"In Profit? : {'Yes' if profit else 'No'}")
            return

    print("No open position.")
exchange.load_markets()
market = exchange.market(SYMBOL)
try:
    exchange.set_leverage(int(5), SYMBOL, {'positionSide': 'LONG'})
    exchange.set_leverage(int(5), SYMBOL, {'positionSide': 'SHORT'})
except Exception as e:
    print(f"[WARN] Could not set leverage: {e}")

try:
    balance = exchange.fetch_balance()
    usdt = balance['total']['USDT']
    log(f'usdt amount: {usdt}')

except Exception as e:
    print(f"[WARN] Could not fetch balance: {e}")

try:
    precision = market['precision']['amount']
    log(f'precision is: {precision}')
    log(f'symbol is: {SYMBOL}')
    exchange.create_market_order(SYMBOL, 'buy', '10', None, {
            'positionSide': 'SHORT',
            'reduceOnly': True
        })
except Exception as e:
    print(f"[WARN] Could not create market order: {e}")
    print(traceback.format_exc())
try:
    balance = exchange.fetch_balance()
    usdt_balance = balance['total']['USDT']
    log(f'usdt amount: {usdt_balance}')
    margin = usdt_balance * (MARGIN_PERCENT / 100)
    log(f'margin is: {margin}')
    position_size = margin * LEVERAGE
    log(f'position size: {position_size}')
    trend = 'up'
    side = 'buy' if trend == 'up' else 'sell'
    position_side = 'LONG' if side == 'buy' else 'SHORT'
    last_price = exchange.fetch_ticker(SYMBOL)['last']
    log(f'last price: {last_price}')
    
    amount = int(position_size / (last_price * main.CONTRACT_SIZE))
    log(f'contract amount: {amount}')

except Exception as e:
    print(f'[WARN] no market data: {e}')
    print(traceback.format_exc())
try:
    positions = exchange.fetch_positions(["BTC/USDT:USDT"])
    log(f'positions is: {pretty_json(positions)}')
    check_position_profit()
except Exception as e:
    print(f"[WARN] Could not fetch orders: {e}")
    print(traceback.format_exc())
