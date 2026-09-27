import sys
import os

# Ensure root workspace is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import json
import urllib.request
from datetime import datetime, timezone, timedelta

# Ensure UTF-8 output encoding for console logging
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# WIB Timezone (UTC+7)
WIB = timezone(timedelta(hours=7))
now_wib = datetime.now(WIB)

# LOCKED S/R CONFIG (27 Sep - 4 Okt 2026)
CONFIG = {
    "XAUUSD": {
        "support": 4220.0,
        "resistance": 4580.0,
        "near_pct": 0.005, # 0.50%
        "digits": 2
    },
    "USDJPY": {
        "support": 152.80,
        "resistance": 158.30,
        "near_pct": 0.003, # 0.30%
        "digits": 2
    }
}

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")
STATE_FILE = "data/sr_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "current_state": {"XAUUSD": "NORMAL", "USDJPY": "NORMAL"},
        "last_hourly_hour": -1,
        "raw_outside_count": {"XAUUSD": {"BREAKOUT": 0, "BREAKDOWN": 0}, "USDJPY": {"BREAKOUT": 0, "BREAKDOWN": 0}}
    }

def save_state(state):
    os.makedirs("data", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def send_telegram(text):
    if not TOKEN or not ADMIN_ID:
        print("[WARN] Telegram secrets missing. Printing to console:\n" + text)
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_ID, "text": text, "parse_mode": "HTML"}
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
            print("[INFO] Telegram alert sent successfully from GitHub Actions.")
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram: {e}")

def send_telegram_photo(photo_bytes, caption=""):
    if not TOKEN or not ADMIN_ID:
        print("[WARN] Telegram secrets missing. Printing photo caption:\n" + caption)
        return
    import uuid
    boundary = uuid.uuid4().hex
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{ADMIN_ID}\r\n".encode("utf-8"))
    if caption:
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"weekly_sr.png\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8"))
    parts.append(photo_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    
    body = b"".join(parts)
    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
            print("[INFO] Telegram S/R photo card sent successfully from GitHub Actions.")
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram photo: {e}")
        send_telegram(caption)

def fetch_tradingview_prices():
    url = "https://scanner.tradingview.com/global/scan"
    payload = {
        "symbols": {"tickers": ["OANDA:XAUUSD", "OANDA:USDJPY", "FX_IDC:XAUUSD", "FX:USDJPY"]},
        "columns": ["close", "bid", "ask"]
    }
    prices = {}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("data", []):
                ticker = item.get("s", "")
                vals = item.get("d", [])
                if len(vals) >= 3:
                    close, bid, ask = vals[0], vals[1], vals[2]
                    mid = (bid + ask) / 2.0 if (bid and ask and bid > 0 and ask > 0) else close
                    if "XAUUSD" in ticker and "XAUUSD" not in prices:
                        prices["XAUUSD"] = {"close": close, "bid": bid, "ask": ask, "mid": mid}
                    elif "USDJPY" in ticker and "USDJPY" not in prices:
                        prices["USDJPY"] = {"close": close, "bid": bid, "ask": ask, "mid": mid}
    except Exception as e:
        print(f"[ERROR] TV fetch error: {e}")
    return prices

def run():
    print(f"[INFO] Running S/R Monitor Engine on GitHub Actions ({now_wib.strftime('%Y-%m-%d %H:%M:%S WIB')})...")
    state = load_state()
    tv_prices = fetch_tradingview_prices()
    
    current_price_data = {}
    
    for symbol, cfg in CONFIG.items():
        if symbol not in tv_prices:
            print(f"[WARN] No TradingView price for {symbol}")
            continue
            
        pdata = tv_prices[symbol]
        mid = round(float(pdata["mid"]), cfg["digits"])
        supp = cfg["support"]
        res = cfg["resistance"]
        
        dist_s = round(mid - supp, cfg["digits"])
        dist_r = round(res - mid, cfg["digits"])
        
        raw_state = "NORMAL"
        
        if mid > res:
            state["raw_outside_count"][symbol]["BREAKOUT"] += 1
            state["raw_outside_count"][symbol]["BREAKDOWN"] = 0
            if state["raw_outside_count"][symbol]["BREAKOUT"] >= 2:
                raw_state = "BREAKOUT"
            else:
                raw_state = state["current_state"].get(symbol, "NORMAL")
        elif mid < supp:
            state["raw_outside_count"][symbol]["BREAKDOWN"] += 1
            state["raw_outside_count"][symbol]["BREAKOUT"] = 0
            if state["raw_outside_count"][symbol]["BREAKDOWN"] >= 2:
                raw_state = "BREAKDOWN"
            else:
                raw_state = state["current_state"].get(symbol, "NORMAL")
        else:
            state["raw_outside_count"][symbol]["BREAKOUT"] = 0
            state["raw_outside_count"][symbol]["BREAKDOWN"] = 0
            
            near_s_bound = supp + (supp * cfg["near_pct"])
            near_r_bound = res - (res * cfg["near_pct"])
            
            if mid >= near_r_bound:
                raw_state = "NEAR_RESISTANCE"
            elif mid <= near_s_bound:
                raw_state = "NEAR_SUPPORT"
            else:
                raw_state = "NORMAL"
                
        prev_state = state["current_state"].get(symbol, "NORMAL")
        digits = cfg["digits"]
        
        # State Machine Anti-Spam Trigger
        if raw_state != prev_state:
            state["current_state"][symbol] = raw_state
            
            if raw_state == "NEAR_SUPPORT":
                dist = round(mid - supp, digits)
                dist_pct = round((mid - supp) / supp * 100.0, 2)
                msg = (
                    f"🚨 <b>S/R ALERT — NEAR SUPPORT</b>\n\n"
                    f"<b>{symbol}</b>\n"
                    f"Price: {mid:.{digits}f}\n"
                    f"🔒 Support: {supp:.{digits}f}\n"
                    f"Distance: +{dist:.{digits}f}\n"
                    f"Distance: +{dist_pct:.2f}%\n\n"
                    f"⚠️ <b>PRICE NEAR SUPPORT</b>"
                )
                send_telegram(msg)
            elif raw_state == "NEAR_RESISTANCE":
                dist = round(res - mid, digits)
                dist_pct = round((res - mid) / res * 100.0, 2)
                msg = (
                    f"🚨 <b>S/R ALERT — NEAR RESISTANCE</b>\n\n"
                    f"<b>{symbol}</b>\n"
                    f"Price: {mid:.{digits}f}\n"
                    f"🔒 Resistance: {res:.{digits}f}\n"
                    f"Distance: +{dist:.{digits}f}\n"
                    f"Distance: +{dist_pct:.2f}%\n\n"
                    f"⚠️ <b>PRICE NEAR RESISTANCE</b>"
                )
                send_telegram(msg)
            elif raw_state == "BREAKOUT":
                msg = (
                    f"🚨🚨 <b>BREAKOUT ALERT</b>\n\n"
                    f"<b>{symbol}</b>\n"
                    f"Price: {mid:.{digits}f}\n"
                    f"🔒 Resistance: {res:.{digits}f}\n\n"
                    f"<b>BREAKOUT RESISTANCE</b>"
                )
                send_telegram(msg)
            elif raw_state == "BREAKDOWN":
                msg = (
                    f"🚨🚨 <b>BREAKDOWN ALERT</b>\n\n"
                    f"<b>{symbol}</b>\n"
                    f"Price: {mid:.{digits}f}\n"
                    f"🔒 Support: {supp:.{digits}f}\n\n"
                    f"<b>BREAKDOWN SUPPORT</b>"
                )
                send_telegram(msg)

        current_price_data[symbol] = {
            "mid": mid, "dist_s": dist_s, "dist_r": dist_r, "status": state["current_state"][symbol]
        }
        
    # Check Hourly Report Trigger
    if state.get("last_hourly_hour") != now_wib.hour:
        state["last_hourly_hour"] = now_wib.hour
        
        blocks = []
        for symbol, cfg in CONFIG.items():
            digits = cfg["digits"]
            data = current_price_data.get(symbol)
            if data:
                live_p = f"{data['mid']:.{digits}f}"
                ds = f"{data['dist_s']:+.{digits}f}"
                dr = f"{data['dist_r']:+.{digits}f}"
                st = data["status"]
            else:
                live_p, ds, dr, st = "N/A", "N/A", "N/A", "NO DATA"
                
            block = (
                f"<b>{symbol}</b>\n"
                f"• Live: {live_p}\n"
                f"• 🔒 S: {cfg['support']:.{digits}f}\n"
                f"• Distance S: {ds}\n"
                f"• 🔒 R: {cfg['resistance']:.{digits}f}\n"
                f"• Distance R: {dr}\n"
                f"• Status: {st}"
            )
            blocks.append(block)

        report_msg = (
            f"📊 <b>S/R HOURLY REPORT</b>\n\n" +
            "\n\n".join(blocks)
        )
        try:
            from backend.telegram.sr_image_generator import generate_sr_card_bytes
            x_data = current_price_data.get("XAUUSD", {})
            j_data = current_price_data.get("USDJPY", {})
            photo_bytes = generate_sr_card_bytes(
                xau_price=x_data.get("mid", 4285.00),
                xau_support=CONFIG["XAUUSD"]["support"],
                xau_resistance=CONFIG["XAUUSD"]["resistance"],
                xau_status=x_data.get("status", "NORMAL"),
                jpy_price=j_data.get("mid", 157.29),
                jpy_support=CONFIG["USDJPY"]["support"],
                jpy_resistance=CONFIG["USDJPY"]["resistance"],
                jpy_status=j_data.get("status", "NORMAL"),
                now_wib=now_wib
            )
            send_telegram_photo(photo_bytes, report_msg)
        except Exception as e:
            print(f"[WARN] Failed to generate/send card photo: {e}")
            send_telegram(report_msg)
        print("[INFO] Hourly Report triggered from GitHub Actions.")

    save_state(state)
    print("[INFO] S/R Monitor Engine execution complete on GitHub Actions.")

if __name__ == "__main__":
    run()
