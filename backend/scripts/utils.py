import json
import urllib.request
import urllib.parse

def get_live_multi_asset_prices():
    prices = {"XAUUSD": 0.0, "XAGUSD": 0.0, "USOIL": 0.0, "DXY": 0.0, "US10Y": 0.0, "SPX": 0.0, "DJI": 0.0, "DAX": 0.0, "NI225": 0.0, "VIX": 0.0, "GSR": 0.0}
    
    # 1. Prioritas 1: Ambil dari TradingView CFD Scan untuk semua aset (Batch Request)
    try:
        url_tv = "https://scanner.tradingview.com/cfd/scan"
        payload_tv = {
            "symbols": {
                "tickers": ["FX_IDC:XAUUSD", "FX_IDC:XAGUSD", "FX:EURUSD", "FX:GBPUSD", "FX:USDJPY", "TVC:USOIL", "TVC:DXY", "TVC:US10Y", "TVC:VIX"],
                "query": { "types": [] }
            },
            "columns": ["close", "change", "Recommend.All|1", "Recommend.All|5", "Recommend.All|15", "Recommend.All|30", "Recommend.All|60", "Recommend.All|240", "Recommend.All"]
        }
        req_tv = urllib.request.Request(
            url_tv, 
            data=json.dumps(payload_tv).encode("utf-8"), 
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req_tv, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("data"):
                for item in data["data"]:
                    ticker = item["s"]
                    close_price = float(item["d"][0])
                    change = float(item["d"][1]) if len(item["d"]) > 1 else 0.0
                    
                    target_assets = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "USOIL"]
                    for ta in target_assets:
                        if ta in ticker:
                            prices[ta] = close_price
                            prices[ta+"_CHANGE"] = change
                            if len(item["d"]) > 8:
                                prices[ta+"_MTF"] = {
                                    "M1": float(item["d"][2]),
                                    "M5": float(item["d"][3]),
                                    "M15": float(item["d"][4]),
                                    "M30": float(item["d"][5]),
                                    "H1": float(item["d"][6]),
                                    "H4": float(item["d"][7]),
                                    "D1": float(item["d"][8])
                                }
                    if "DXY" in ticker: prices["DXY"] = close_price
                    elif "US10Y" in ticker: prices["US10Y"] = close_price
                
                # Calculate Gold/Silver Ratio (GSR)
                if prices["XAUUSD"] > 0 and prices["XAGUSD"] > 0:
                    prices["GSR"] = prices["XAUUSD"] / prices["XAGUSD"]

                print(f"Fetched live multi-asset prices from TradingView: {prices}")
                if prices["XAUUSD"] > 0:
                    return prices
    except Exception as e:
        print(f"Failed to fetch batch prices from TradingView: {e}")

    # 2. Fallback: Ambil secara terpisah menggunakan Yahoo Finance
    try:
        # Fallback XAUUSD via PAXG-USD
        if prices["XAUUSD"] == 0.0:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/PAXG-USD?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
                prices["XAUUSD"] = float(data['chart']['result'][0]['meta']['regularMarketPrice'])
                prev_close = float(data['chart']['result'][0]['meta']['chartPreviousClose'])
                prices["XAUUSD_CHANGE"] = prices["XAUUSD"] - prev_close

        # Fallback DXY via DX-Y.NYB
        if prices["DXY"] == 0.0:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
                prices["DXY"] = float(data['chart']['result'][0]['meta']['regularMarketPrice'])

        # Fallback US10Y via ^TNX
        if prices["US10Y"] == 0.0:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/^TNX?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
                prices["US10Y"] = float(data['chart']['result'][0]['meta']['regularMarketPrice'])
                
        print(f"Fetched live multi-asset prices using Yahoo fallbacks: {prices}")
    except Exception as e:
        print(f"Failed to fetch Yahoo fallback prices: {e}")

    return prices


def clean_json_string(raw_str):
    raw_str = raw_str.strip()
    # Remove markdown code fences if present
    if raw_str.startswith("```"):
        lines = raw_str.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw_str = "\n".join(lines).strip()
    return raw_str
