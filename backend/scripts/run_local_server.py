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

# Cached prices updated in background
PRICE_CACHE = {
    "source": "INITIALIZING",
    "mt5_bridge": {
        "connected": False,
        "broker": "-",
        "server": "-",
        "login": "-",
        "name": "-",
        "balance": 0.0,
        "equity": 0.0,
        "ping": 0,
        "xau_spread": 0.0,
        "jpy_spread": 0.0
    },
    "XAUUSD": {"price": 4138.30, "changePct": 0.54, "changeAbs": 22.18, "high": 4140.00, "low": 4113.48, "rec": -0.37},
    "USDJPY": {"price": 157.384, "changePct": -0.03, "changeAbs": -0.044, "high": 157.584, "low": 157.232, "rec": -0.11},
    "timestamp": time.strftime("%H:%M:%S WIB")
}

def poll_prices_and_mt5():
    global PRICE_CACHE
    mt5_initialized = False

    while True:
        mt5_success = False

        # 1. Try MT5 Direct Feed if library is available
        if MT5_AVAILABLE:
            try:
                if not mt5_initialized:
                    mt5_initialized = mt5.initialize()

                if mt5_initialized:
                    term = mt5.terminal_info()
                    acc = mt5.account_info()

                    if term and term.connected and acc:
                        tick_xau = mt5.symbol_info_tick('XAUUSD')
                        tick_jpy = mt5.symbol_info_tick('USDJPY')

                        if tick_xau and tick_jpy and tick_xau.bid > 0 and tick_jpy.bid > 0:
                            mt5_success = True
                            xau_spread = round(tick_xau.ask - tick_xau.bid, 2)
                            jpy_spread = round((tick_jpy.ask - tick_jpy.bid) * 100, 1)

                            # Calculate intraday change if high/low exist
                            xau_high = max(PRICE_CACHE["XAUUSD"]["high"], tick_xau.bid)
                            xau_low = min(PRICE_CACHE["XAUUSD"]["low"], tick_xau.bid) if PRICE_CACHE["XAUUSD"]["low"] > 0 else tick_xau.bid

                            jpy_high = max(PRICE_CACHE["USDJPY"]["high"], tick_jpy.bid)
                            jpy_low = min(PRICE_CACHE["USDJPY"]["low"], tick_jpy.bid) if PRICE_CACHE["USDJPY"]["low"] > 0 else tick_jpy.bid

                            PRICE_CACHE["source"] = "MT5_BRIDGE"
                            PRICE_CACHE["mt5_bridge"] = {
                                "connected": True,
                                "broker": term.name,
                                "server": acc.server,
                                "login": acc.login,
                                "name": acc.name,
                                "balance": round(acc.balance, 2),
                                "equity": round(acc.equity, 2),
                                "ping": round(term.ping_last / 1000.0, 1),
                                "xau_bid": tick_xau.bid,
                                "xau_ask": tick_xau.ask,
                                "xau_spread": xau_spread,
                                "jpy_bid": tick_jpy.bid,
                                "jpy_ask": tick_jpy.ask,
                                "jpy_spread": jpy_spread
                            }

                            PRICE_CACHE["XAUUSD"] = {
                                "price": tick_xau.bid,
                                "ask": tick_xau.ask,
                                "spread": xau_spread,
                                "changePct": PRICE_CACHE["XAUUSD"].get("changePct", 0.54),
                                "changeAbs": PRICE_CACHE["XAUUSD"].get("changeAbs", 22.18),
                                "high": xau_high,
                                "low": xau_low,
                                "rec": -0.25
                            }

                            PRICE_CACHE["USDJPY"] = {
                                "price": tick_jpy.bid,
                                "ask": tick_jpy.ask,
                                "spread": jpy_spread,
                                "changePct": PRICE_CACHE["USDJPY"].get("changePct", -0.03),
                                "changeAbs": PRICE_CACHE["USDJPY"].get("changeAbs", -0.044),
                                "high": jpy_high,
                                "low": jpy_low,
                                "rec": -0.15
                            }
                            PRICE_CACHE["timestamp"] = time.strftime("%H:%M:%S WIB")
            except Exception as e:
                mt5_initialized = False

        # 2. Fallback to TradingView Scanner if MT5 is closed or not available
        if not mt5_success:
            try:
                # JPY
                req_jpy = urllib.request.Request(
                    'https://scanner.tradingview.com/forex/scan',
                    data=json.dumps({
                        'symbols': {'tickers': ['OANDA:USDJPY']},
                        'columns': ['close', 'change', 'change_abs', 'high', 'low', 'Recommend.All']
                    }).encode(),
                    headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
                )
                res_jpy = urllib.request.urlopen(req_jpy, timeout=4)
                d_jpy = json.loads(res_jpy.read())['data'][0]['d']

                # XAU
                req_xau = urllib.request.Request(
                    'https://scanner.tradingview.com/cfd/scan',
                    data=json.dumps({
                        'symbols': {'tickers': ['OANDA:XAUUSD']},
                        'columns': ['close', 'change', 'change_abs', 'high', 'low', 'Recommend.All']
                    }).encode(),
                    headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
                )
                res_xau = urllib.request.urlopen(req_xau, timeout=4)
                d_xau = json.loads(res_xau.read())['data'][0]['d']

                PRICE_CACHE["source"] = "TRADINGVIEW_SCANNER"
                PRICE_CACHE["mt5_bridge"]["connected"] = False
                PRICE_CACHE["USDJPY"] = {
                    "price": d_jpy[0],
                    "changePct": d_jpy[1],
                    "changeAbs": d_jpy[2],
                    "high": d_jpy[3],
                    "low": d_jpy[4],
                    "rec": d_jpy[5]
                }
                PRICE_CACHE["XAUUSD"] = {
                    "price": d_xau[0],
                    "changePct": d_xau[1],
                    "changeAbs": d_xau[2],
                    "high": d_xau[3],
                    "low": d_xau[4],
                    "rec": d_xau[5]
                }
                PRICE_CACHE["timestamp"] = time.strftime("%H:%M:%S WIB")
            except Exception:
                pass

        time.sleep(1.5 if mt5_success else 4.0)  # Ultra-fast 1.5s refresh for MT5 ticks!

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

    # Start price background poller (MT5 + TradingView)
    threading.Thread(target=poll_prices_and_mt5, daemon=True).start()

    port = 8000
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            port = find_available_port(8001)

    lan_ip = get_lan_ip()

    handler = partial(CORSStaticServer, directory=frontend_dir)
    server = http.server.ThreadingHTTPServer(('0.0.0.0', port), handler)

    print("=" * 65)
    print("  XEDY V42 - SERVER LOKAL & MT5 CLOUD BRIDGE AKTIF")
    print("=" * 65)
    print(f"\n  [AKSES LAPTOP]")
    print(f"  -> Info Tajam & S/R Radar : http://localhost:{port}/sr.html")
    print(f"  -> Dashboard Lengkap     : http://localhost:{port}/")
    print(f"\n  [AKSES HP / TABLET (Wi-Fi sama)]")
    print(f"  -> Info Tajam & S/R Radar : http://{lan_ip}:{port}/sr.html")
    print(f"  -> Dashboard Lengkap     : http://{lan_ip}:{port}/")
    print("\n" + "=" * 65)
    print("  MT5 Bridge Engine: AKTIF (Finex Bisnis Solusi / MetaQuotes)")
    print("  Tekan Ctrl+C untuk mematikan server.")
    print("=" * 65 + "\n")
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server lokal dimatikan.")
        server.server_close()

if __name__ == "__main__":
    main()
