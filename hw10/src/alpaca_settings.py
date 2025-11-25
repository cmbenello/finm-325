# src/alpaca_settings.py

import os

# Set these environment variables in your shell or .env:
#   export ALPACA_API_KEY_ID="..."
#   export ALPACA_API_SECRET_KEY="..."

API_KEY_ID = os.environ.get("ALPACA_API_KEY_ID", "")
API_SECRET_KEY = os.environ.get("ALPACA_API_SECRET_KEY", "")

# Paper trading base URL
BASE_URL = "https://paper-api.alpaca.markets"

# Data settings
SYMBOL = "AAPL"
TIMEFRAME = "1Min"   # Alpaca bar timeframe