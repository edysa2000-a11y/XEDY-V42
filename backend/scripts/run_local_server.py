import http.server
import socket
import webbrowser
import os
import sys
import threading
import time
from functools import partial

# Ensure standard UTF-8 console output
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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
        if self.path == '/sr':
            self.path = '/sr.html'
        return super().do_GET()

    def log_message(self, format, *args):
        # Format clean log to console
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

    port = find_available_port(8000)
    lan_ip = get_lan_ip()

    handler = partial(CORSStaticServer, directory=frontend_dir)
    server = http.server.ThreadingHTTPServer(('0.0.0.0', port), handler)

    print("=" * 65)
    print("  XEDY V42 - SERVER LOKAL RESMI AKTIF & BERJALAN")
    print("=" * 65)
    print(f"\n  [LAPTOP / PC INI]")
    print(f"  -> Info Tajam & S/R Radar : http://localhost:{port}/sr.html")
    print(f"  -> Dashboard Lengkap     : http://localhost:{port}/")
    print(f"\n  [HP / TABLET (Wi-Fi sama)]")
    print(f"  -> Info Tajam & S/R Radar : http://{lan_ip}:{port}/sr.html")
    print(f"  -> Dashboard Lengkap     : http://{lan_ip}:{port}/")
    print("\n" + "=" * 65)
    print("  Status: READY • Tekan Ctrl+C untuk mematikan server.")
    print("=" * 65 + "\n")
    sys.stdout.flush()

    # Otomatis buka browser setelah 0.5 detik
    def open_browser():
        time.sleep(0.5)
        webbrowser.open(f"http://localhost:{port}/sr.html")

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server lokal dimatikan.")
        server.server_close()

if __name__ == "__main__":
    main()
