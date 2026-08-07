import os
import json
import time
import subprocess
import sys

def monitor_and_optimize():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    trades_file = os.path.join(project_root, 'data', 'closed_trades.json')
    log_file = os.path.join(project_root, 'data', 'profit_monitor.log')
    learning_script = os.path.join(project_root, 'backend', 'scripts', 'adaptive_self_learning.py')
    
    def log_msg(msg):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        full_msg = f"[{timestamp}] {msg}"
        print(full_msg)
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(full_msg + '\n')
        except:
            pass

    def active_sleep(seconds, interval=10, msg="Monitoring system health"):
        """Sleeps in chunks and logs a heartbeat message so it doesn't look dead."""
        slept = 0
        while slept < seconds:
            remaining = seconds - slept
            if remaining > 60:
                log_msg(f"⏳ {msg}... ({remaining // 60} min {remaining % 60} sec remaining)")
            else:
                log_msg(f"⏳ {msg}... ({remaining} sec remaining)")
            
            chunk = min(interval, remaining)
            time.sleep(chunk)
            slept += chunk

    log_msg("Profit Monitor Daemon started. Monitoring data/closed_trades.json...")
    
    while True:
        try:
            if os.path.exists(trades_file):
                with open(trades_file, 'r') as f:
                    trades = json.load(f)
                
                # Check recent profit (e.g. last 50 trades or overall)
                total_profit = sum(t.get('profit', 0) for t in trades)
                
                log_msg(f"Total Profit: {total_profit:.2f}")
                
                if total_profit < 0:
                    log_msg("Negative profit detected! Triggering adaptive_self_learning.py for optimization...")
                    # We can also capture output of subprocess if we want, but letting it run is fine.
                    result = subprocess.run([sys.executable, learning_script], cwd=project_root, capture_output=True, text=True)
                    if result.stdout:
                        for line in result.stdout.split('\n'):
                            if line.strip(): log_msg(f"  > {line}")
                    if result.stderr:
                        for line in result.stderr.split('\n'):
                            if line.strip(): log_msg(f"  ! {line}")
                    log_msg("Optimization complete. Sleeping for 10 minutes to let new trades accumulate.")
                    active_sleep(600, msg="Post-optimization cooling down") # 10 minutes

                else:
                    log_msg("Profit is positive. No optimization needed.")
            else:
                log_msg(f"No trade history found at {trades_file}")
                
        except Exception as e:
            log_msg(f"Error in Profit Monitor Daemon: {e}")
            
        # Check every 10 minutes, log a heartbeat every 1 minute
        log_msg("Trade history checked. Entering standby mode.")
        active_sleep(600, msg="Standby & listening for trades")

if __name__ == "__main__":
    monitor_and_optimize()
