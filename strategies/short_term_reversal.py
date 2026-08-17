import os
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# Static stand-in for "top 100 US stocks by market cap" (large, liquid names)
UNIVERSE = [
    "AAPL","MSFT","NVDA","GOOGL","GOOG","AMZN","META","BRK.B","LLY","AVGO",
    "TSLA","JPM","WMT","V","XOM","UNH","MA","PG","COST","JNJ",
    "HD","ORCL","MRK","ABBV","BAC","CVX","KO","AMD","PEP","CRM",
    "ADBE","NFLX","TMO","MCD","LIN","CSCO","ABT","ACN","WFC","DHR",
    "TXN","PM","INTU","VZ","DIS","CAT","AMGN","IBM","NEE","NOW",
    "GE","QCOM","CMCSA","UNP","SPGI","AMAT","LOW","BKNG","ISRG","PFE",
    "HON","T","COP","RTX","UBER","GS","BLK","ELV","LMT","SYK",
    "DE","PLD","SBUX","MDT","ADP","TJX","GILD","MMC","VRTX","REGN",
    "SCHW","BSX","ETN","CB","MU","BA","PANW","ADI","KLAC","LRCX",
    "SO","ZTS","CI","MO","PGR","FI","APH","DUK","BMY","TGT"
]

LEG_NOTIONAL = 5000       # total $ allocated to the long side, and separately to the short side
NUM_LONG = 10
NUM_SHORT = 10
LOOKBACK_DAYS = 45        # enough calendar days to get ~21+ trading days of history

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 1. Pull recent daily bars for the whole universe
request = StockBarsRequest(
    symbol_or_symbols=UNIVERSE,
    timeframe=TimeFrame.Day,
    start=datetime.now() - timedelta(days=LOOKBACK_DAYS)
)
bars = data_client.get_stock_bars(request).df

# 2. Compute weekly (5-trading-day) and monthly (21-trading-day) returns per symbol
weekly_returns = {}
monthly_returns = {}
for symbol in UNIVERSE:
    try:
        closes = bars.loc[symbol]["close"]
    except KeyError:
        continue  # symbol had no data returned, skip it
    if len(closes) < 22:
        continue  # not enough history yet
    weekly_returns[symbol] = closes.iloc[-1] / closes.iloc[-6] - 1
    monthly_returns[symbol] = closes.iloc[-1] / closes.iloc[-22] - 1

# 3. Rank: long = worst weekly performers, short = best monthly performers (excluding longs)
sorted_by_week = sorted(weekly_returns.items(), key=lambda x: x[1])
longs = [s for s, _ in sorted_by_week[:NUM_LONG]]

sorted_by_month = sorted(monthly_returns.items(), key=lambda x: x[1], reverse=True)
shorts = []
for symbol, _ in sorted_by_month:
    if symbol not in longs:
        shorts.append(symbol)
    if len(shorts) == NUM_SHORT:
        break

# 4. Liquidate any existing position in this universe that isn't in this week's long/short list
current_positions = trading_client.get_all_positions()
target_symbols = set(longs) | set(shorts)
for p in current_positions:
    if p.symbol in UNIVERSE and p.symbol not in target_symbols:
        trading_client.close_position(p.symbol)

# 5. Also close positions that need to flip side (e.g. was long, now short, or vice versa)
existing_by_symbol = {p.symbol: p for p in current_positions}
for symbol in target_symbols:
    pos = existing_by_symbol.get(symbol)
    if pos:
        is_long = float(pos.qty) > 0
        should_be_long = symbol in longs
        if is_long != should_be_long:
            trading_client.close_position(symbol)

# 6. Place new orders for this week's target long/short list (skip if already correctly positioned)
current_positions = trading_client.get_all_positions()  # refresh after closes
already_held = {p.symbol for p in current_positions}

per_long_notional = LEG_NOTIONAL / len(longs) if longs else 0
per_short_notional = LEG_NOTIONAL / len(shorts) if shorts else 0

for symbol in longs:
    if symbol not in already_held:
        order = MarketOrderRequest(
            symbol=symbol, notional=round(per_long_notional, 2),
            side=OrderSide.BUY, time_in_force=TimeInForce.DAY
        )
        trading_client.submit_order(order)

for symbol in shorts:
    if symbol not in already_held:
        order = MarketOrderRequest(
            symbol=symbol, notional=round(per_short_notional, 2),
            side=OrderSide.SELL, time_in_force=TimeInForce.DAY
        )
        trading_client.submit_order(order)

# 7. Log this week's rebalance
log_line = f"{datetime.utcnow().isoformat()},longs={'|'.join(longs)},shorts={'|'.join(shorts)}"
print(log_line)
with open(log_dir / "short_term_reversal_log.csv", "a") as f:
    f.write(log_line + "\n")

# 8. Track approximate performance: mark-to-market value of this strategy's positions only
positions_now = trading_client.get_all_positions()
strategy_positions = [p for p in positions_now if p.symbol in UNIVERSE]
total_unrealized_pl = sum(float(p.unrealized_pl) for p in strategy_positions)
total_market_value = sum(abs(float(p.market_value)) for p in strategy_positions)

results_file = log_dir / "short_term_reversal_results.csv"
write_header = not results_file.exists()
with open(results_file, "a", newline="") as f:
    writer = csv.writer(f)
    if write_header:
        writer.writerow(["date", "num_longs", "num_shorts", "total_market_value", "total_unrealized_pnl"])
    writer.writerow([
        datetime.utcnow().date().isoformat(), len(longs), len(shorts),
        f"{total_market_value:.2f}", f"{total_unrealized_pl:.2f}"
    ])