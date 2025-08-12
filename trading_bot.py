import os
import sys
import time
import ccxt
import dotenv
from datetime import datetime, timezone, UTC
import threading
import traceback
from typing import List, Tuple, Callable, Dict, Optional


class TradingBot:
    """
    Core trading bot that runs in its own thread and uses a log callback to emit messages.
    - config: dict of configuration
    - log_cb: function(str) -> None
    """

    def __init__(self, config: Dict, log_cb: Optional[Callable[[str], None]] = None):
        self.config = config.copy()
        self.log_cb = log_cb or (lambda s: print(s))
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running_lock = threading.Lock()
        self._is_running = False

    # helper logging
    def log(self, msg: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        text = f"[{ts}] {msg}"
        try:
            self.log_cb(text)
        except Exception:
            # Never let logging break the bot
            print("Log callback error:", traceback.format_exc())
            print(text)

    def start(self):
        with self._running_lock:
            if self._is_running:
                self.log("Bot already running")
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self._is_running = True
            self.log("TradingBot.start() called")

    def stop(self, timeout: float = 10.0):
        with self._running_lock:
            if not self._is_running:
                self.log("Bot is not running")
                return
            self.log("Stopping TradingBot...")
            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout)
            self._is_running = False
            self.log("TradingBot stopped")

    def is_running(self) -> bool:
        with self._running_lock:
            return self._is_running
    # the main loop - call your existing interval-based logic here

    def _run(self):
        try:
            self.log(f"Bot loop started with config: {self.config}")
            # Example main loop: call _run_once repeatedly until stop requested
            while not self._stop_event.is_set():
                start_ts = time.time()
                try:
                    # PUT YOUR CORE STEP HERE:
                    # You can call self._run_once() where _run_once implements:
                    # - fetch candles
                    # - compute HA
                    # - detect trend
                    # - place/close orders
                    # - log actions via self.log(...)
                    self._run_once()
                except Exception as e:
                    self.log(f"[ERROR] run step failed: {e}")
                    self.log(traceback.format_exc())

                # respect a configured polling interval if present, otherwise small sleep
                interval = float(self.config.get("POLL_INTERVAL", 60))
                elapsed = time.time() - start_ts
                sleep_for = max(0.0, interval - elapsed)
                # early exit responsiveness
                for _ in range(int(sleep_for // 1)):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
                else:
                    if not self._stop_event.is_set():
                        time.sleep(sleep_for % 1)
            self.log("Bot loop exiting normally")
        except Exception as e:
            self.log(f"[FATAL] unexpected exception: {e}")
            self.log(traceback.format_exc())
        finally:
            with self._running_lock:
                self._is_running = False
    # Placeholder single-step run - replace with your real logic

    def _run_once(self):
        """
        Example placeholder. Replace this by importing and calling your actual functions
        (fetch ohlcv, compute HA, detect trend, open/close positions).
        Use self.log(...) to report.
        """
        # Example: log heartbeat and sleep
        self.log("Heartbeat - replace _run_once with real trading logic.")
        # If you want shorter immediate testing, set POLL_INTERVAL in config.
        time.sleep(0.1)


# ========== Load Config ==========
dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
EXCHANGE_NAME = os.getenv("EXCHANGE", "xt").lower()
SYMBOL = os.getenv("SYMBOL", "BTC/USDT:USDT")
LEVERAGE = float(os.getenv("LEVERAGE", 5))
MARGIN_PERCENT = float(os.getenv("MARGIN_PERCENT", 50))
TIMEFRAME_SECONDS = int(os.getenv("TIMEFRAME_SECONDS", 300))  # default 5m
CONTRACT_NUM = int(os.getenv("CONTRACT_NUM", 0))

CONTRACT_SIZE = 0.0001
# ========== Exchange Setup ==========
exchange_class = getattr(ccxt, EXCHANGE_NAME)
exchange = exchange_class({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})
exchange.load_markets()
if SYMBOL not in exchange.markets:
    raise ValueError(f"Symbol '{SYMBOL}' not found in exchange markets")

market = exchange.market(SYMBOL)
if market.get('contract', False):
    try:
        exchange.set_leverage(int(LEVERAGE), SYMBOL, {'positionSide': 'LONG'})
        exchange.set_leverage(int(LEVERAGE), SYMBOL, {'positionSide': 'SHORT'})
    except Exception as e:
        print(f"[WARN] Could not set leverage: {e}")
else:
    print(f"[WARN] {SYMBOL} is not a contract market; leverage not set.")
# ========== Utilities ==========


def log(msg):
    log_filename = f"logging-{datetime.now().strftime('%Y%m%d')}.log"
    string = f"[{datetime.now().isoformat()}] {msg}\n"
    print(string.strip())
    with open(log_filename, 'a') as f:
        f.write(string)


def int_to_timeframe(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    elif seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        raise ValueError(
            "Timeframe must be divisible by 60 or less than 60 seconds.")


def get_candles(symbol: str, seconds: int, limit: int = 6):
    now = int(time.time())
    wait_time = seconds - (now % seconds) + 2
    log(f"Waiting {wait_time}s for next finalized candle...")
    time.sleep(wait_time)
    tf = int_to_timeframe(seconds)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
    return ohlcv[:-1]


def to_heikin_ashi(candles: List[List[float]]) -> List[dict]:
    ha_candles = []
    for i, c in enumerate(candles):
        o, h, l, cl = c[1:5]
        ha_close = (o + h + l + cl) / 4
        ha_open = (ha_candles[i-1]['open'] + ha_candles[i-1]
                   ['close']) / 2 if i > 0 else (o + cl) / 2
        ha_high = max(h, ha_open, ha_close)
        ha_low = min(l, ha_open, ha_close)
        ha_candle = {
            'open': ha_open,
            'high': ha_high,
            'low': ha_low,
            'close': ha_close
        }
        ha_candles.append(ha_candle)
    return ha_candles


def detect_trend_change(c1: dict, c2: dict) -> Tuple[bool, str]:
    trend1 = 'up' if c1['close'] > c1['open'] else 'down'
    trend2 = 'up' if c2['close'] > c2['open'] else 'down'
    return trend1 != trend2, trend2


def get_balance():
    balance = exchange.fetch_balance()
    return balance['total']['USDT']


def check_position_profit():
    positions = exchange.fetch_positions([SYMBOL])
    for pos in positions:
        if float(pos['contracts']) > 0:
            entry_price = float(pos['entryPrice'])
            mark_price = float(pos.get('markPrice')
                               or exchange.fetch_ticker(SYMBOL)['last'])
            side = pos['side']
            profit = mark_price > entry_price if side == 'long' else mark_price < entry_price

            log(f"--- Position Info ---")
            log(f"Side       : {side.upper()}")
            log(f"Entry Price: {entry_price}")
            log(f"Mark Price : {mark_price}")
            log(f"In Profit? : {'Yes' if profit else 'No'}")
            return

    print("No open position.")


def get_open_position():
    positions = exchange.fetch_positions([SYMBOL])
    for p in positions:
        if float(p['contracts']) > 0:
            return p
    return None


def close_position(pos):
    side = 'sell' if pos['side'] == 'long' else 'buy'
    amount = float(pos['contracts'])
    position_side = 'LONG' if side == 'sell' else 'SHORT'
    check_position_profit()
    exchange.create_market_order(SYMBOL, side, amount, None, {
        'reduceOnly': True,
        'positionSide': position_side
    })
    log(f"Closed position: {side} {amount} {SYMBOL} [{position_side}]")


def open_position(trend):
    side = 'buy' if trend == 'up' else 'sell'
    position_side = 'LONG' if side == 'buy' else 'SHORT'
    last_price = exchange.fetch_ticker(SYMBOL)['last']
    if CONTRACT_NUM > 0:  # fixed
        amount = CONTRACT_NUM
        exchange.create_market_order(SYMBOL, side, amount, None, {
            'positionSide': position_side
        })
        log(f"Opened position: {side} {amount} {SYMBOL} [{position_side}]")
        log(f'Volume: {amount*CONTRACT_SIZE*last_price}')
    else:
        usdt_balance = get_balance()
        margin = usdt_balance * (MARGIN_PERCENT / 100)
        position_size = margin * LEVERAGE
        amount = int(position_size / (last_price * CONTRACT_SIZE))
        exchange.create_market_order(SYMBOL, side, amount, None, {
            'positionSide': position_side
        })
        log(f"Opened position: {side} {amount} {SYMBOL} [{position_side}]")
        log(f'With data:\nusdt_balance: {usdt_balance}, margin: {(amount*CONTRACT_SIZE*last_price)/LEVERAGE}, position size: {amount*CONTRACT_SIZE*last_price}')

# ========== Main Loop ==========


def run():
    log("Bot started")
    last_candle_time = 0

    while True:
        try:
            candles = get_candles(SYMBOL, 300, limit=6)
            if candles[-1][0] == last_candle_time:
                time.sleep(5)
                continue
            last_candle_time = candles[-1][0]
            ha = to_heikin_ashi(candles)
            log("Latest regular and HA candles:")
            for i in range(len(ha)):
                ts = datetime.fromtimestamp(
                    candles[i][0]/1000, UTC).strftime('%Y-%m-%d %H:%M')
                log(f"[{ts}] Regular: O={candles[i][1]} C={candles[i][4]} | HA: O={ha[i]['open']:.2f} C={ha[i]['close']:.2f}")

            trend_changed, new_trend = detect_trend_change(ha[-2], ha[-1])
            log(f"Trend changed: {trend_changed}, New trend: {new_trend}")

            if trend_changed:
                open_pos = get_open_position()
                if open_pos:
                    close_position(open_pos)
                open_position(new_trend)
        except KeyboardInterrupt:
            log(f"Graceful exit ....")
            sys.exit(0)


if __name__ == '__main__':
    run()
