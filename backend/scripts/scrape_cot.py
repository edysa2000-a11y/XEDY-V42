import yfinance as yf
import json
import os
from datetime import datetime, timezone

def fetch_cot_data():
    output = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "GLD_NET_FLOW": {"price": 0, "change": 0, "change_pct": 0, "status": "Neutral"},
        "COMEX_NET_LONG": {"price": 0, "change": 0, "change_pct": 0, "status": "Neutral"}
    }
    
    try:
        # Fetch GLD ETF data (Proxy for ETF Flows)
        gld = yf.download("GLD", period="5d", progress=False)
        if not gld.empty and 'Volume' in gld:
            # yfinance returns multi-index columns sometimes, handle it safely
            try:
                closes = gld['Close']['GLD']
                vols = gld['Volume']['GLD']
            except:
                closes = gld['Close']
                vols = gld['Volume']
                
            vol_curr = float(vols.dropna().iloc[-1])
            vol_prev = float(vols.dropna().iloc[-2])
            close_curr = float(closes.dropna().iloc[-1])
            close_prev = float(closes.dropna().iloc[-2])
            
            flow_change = vol_curr - vol_prev
            pct = (flow_change / vol_prev * 100) if vol_prev > 0 else 0
            
            status = "Bullish" if (vol_curr > vol_prev and close_curr > close_prev) else "Bearish" if (vol_curr > vol_prev and close_curr < close_prev) else "Neutral"
            
            output["GLD_NET_FLOW"] = {
                "price": round(vol_curr / 1000000, 2), # in millions
                "change": round(flow_change / 1000000, 2),
                "change_pct": round(pct, 2),
                "status": status
            }
            
        # Fetch COMEX Gold futures volume (Proxy for COT Open Interest)
        comex = yf.download("GC=F", period="5d", progress=False)
        if not comex.empty and 'Volume' in comex:
            try:
                closes = comex['Close']['GC=F']
                vols = comex['Volume']['GC=F']
            except:
                closes = comex['Close']
                vols = comex['Volume']
                
            vol_curr = float(vols.dropna().iloc[-1])
            vol_prev = float(vols.dropna().iloc[-2])
            close_curr = float(closes.dropna().iloc[-1])
            close_prev = float(closes.dropna().iloc[-2])
            
            flow_change = vol_curr - vol_prev
            pct = (flow_change / vol_prev * 100) if vol_prev > 0 else 0
            
            status = "Bullish" if close_curr > close_prev else "Bearish"
            
            output["COMEX_NET_LONG"] = {
                "price": int(vol_curr),
                "change": int(flow_change),
                "change_pct": round(pct, 2),
                "status": status
            }
            
    except Exception as e:
        print(f"Error fetching COT data: {e}")
        
    os.makedirs("data", exist_ok=True)
    with open("data/cot_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print("COT Data successfully generated.")

if __name__ == "__main__":
    fetch_cot_data()
