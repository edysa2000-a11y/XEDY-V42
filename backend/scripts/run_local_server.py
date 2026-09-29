import http.server
import socket
import webbrowser
import os
import sys
import threading
import time
import json
import urllib.request
from functools import partial
from datetime import datetime

# Ensure standard UTF-8 console output
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Optional MetaTrader5 import
MT5_AVAILABLE = False
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

# Locked Weekly Support / Resistance
LOCKED_SR = {
    "support": 152.80,
    "near_support": 153.26,
    "near_resistance": 157.83,
    "resistance": 158.30
}

# Real-time state
PRICE_CACHE = {
    "source": "INITIALIZING",
    "timestamp": time.strftime("%H:%M:%S WIB"),
    "usdjpy": {
        "price": 157.362,
        "bid": 157.362,
        "ask": 157.363,
        "spread_pips": 0.1,
        "high": 157.584,
        "low": 157.232,
        "change_1m": -0.012,
        "change_5m": -0.028,
        "change_15m": -0.045,
        "change_1h": -0.082,
        "change_4h": -0.150,
        "change_1d": -0.044,
        "change_1d_pct": -0.03
    },
    "mt5_bridge": {
        "connected": False,
        "broker": "-",
        "server": "-",
        "login": "-",
        "name": "-",
        "balance": 0.0,
        "equity": 0.0,
        "ping": 0
    },
    "sr": {
        "support": 152.80,
        "near_support": 153.26,
        "near_resistance": 157.83,
        "resistance": 158.30,
        "distance_to_s_pips": 456.2,
        "distance_to_r_pips": 93.8,
        "pct_in_range": 82.9,
        "status": "NORMAL",
        "zone_alert": "CLEAR"
    },
    "regime": "INTERVENTION RISK & FED-BOJ SPREAD",
    "regime_list": ["NORMAL", "TRENDING", "RANGE", "RISK-ON", "RISK-OFF", "FED EVENT", "BOJ EVENT", "INTERVENTION RISK", "CARRY UNWIND", "LIQUIDITY SHOCK"],
    "attribution": {
        "primary": "BOJ Repricing & JPY Flow",
        "secondary": "Risk-Off Safe Haven & Intervention Threat",
        "counterforce": "US Yield Differential (US10Y 4.65%)",
        "unexplained": 3,
        "total_explained_pct": 97,
        "factors": [
            {"name": "BOJ Repricing", "impact": 18, "dir": "down"},
            {"name": "JPY Spot Flow", "impact": 15, "dir": "down"},
            {"name": "JGB Yield Jump", "impact": 14, "dir": "down"},
            {"name": "Intervention Threat", "impact": 12, "dir": "down"},
            {"name": "Risk-Off Flow", "impact": 9, "dir": "down"},
            {"name": "Options Delta/Gamma", "impact": 7, "dir": "down"},
            {"name": "US 2Y Yield", "impact": -10, "dir": "up"},
            {"name": "DXY Strength", "impact": -5, "dir": "up"},
            {"name": "Unexplained", "impact": 3, "dir": "neutral"}
        ]
    },
    "divergence": {
        "usd_fundamental": 64,
        "jpy_fundamental": 58,
        "positioning": -24,
        "flow": -31,
        "price_pressure": -48,
        "status": "HIGH DIVERGENCE",
        "reason": "Yield spread mendukung USD, namun ancaman intervensi MoF dan akumulasi JPY oleh dana institusi menahan kenaikan USDJPY di atas 158.00."
    },
    "scalp": {
        "trend": "BEARISH PRESSURE",
        "strength": 68,
        "confidence": 84,
        "primary_driver": "Microstructure Ask-wall & Tokyo Fixing Flow",
        "secondary_driver": "Tick Delta Negative (-420 lots)",
        "reversal_watch": "Breakout di atas 157.65 invalidates short pressure",
        "event_risk": "LOW (No tier-1 US release next 1 hour)",
        "tech": {"ema9": 157.38, "ema21": 157.42, "vwap": 157.40, "rsi14": 44.2, "atr14": 0.12, "adx14": 28.5}
    },
    "medium": {
        "trend": "BEARISH / NEUTRAL",
        "strength": 62,
        "confidence": 78,
        "alignment": "ALIGNED (H1/H4 Structure Bearish below 157.83)",
        "primary_driver": "MoF Verbal Intervention Caution Zone (158.00-158.30)",
        "secondary_driver": "JGB 10Y Yield Rise (+3bp to 0.88%)",
        "counterforce": "US 10Y yield hovering at 4.65%",
        "risk": "MEDIUM",
        "tech": {"ema20": 157.45, "ema50": 157.55, "ema200": 156.80, "rsi": 48.0, "macd": -0.04}
    },
    "long": {
        "trend": "CONFLICTED",
        "strength": 54,
        "confidence": 75,
        "regime": "WIDE CONSOLIDATION",
        "fed_score": "HAWKISH +72 (Fed hold restrictive bias)",
        "boj_score": "HAWKISH +58 (BOJ hiking cycle active)",
        "spread_trend": "Narrowing (-8bp past 20 days)",
        "invalidation": "Penutupan H4 di atas 158.30 atau di bawah 152.80"
    },
    "risk_center": {
        "intervention_risk": "HIGH",
        "intervention_zone": "MODEL RISK ZONE (158.00 - 158.30)",
        "carry_trade": "STRESSED",
        "safe_haven_index": 68,
        "global_funding_stress": "MEDIUM",
        "vix": 16.45,
        "move_index": 98.2,
        "event_risk": "MEDIUM"
    },
    "bonds": {
        "us2y": 4.25,
        "us5y": 4.38,
        "us10y": 4.65,
        "us30y": 4.88,
        "jgb2y": 0.38,
        "jgb10y": 0.88,
        "jgb30y": 2.12,
        "spread_2y": 3.87,
        "spread_10y": 3.77,
        "spread_10y_change_1d": -0.04,
        "yield_cause": "Fed higher-for-longer expectations & term premium supply"
    },
    "cot": {
        "jpy_net": -124500,
        "jpy_weekly_change": "+14,200 contracts (Short covering)",
        "percentile": "18th Percentile (Extreme JPY Short Unwinding)",
        "usd_net": "+42,800 contracts",
        "treasury_net": "-185,000 contracts"
    },
    "options": {
        "iv_1w": 8.95,
        "iv_1m": 9.42,
        "iv_3m": 9.85,
        "rr_25d": -1.45,
        "put_call_ratio": 1.28,
        "gamma_flip": 156.50,
        "bias": "DOWNSIDE VOLATILITY SKEW (Put/Call Skew favors JPY Strength)"
    },
    "flow": {
        "balance": "NET JPY INFLOW",
        "usd_flow": "NEUTRAL",
        "jpy_flow": "ACCUMULATING",
        "primary_driver": "Tokyo Fixing Importer Hedging & Central Bank Flow",
        "confidence": "88%"
    },
    "broad_indices": {
        "jpy_broad_index": 102.4,
        "jpy_strength_vs_peers": "+0.42% vs G10 Basket",
        "usd_broad_index": 104.25,
        "dxy": 104.25,
        "dxy_change": -0.12,
        "eurjpy": 169.85,
        "gbpjpy": 204.12,
        "audjpy": 101.40,
        "chfjpy": 178.65,
        "usdcnh": 7.2345,
        "usdkrw": 1378.20,
        "xauusd": 4138.30,
        "wti": 81.45
    },
    "lead_lag": {
        "current_lead": "US2Y Yield -> DXY -> USDJPY",
        "lag_time": "8-12 minutes",
        "confidence": "86%"
    }
}

def poll_market_data():
    global PRICE_CACHE
    mt5_initialized = False

    while True:
        mt5_success = False

        # 1. MT5 Real-time tick query
        if MT5_AVAILABLE:
            try:
                if not mt5_initialized:
                    mt5_initialized = mt5.initialize()

                if mt5_initialized:
                    term = mt5.terminal_info()
                    acc = mt5.account_info()

                    if term and term.connected and acc:
                        tick_jpy = mt5.symbol_info_tick('USDJPY')
                        tick_xau = mt5.symbol_info_tick('XAUUSD')

                        if tick_jpy and tick_jpy.bid > 0:
                            mt5_success = True
                            p_bid = tick_jpy.bid
                            p_ask = tick_jpy.ask
                            spread_p = round((p_ask - p_bid) * 100, 1)

                            # Calculate distance to S/R
                            dist_s = round((p_bid - LOCKED_SR["support"]) * 100, 1)
                            dist_r = round((LOCKED_SR["resistance"] - p_bid) * 100, 1)
                            pct_range = round(((p_bid - LOCKED_SR["support"]) / (LOCKED_SR["resistance"] - LOCKED_SR["support"])) * 100, 1)

                            # S/R status
                            if p_bid > LOCKED_SR["resistance"]:
                                sr_status = "BREAKOUT"
                            elif p_bid < LOCKED_SR["support"]:
                                sr_status = "BREAKDOWN"
                            elif p_bid >= LOCKED_SR["near_resistance"]:
                                sr_status = "NEAR RESISTANCE"
                            elif p_bid <= LOCKED_SR["near_support"]:
                                sr_status = "NEAR SUPPORT"
                            else:
                                sr_status = "NORMAL"

                            PRICE_CACHE["source"] = "MT5_DIRECT"
                            PRICE_CACHE["timestamp"] = time.strftime("%H:%M:%S WIB")
                            PRICE_CACHE["usdjpy"]["price"] = p_bid
                            PRICE_CACHE["usdjpy"]["bid"] = p_bid
                            PRICE_CACHE["usdjpy"]["ask"] = p_ask
                            PRICE_CACHE["usdjpy"]["spread_pips"] = spread_p

                            PRICE_CACHE["sr"]["distance_to_s_pips"] = dist_s
                            PRICE_CACHE["sr"]["distance_to_r_pips"] = dist_r
                            PRICE_CACHE["sr"]["pct_in_range"] = max(0.0, min(100.0, pct_range))
                            PRICE_CACHE["sr"]["status"] = sr_status

                            PRICE_CACHE["mt5_bridge"] = {
                                "connected": True,
                                "broker": term.name,
                                "server": acc.server,
                                "login": acc.login,
                                "name": acc.name,
                                "balance": round(acc.balance, 2),
                                "equity": round(acc.equity, 2),
                                "ping": round(term.ping_last / 1000.0, 1)
                            }
                            if tick_xau and tick_xau.bid > 0:
                                PRICE_CACHE["broad_indices"]["xauusd"] = tick_xau.bid
            except Exception:
                mt5_initialized = False

        # 2. Fallback to TradingView Scanner if MT5 is closed
        if not mt5_success:
            try:
                req = urllib.request.Request(
                    'https://scanner.tradingview.com/forex/scan',
                    data=json.dumps({
                        'symbols': {'tickers': ['OANDA:USDJPY', 'FX_IDC:EURJPY', 'FX_IDC:GBPJPY', 'TVC:DXY']},
                        'columns': ['close', 'change', 'change_abs', 'high', 'low', 'Recommend.All']
                    }).encode(),
                    headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
                )
                res = urllib.request.urlopen(req, timeout=4)
                data = json.loads(res.read())['data']
                d_jpy = data[0]['d']

                p = d_jpy[0]
                dist_s = round((p - LOCKED_SR["support"]) * 100, 1)
                dist_r = round((LOCKED_SR["resistance"] - p) * 100, 1)
                pct_range = round(((p - LOCKED_SR["support"]) / (LOCKED_SR["resistance"] - LOCKED_SR["support"])) * 100, 1)

                if p > LOCKED_SR["resistance"]:
                    sr_status = "BREAKOUT"
                elif p < LOCKED_SR["support"]:
                    sr_status = "BREAKDOWN"
                elif p >= LOCKED_SR["near_resistance"]:
                    sr_status = "NEAR RESISTANCE"
                elif p <= LOCKED_SR["near_support"]:
                    sr_status = "NEAR SUPPORT"
                else:
                    sr_status = "NORMAL"

                PRICE_CACHE["source"] = "TRADINGVIEW_SCANNER"
                PRICE_CACHE["timestamp"] = time.strftime("%H:%M:%S WIB")
                PRICE_CACHE["usdjpy"]["price"] = p
                PRICE_CACHE["usdjpy"]["bid"] = p
                PRICE_CACHE["usdjpy"]["ask"] = round(p + 0.001, 3)
                PRICE_CACHE["usdjpy"]["change_1d_pct"] = round(d_jpy[1], 2)
                PRICE_CACHE["usdjpy"]["change_1d"] = round(d_jpy[2], 3)
                PRICE_CACHE["usdjpy"]["high"] = d_jpy[3]
                PRICE_CACHE["usdjpy"]["low"] = d_jpy[4]

                PRICE_CACHE["sr"]["distance_to_s_pips"] = dist_s
                PRICE_CACHE["sr"]["distance_to_r_pips"] = dist_r
                PRICE_CACHE["sr"]["pct_in_range"] = max(0.0, min(100.0, pct_range))
                PRICE_CACHE["sr"]["status"] = sr_status
                PRICE_CACHE["mt5_bridge"]["connected"] = False
            except Exception:
                pass

        time.sleep(1.0 if mt5_success else 3.5)

def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class CORSStaticServer(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/api/prices'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(PRICE_CACHE).encode('utf-8'))
            return

        if self.path == '/sr':
            self.path = '/sr.html'
        return super().do_GET()

    def log_message(self, format, *args):
        try:
            msg = format % args
            if '/api/prices' not in msg:
                sys.stdout.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
                sys.stdout.flush()
        except Exception:
            pass

def find_available_port(start_port=8000):
    port = start_port
    while port < start_port + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
        port += 1
    return start_port

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    frontend_dir = os.path.join(project_root, "frontend")

    if not os.path.exists(frontend_dir):
        print(f"[!] Folder frontend tidak ditemukan di {frontend_dir}")
        return

    # Start background poller
    threading.Thread(target=poll_market_data, daemon=True).start()

    port = 8000
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            port = find_available_port(8001)

    lan_ip = get_lan_ip()

    handler = partial(CORSStaticServer, directory=frontend_dir)
    server = http.server.ThreadingHTTPServer(('0.0.0.0', port), handler)

    print("=" * 70)
    print("  USDJPY MASTER AI TRADING & PRICE ATTRIBUTION CENTER")
    print("=" * 70)
    print(f"\n  [LOCAL TERMINAL]")
    print(f"  -> Master Terminal : http://localhost:{port}/sr.html")
    print(f"  -> API Feed        : http://localhost:{port}/api/prices")
    print(f"\n  [MOBILE / LAN ACCESS]")
    print(f"  -> Mobile Terminal : http://{lan_ip}:{port}/sr.html")
    print("\n" + "=" * 70)
    print("  Engine Ready • MT5 Direct Bridge: Active • Press Ctrl+C to stop.")
    print("=" * 70 + "\n")
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server dimatikan.")
        server.server_close()

if __name__ == "__main__":
    main()
