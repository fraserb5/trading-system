import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

client = TradingClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

account = client.get_account()
print("Connected successfully.")
print(f"Account status: {account.status}")
print(f"Cash: ${account.cash}")
print(f"Portfolio value: ${account.portfolio_value}")