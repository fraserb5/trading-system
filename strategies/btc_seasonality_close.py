import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from datetime import datetime

load_dotenv()

client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

SYMBOL = "BTC/USD"

positions = client.get_all_positions()
held = next((p for p in positions if p.symbol == "BTCUSD"), None)

if held:
    client.close_position("BTCUSD")
    log_line = f"{datetime.utcnow().isoformat()},{SYMBOL},action=CLOSE,qty={held.qty}"
else:
    log_line = f"{datetime.utcnow().isoformat()},{SYMBOL},action=CLOSE,note=no_position_found"

print(log_line)
with open("logs/btc_seasonality_log.csv", "a") as f:
    f.write(log_line + "\n")