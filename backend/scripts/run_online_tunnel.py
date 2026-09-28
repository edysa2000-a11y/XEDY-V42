import subprocess
import time
import re
import sys
import os

def main():
    print("=" * 60)
    print("  XEDY V42 - ONLINE CLOUD TUNNEL LAUNCHER")
    print("  Membuka akses web Info Tajam agar bisa diakses dari HP / luar")
    print("=" * 60)

    # Path to frontend
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    frontend_dir = os.path.join(project_root, "frontend")
    cloudflared_exe = os.path.join(project_root, "cloudflared.exe")

    if not os.path.exists(cloudflared_exe):
        print(f"[!] cloudflared.exe tidak ditemukan di {cloudflared_exe}")
        return

    port = 8089
    print(f"[*] Menjalankan local server di port {port}...")
    srv = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", frontend_dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("[*] Menghubungkan ke Cloudflare Global Network (HTTPS)...")
    cf = subprocess.Popen(
        [cloudflared_exe, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    tunnel_url = None
    t0 = time.time()
    while time.time() - t0 < 30:
        line = cf.stdout.readline()
        if not line:
            continue
        m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if m:
            tunnel_url = m.group(0)
            break

    if tunnel_url:
        online_link = f"{tunnel_url}/sr.html"
        print("\n" + "=" * 65)
        print("  BERHASIL ONLINE! LINK INI BISA DIAKSES DARI MANA SAJA:")
        print(f"  --> {online_link}")
        print("=" * 65)
        print("\nSilakan salin link di atas dan buka di HP atau komputer mana saja.")
        print("Jangan tutup jendela ini selama ingin mengakses web dari luar.\n")
        
        # Save to file for easy reference
        with open(os.path.join(project_root, "active_online_url.txt"), "w") as f:
            f.write(online_link)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nMematikan tunnel...")
    else:
        print("[!] Gagal mendapatkan URL Cloudflare Tunnel dalam 30 detik.")

    srv.terminate()
    cf.terminate()

if __name__ == "__main__":
    main()
