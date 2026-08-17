import os
import json
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoLatestQuoteRequest
from datetime import datetime

load_dotenv()

trading_client = TradingClient(
    os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), paper=True
)
data_client = CryptoHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
)

SYMBOL = "BTC/USD"
NOTIONAL_USD = 1000

# Get current price before entering, so we can measure performance later
quote_req = CryptoLatestQuoteRequest(symbol_or_symbols=SYMBOL)
quote = data_client.get_crypto_latest_quote(quote_req)[SYMBOL]
entry_price = float(quote.ask_price)

order = MarketOrderRequest(
    symbol=SYMBOL, notional=NOTIONAL_USD, side=OrderSide.BUY, time_in_force=TimeInForce.GTC
)
trading_client.submit_order(order)

# Save entry details so the close script can calculate P&L
state = {
    "entry_time": datetime.utcnow().isoformat(),
    "entry_price": entry_price,
    "notional": NOTIONAL_USD
}
with open("logs/btc_seasonality_open_state.json", "w") as f:
    json.dump(state, f)

log_line = f"{state['entry_time']},{SYMBOL},action=OPEN,price={entry_price:.2f},notional={NOTIONAL_USD}"
print(log_line)
with open("logs/btc_seasonality_log.csv", "a") as f:
    f.write(log_line + "\n")