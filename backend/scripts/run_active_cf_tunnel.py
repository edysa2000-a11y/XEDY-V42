import subprocess
import re
import time
import os
import sys

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cloudflared_exe = os.path.join(project_root, "cloudflared.exe")

    if not os.path.exists(cloudflared_exe):
        print(f"[!] cloudflared.exe tidak ditemukan di {cloudflared_exe}")
        return

    print("[*] Menghubungkan port 8000 ke Cloudflare Global Tunnel...")
    cf = subprocess.Popen(
        [cloudflared_exe, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    t0 = time.time()
    url = None
    while time.time() - t0 < 30:
        line = cf.stdout.readline()
        if not line:
            continue
        m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if m:
            url = m.group(0)
            break

    if url:
        sr_link = f"{url}/sr.html"
        with open(os.path.join(project_root, "active_tunnel_url.txt"), "w", encoding="utf-8") as f:
            f.write(sr_link)

        print("=" * 65)
        print("  TUNNEL AKTIF! AKSES DARI HP / MANA SAJA:")
        print(f"  -> {sr_link}")
        print("=" * 65)
        sys.stdout.flush()

        try:
            while True:
                line = cf.stdout.readline()
                if not line:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("[!] Tunnel dihentikan.")
            cf.terminate()
    else:
        print("[!] Gagal mendapatkan URL dari Cloudflare.")
        cf.terminate()

if __name__ == "__main__":
    main()
