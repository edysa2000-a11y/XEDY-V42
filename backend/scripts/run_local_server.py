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

# Cached prices updated in background
PRICE_CACHE = {
    "XAUUSD": {"price": 4136.18, "changePct": 0.51, "changeAbs": 21.19, "high": 4138.11, "low": 4113.49, "rec": -0.37},
    "USDJPY": {"price": 157.314, "changePct": -0.04, "changeAbs": -0.064, "high": 157.584, "low": 157.232, "rec": -0.11},
    "timestamp": time.strftime("%H:%M:%S WIB")
}

def fetch_external_prices():
    global PRICE_CACHE
    while True:
        try:
            # 1. Fetch USDJPY
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

            # 2. Fetch XAUUSD
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

            PRICE_CACHE = {
                "USDJPY": {
                    "price": d_jpy[0],
                    "changePct": d_jpy[1],
                    "changeAbs": d_jpy[2],
                    "high": d_jpy[3],
                    "low": d_jpy[4],
                    "rec": d_jpy[5]
                },
                "XAUUSD": {
                    "price": d_xau[0],
                    "changePct": d_xau[1],
                    "changeAbs": d_xau[2],
                    "high": d_xau[3],
                    "low": d_xau[4],
                    "rec": d_xau[5]
                },
                "timestamp": time.strftime("%H:%M:%S WIB")
            }
        except Exception as e:
            pass
        time.sleep(5)  # Update cache every 5 seconds

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
        # Format clean log to console (skip polling spam for /api/prices)
        if '/api/prices' not in str(args):
            sys.stdout.write(f"[{time.strftime('%H:%M:%S')}] {args[0]} {args[1]} -> {args[2]}\n")
            sys.stdout.flush()

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

    # Start price background poller
    threading.Thread(target=fetch_external_prices, daemon=True).start()

    port = 8000  # Default port
    # Check if port is in use
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            port = find_available_port(8001)

    lan_ip = get_lan_ip()

    handler = partial(CORSStaticServer, directory=frontend_dir)
    server = http.server.ThreadingHTTPServer(('0.0.0.0', port), handler)

    print("=" * 65)
    print("  XEDY V42 - SERVER LOKAL RESMI AKTIF & LIVE UPDATE")
    print("=" * 65)
    print(f"\n  [LAPTOP / PC INI]")
    print(f"  -> Info Tajam & S/R Radar : http://localhost:{port}/sr.html")
    print(f"  -> Dashboard Lengkap     : http://localhost:{port}/")
    print(f"\n  [HP / TABLET (Wi-Fi sama)]")
    print(f"  -> Info Tajam & S/R Radar : http://{lan_ip}:{port}/sr.html")
    print(f"  -> Dashboard Lengkap     : http://{lan_ip}:{port}/")
    print("\n" + "=" * 65)
    print("  Status: READY • Auto-fetch harga aktif setiap 5 detik.")
    print("=" * 65 + "\n")
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server lokal dimatikan.")
        server.server_close()

if __name__ == "__main__":
    main()
