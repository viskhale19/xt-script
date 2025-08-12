from trading_bot import TradingBot

if __name__ == "__main__":
    config = {  # Hardcoded or parsed from .env
        "API_KEY": "...",
        "API_SECRET": "...",
        "EXCHANGE_NAME": "xt",
        "SYMBOL": "BTC/USDT:USDT",
        "LEVERAGE": 5,
        "MARGIN_PERCENT": 50,
        "TIMEFRAME_SECONDS": 300,
        "CONTRACT_NUM": 0
    }
    bot = TradingBot(config)
    bot.start()