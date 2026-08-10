import requests
import json

def test_tv_data():
    url = "https://scanner.tradingview.com/cfd/scan"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "symbols": {
            "tickers": [
                "TVC:DE10Y", 
                "TVC:UK10Y", 
                "TVC:JP10Y", 
                "TVC:VIX",
                "OANDA:XAGUSD"
            ],
            "query": { "types": [] }
        },
        "columns": ["close"]
    }
    try:
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=5)
        if res.status_code == 200:
            data = res.json()
            print("Response:", json.dumps(data, indent=2))
        else:
            print("Status code:", res.status_code)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_tv_data()
