# cli.py
import os
from trading_bot import TradingBot
import dotenv
import time

if __name__ == "__main__":
    dotenv.load_dotenv()
    config = {
        "API_KEY": os.getenv("API_KEY"),
        "API_SECRET": os.getenv("API_SECRET"),
        "EXCHANGE_NAME": os.getenv("EXCHANGE", "xt").lower(),
        "SYMBOL": os.getenv("SYMBOL", "BTC/USDT:USDT"),
        "LEVERAGE": float(os.getenv("LEVERAGE", 5)),
        "MARGIN_PERCENT": float(os.getenv("MARGIN_PERCENT", 50)),
        "TIMEFRAME_SECONDS": int(os.getenv("TIMEFRAME_SECONDS", 300)),  # default 5m
        "CONTRACT_NUM": int(os.getenv("CONTRACT_NUM", 0)),
    }

    def print_log(s): print(s)

    bot = TradingBot(config=config, log_cb=print_log)
    bot.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot.stop()
