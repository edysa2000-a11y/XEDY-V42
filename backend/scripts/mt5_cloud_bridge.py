import time
import json
import urllib.request
import os
import subprocess
from datetime import datetime
import MetaTrader5 as mt5
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

GITHUB_RAW_URL = "https://raw.githubusercontent.com/edysa2000-a11y/XEDY-V42/main/data/news_feed.json"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")

# MT5 Config
MT5_SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD")
MT5_LOT_SIZE = float(os.getenv("MT5_LOT_SIZE", "0.01"))
POLL_INTERVAL_SECONDS = 30
ACTIVE_TICKETS = set()

def send_telegram_msg(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ADMIN_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_ADMIN_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode("utf-8"), 
            headers={"Content-Type": "application/json"}, 
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")

def fetch_cloud_json():
    try:
        # Fetch metadata safely from the remote (does not alter working directory)
        subprocess.run(["git", "fetch", "origin", "data-feed"], check=True, capture_output=True)
        # Read the file directly from the remote-tracking branch
        result = subprocess.run(
            ["git", "show", "origin/data-feed:data/news_feed.json"],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Git operation failed: {e.stderr}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch JSON via git: {e}")
    return None

def save_trade_history(ticket, pnl, exit_price):
    history_file = "data/real_trades_history.json"
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    
    data = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                data = json.load(f)
        except Exception:
            data = []
            
    data.append({
        "ticket": ticket,
        "close_time": datetime.now().isoformat(),
        "pnl": pnl,
        "exit_price": exit_price
    })
    
    with open(history_file, "w") as f:
        json.dump(data, f, indent=4)
        
    # Push to GitHub for Self-Learning Loop
    try:
        subprocess.run(["git", "add", history_file], check=True, capture_output=True)
        # We commit it locally to main branch so it gets picked up.
        subprocess.run(["git", "commit", "-m", f"auto: log real trade {ticket} PnL {pnl}"], check=True, capture_output=True)
        print("✅ Trade history saved locally and committed to Git for Self-Learning!")
    except Exception as e:
        print(f"⚠️ Failed to commit history to Git: {e}. Saved locally only.")

def monitor_closed_positions():
    global ACTIVE_TICKETS
    if not ACTIVE_TICKETS:
        return
        
    positions = mt5.positions_get()
    current_tickets = set()
    if positions:
        current_tickets = {p.ticket for p in positions}
        
    closed_tickets = ACTIVE_TICKETS - current_tickets
    
    for ticket in list(closed_tickets):
        # Trade has been closed! Retrieve history to get Profit/Loss
        deals = mt5.history_deals_get(position=ticket)
        if deals:
            profit = sum(d.profit for d in deals)
            commission = sum(d.commission for d in deals)
            swap = sum(d.swap for d in deals)
            total_net = profit + commission + swap
            
            # Find the exit deal to get the closing price
            exit_deals = [d for d in deals if d.entry == 1]
            exit_price = exit_deals[0].price if exit_deals else 0
            
            status_icon = "🟢 PROFIT" if total_net > 0 else "🔴 LOSS"
            msg = (
                f"🔔 <b>XEDY LIVE TRADE CLOSED</b>\n\n"
                f"Status: <b>{status_icon}</b>\n"
                f"Ticket: {ticket}\n"
                f"Exit Price: {exit_price}\n"
                f"Net PnL: <b>${total_net:.2f}</b>\n"
                f"Terminal: MT5 Lokal"
            )
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Trade {ticket} closed. PnL: ${total_net:.2f}")
            send_telegram_msg(msg)
            
            # Save to local file for AI self-learning
            save_trade_history(ticket, total_net, exit_price)
            
        ACTIVE_TICKETS.remove(ticket)

def execute_mt5_order(symbol, bias, analysis_data):
    global ACTIVE_TICKETS
    if not mt5.initialize():
        msg = f"❌ [MT5 Bridge] Gagal inisialisasi MT5! Error code: {mt5.last_error()}"
        print(msg)
        send_telegram_msg(msg)
        return False
        
    # Ensure symbol is visible in market watch
    if not mt5.symbol_select(symbol, True):
        msg = f"❌ [MT5 Bridge] Simbol {symbol} tidak ditemukan di Market Watch!"
        print(msg)
        send_telegram_msg(msg)
        return False

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"❌ [MT5 Bridge] Gagal mendapatkan harga tick untuk {symbol}.")
        return False
        
    # Determine filling mode safely
    filling_mode = mt5.ORDER_FILLING_FOK
    info = mt5.symbol_info(symbol)
    if info is not None:
        if info.filling_mode == 1:
            filling_mode = mt5.ORDER_FILLING_FOK
        elif info.filling_mode == 2:
            filling_mode = mt5.ORDER_FILLING_IOC
        elif info.filling_mode == 3:
            filling_mode = mt5.ORDER_FILLING_IOC
        else:
            filling_mode = mt5.ORDER_FILLING_RETURN

    order_type = mt5.ORDER_TYPE_BUY if bias == "BUY_ONLY" else mt5.ORDER_TYPE_SELL
    price = tick.ask if bias == "BUY_ONLY" else tick.bid
    
    # Get SL and TP from Qwen's analysis, fallback to 10/20 points if missing
    fallback_sl = price - 10 if bias == "BUY_ONLY" else price + 10
    fallback_tp = price + 20 if bias == "BUY_ONLY" else price - 20
    
    sl_price = float(analysis_data.get("sl_price", fallback_sl))
    tp_price = float(analysis_data.get("tp1_price", fallback_tp))
    
    # Send order request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": MT5_LOT_SIZE,
        "type": order_type,
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 20,
        "magic": 999111,
        "comment": "XEDY Cloud Bridge",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    print(f"Mengirim order ke MT5: {bias} {MT5_LOT_SIZE} {symbol} @ {price} (SL: {sl_price}, TP: {tp_price})")
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        msg = f"❌ [MT5 Bridge] OP {bias} GAGAL! Retcode: {result.retcode}\nComment: {result.comment}"
        print(msg)
        send_telegram_msg(msg)
        return False
    else:
        msg = (
            f"⚡ <b>XEDY MT5 BRIDGE - OP BERHASIL!</b>\n\n"
            f"Simbol: <code>{symbol}</code>\n"
            f"Aksi: <b>{bias.replace('_ONLY', '')}</b>\n"
            f"Lot: {MT5_LOT_SIZE}\n"
            f"Entry: {price}\n"
            f"SL: {sl_price}\n"
            f"TP: {tp_price}\n"
            f"Ticket: {result.order}\n"
            f"Terminal: MT5 Lokal Terhubung 🟢"
        )
        print(f"OP Berhasil! Ticket: {result.order}")
        ACTIVE_TICKETS.add(result.order)
        send_telegram_msg(msg)
        return True

def main():
    global ACTIVE_TICKETS
    print("="*50)
    print("🚀 XEDY MT5 CLOUD BRIDGE 🚀")
    print("="*50)
    print(f"Symbol     : {MT5_SYMBOL}")
    print(f"Lot Size   : {MT5_LOT_SIZE}")
    print(f"Source URL : {GITHUB_RAW_URL}")
    print("="*50)
    
    if not mt5.initialize():
        print(f"❌ Peringatan: MetaTrader 5 tidak terdeteksi atau belum login. Error: {mt5.last_error()}")
        print("Harap buka terminal MT5 terlebih dahulu!")
    else:
        print(f"✅ MetaTrader 5 terhubung! Terminal: {mt5.terminal_info().name}")
        # Pre-seed active tickets so we track anything already open by the bot
        positions = mt5.positions_get()
        if positions:
            for p in positions:
                if p.magic == 999111: # Only track our bot's trades
                    ACTIVE_TICKETS.add(p.ticket)
            if ACTIVE_TICKETS:
                print(f"🔍 Ditemukan {len(ACTIVE_TICKETS)} posisi aktif milik bot. Mulai memantau...")
        
    last_seen_timestamp = None
    
    print("Melakukan sinkronisasi state awal...")
    initial_data = fetch_cloud_json()
    if initial_data:
        last_seen_timestamp = initial_data.get("generated_at")
        print(f"Sinkronisasi berhasil. Last Signal Time: {last_seen_timestamp}")
    else:
        print("Gagal mengambil state awal. Akan dicoba lagi pada putaran berikutnya.")
        
    print("\nMenunggu sinyal trading baru dari Cloud AI Qwen...\n")
    
    # We use a tighter loop for monitoring positions (every 2 seconds)
    # But only poll GitHub every POLL_INTERVAL_SECONDS (30 seconds)
    loops_since_poll = 0
    poll_loop_threshold = int(POLL_INTERVAL_SECONDS / 2)
    
    while True:
        try:
            # 1. Monitor active trades
            monitor_closed_positions()
            
            # 2. Check for new signals
            if loops_since_poll >= poll_loop_threshold:
                loops_since_poll = 0
                data = fetch_cloud_json()
                if data:
                    current_timestamp = data.get("generated_at")
                    
                    if current_timestamp and current_timestamp != last_seen_timestamp:
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚨 SINYAL BARU TERDETEKSI DARI CLOUD!")
                        last_seen_timestamp = current_timestamp
                        
                        analysis = data.get("macro_analysis", {})
                        bias = analysis.get("bias", "")
                        
                        if bias in ["BUY_ONLY", "SELL_ONLY"]:
                            execute_mt5_order(MT5_SYMBOL, bias, analysis)
                        else:
                            print(f"Sinyal adalah {bias}. Mengabaikan (Tidak OP).")
            
            time.sleep(2)
            loops_since_poll += 1
            
        except KeyboardInterrupt:
            print("\nMenghentikan MT5 Bridge...")
            mt5.shutdown()
            break
        except Exception as e:
            print(f"Unexpected error in polling loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
