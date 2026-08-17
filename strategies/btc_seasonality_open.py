import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime

load_dotenv()

client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

SYMBOL = "BTC/USD"
NOTIONAL_USD = 1000  # how much (fake) money to put into the trade each night

order = MarketOrderRequest(
    symbol=SYMBOL,
    notional=NOTIONAL_USD,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.GTC
)
client.submit_order(order)

log_line = f"{datetime.utcnow().isoformat()},{SYMBOL},action=OPEN,notional={NOTIONAL_USD}"
print(log_line)
with open("logs/btc_seasonality_log.csv", "a") as f:
    f.write(log_line + "\n")