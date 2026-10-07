import sys
import os
import time
import asyncio
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception:
    pass

from backend.telegram.sr_monitor import SRMonitorEngine

WIB = timezone(timedelta(hours=7))

def check_local_daemon_active() -> tuple[bool, float]:
    """
    Checks if Local Daemon has sent a heartbeat recently via LOCAL_DAEMON_LAST_SEEN.
    Returns (is_active, age_minutes).
    Threshold: 18 minutes (since scheduled pushes happen every 15 minutes).
    """
    val = os.environ.get("LOCAL_DAEMON_LAST_SEEN", "").strip()
    pat = os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN")
    
    # If not in env, attempt live fetch from GitHub API
    if (not val or val == "0") and pat:
        try:
            import urllib.request, json
            repo = os.environ.get("GITHUB_REPOSITORY", "edysa2000-a11y/XEDY-V42")
            url = f"https://api.github.com/repos/{repo}/actions/variables/LOCAL_DAEMON_LAST_SEEN"
            req = urllib.request.Request(url, headers={"Authorization": f"token {pat}", "User-Agent": "XEDY-Cron"})
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                val = data.get("value", "")
        except Exception:
            pass

    if val:
        try:
            last_ts = float(val)
            age_min = (time.time() - last_ts) / 60.0
            if age_min < 18.0:
                return True, age_min
            return False, age_min
        except Exception:
            pass
    return False, 999.0

async def main():
    print("XEDY GitHub 15-Minute Bloomberg SR Push starting...")
    now_wib = datetime.now(WIB)

    # Failover Gate Check: Local Daemon is First Priority
    force = any(arg in sys.argv for arg in ["--force", "-f", "--all", "--engine", "--flow"])
    is_active, age_m = check_local_daemon_active()

    if is_active and not force:
        print(f"ℹ️ [FAILOVER GATE] Local Daemon is ACTIVE (Heartbeat received {age_m:.1f}m ago).")
        print("ℹ️ Skipping GitHub Actions push to prevent duplicate (Local Daemon is First Priority).")
        print("Finished gracefully.")
        return

    if age_m < 900.0:
        print(f"⚠️ [FAILOVER GATE] Local Daemon is INACTIVE (Last seen: {age_m:.1f}m ago).")
    else:
        print("⚠️ [FAILOVER GATE] Local Daemon heartbeat not detected or timed out.")
    print("🚀 [FAILOVER GATE] FAILOVER ACTIVATED: GitHub Actions taking over scheduled push!")

    engine = SRMonitorEngine()
    print(f"Scanning market symbols at {now_wib.strftime('%Y-%m-%d %H:%M:%S WIB')}...")
    await engine.check_all_symbols(now_wib)
    print("Generating and sending 16:9 Bloomberg dashboard card to Telegram...")
    await engine.send_scheduled_report(now_wib)
    
    # Tolerance window for GitHub Actions cron scheduler delay (+- 7 minutes around :00 and :30)
    m = now_wib.minute
    is_30m_slot = (m in range(0, 8) or m in range(28, 38) or m >= 58)
    force_all = len(sys.argv) > 1 and sys.argv[1] in ["--all"]
    force_flow = len(sys.argv) > 1 and sys.argv[1] in ["--flow", "--all"]
    force_engine = len(sys.argv) > 1 and sys.argv[1] in ["--engine", "--all"]

    if is_30m_slot or force_flow:
        print("Generating and sending 30-Minute Money Flow Radar to Telegram...")
        from backend.telegram.money_flow_engine import MoneyFlowRadarEngine
        flow_engine = MoneyFlowRadarEngine()
        await flow_engine.send_scheduled_radar(now_wib)
        
    if is_30m_slot or force_engine:
        print("Generating and sending 30-Minute XEDY AI Precision Trading Engine to Telegram...")
        from backend.telegram.precision_engine import PrecisionTradingEngine
        prec_engine = PrecisionTradingEngine()
        await prec_engine.send_scheduled_engine(now_wib)
        
    print("Finished successfully!")

if __name__ == "__main__":
    asyncio.run(main())
