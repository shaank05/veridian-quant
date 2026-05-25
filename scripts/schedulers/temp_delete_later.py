import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Setup authorization headers
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# Testing with a prominent stock (e.g., Reliance Industries Limited - RIL)
INSTRUMENT_KEY = "NSE_EQ|INE002A01018" 

def check_historical_candles():
    """Queries the V3 Historical Candle Data API to check data array bounds."""
    print("\n--- Testing Upstox V3 Historical Candle Data API ---")
    
    # URL structure for V3 Historical Candles: /v3/historical-candle/{instrument_key}/{unit}/{interval}
    url = f"https://api.upstox.com/v3/historical-candle/{INSTRUMENT_KEY}/days/1"
    params = {
        "to_date": "2026-05-22"  # Adjust to the latest completed trading day
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            res_data = response.json()
            candles = res_data.get("data", {}).get("candles", [])
            
            if candles:
                print("\nSample Candle Array Structure (Latest Day):")
                print(json.dumps(candles[0], indent=2))
                
                print(f"\nArray Length: {len(candles[0])} items.")
                print("Index mapping lookup:")
                print("  [0]: Timestamp")
                print("  [1]: Open")
                print("  [2]: High")
                print("  [3]: Low")
                print("  [4]: Close")
                print("  [5]: Volume")
                if len(candles[0]) > 6:
                    print(f"  [6]: Extra field detected -> {candles[0][6]}")
            else:
                print("No candles returned inside data block.")
        else:
            print(f"Error payload: {response.text}")
            
    except Exception as e:
        print(f"Execution Error: {e}")

def check_market_quote_ohlc():
    """Queries the V3 Market Quote OHLC snapshot endpoint."""
    print("\n--- Testing Upstox V3 Market Quote OHLC API ---")
    url = "https://api.upstox.com/v3/market-quote/ohlc"
    params = {
        "instrument_key": INSTRUMENT_KEY,
        "interval": "1d"
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            print("\nMarket Quote JSON Response Object:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error payload: {response.text}")
            
    except Exception as e:
        print(f"Execution Error: {e}")

if __name__ == "__main__":
    if ACCESS_TOKEN == "YOUR_ACCESS_TOKEN":
        print("⚠️ Warning: Update your access token inside your .env file or script first.")
    check_historical_candles()
    check_market_quote_ohlc()