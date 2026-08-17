import os
import json
import csv
from pathlib import Path
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
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
state_file = Path("logs/btc_seasonality_open_state.json")
results_file = Path("logs/btc_seasonality_results.csv")

quote_req = CryptoLatestQuoteRequest(symbol_or_symbols=SYMBOL)
quote = data_client.get_crypto_latest_quote(quote_req)[SYMBOL]
exit_price = float(quote.bid_price)

positions = trading_client.get_all_positions()
held = next((p for p in positions if p.symbol == "BTCUSD"), None)

if held:
    trading_client.close_position("BTCUSD")

if state_file.exists() and held:
    state = json.loads(state_file.read_text())
    entry_price = state["entry_price"]
    notional = state["notional"]

    pnl_pct = (exit_price - entry_price) / entry_price * 100
    pnl_usd = notional * (pnl_pct / 100)

    # Read existing cumulative P&L so it keeps a running total
    cumulative_pnl = 0.0
    if results_file.exists():
        with open(results_file) as f:
            rows = list(csv.DictReader(f))
            if rows:
                cumulative_pnl = float(rows[-1]["cumulative_pnl_usd"])
    cumulative_pnl += pnl_usd

    # Write header if this is the first ever result
    write_header = not results_file.exists()
    with open(results_file, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "date", "entry_price", "exit_price", "pnl_pct", "pnl_usd", "cumulative_pnl_usd"
            ])
        writer.writerow([
            datetime.utcnow().date().isoformat(),
            f"{entry_price:.2f}",
            f"{exit_price:.2f}",
            f"{pnl_pct:.3f}",
            f"{pnl_usd:.2f}",
            f"{cumulative_pnl:.2f}"
        ])

    log_line = f"{datetime.utcnow().isoformat()},{SYMBOL},action=CLOSE,entry={entry_price:.2f},exit={exit_price:.2f},pnl_pct={pnl_pct:.3f}%"
    state_file.unlink()  # clear state, ready for tomorrow's trade
else:
    log_line = f"{datetime.utcnow().isoformat()},{SYMBOL},action=CLOSE,note=no_position_or_state_found"

print(log_line)
with open("logs/btc_seasonality_log.csv", "a") as f:
    f.write(log_line + "\n")