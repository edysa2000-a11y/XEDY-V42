import sys
import MetaTrader5 as mt5

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

if mt5.initialize():
    terminal = mt5.terminal_info()
    account = mt5.account_info()
    symbol = mt5.symbol_info('XAUUSD')
    
    print("="*60)
    print("         STATUS MT5 BRIDGE & TERMINAL LOKAL         ")
    print("="*60)
    print("• Status Bridge         : AKTIF 🟢 (Terhubung)")
    print("• Terminal Connected    :", terminal.connected if terminal else False)
    print("• Terminal Build        :", terminal.build if terminal else 'N/A')
    print("• Trade Allowed         :", terminal.trade_allowed if terminal else False)
    print("• Trade DLLs Allowed    :", terminal.dlls_allowed if terminal else False)
    print("• Trade Expert Allowed  :", terminal.tradeapi_disabled == False if terminal else 'N/A')
    
    if account:
        print("\n--- INFORMASI AKUN TRADING ---")
        print("• Login ID / Akun       :", account.login)
        print("• Broker / Server       :", account.server)
        print("• Nama Akun             :", account.name)
        print("• Saldo (Balance)       :", f"${account.balance:,.2f} USD")
        print("• Ekuitas (Equity)      :", f"${account.equity:,.2f} USD")
        print("• Margin Bebas          :", f"${account.margin_free:,.2f} USD")
        print("• Leverage              :", f"1:{account.leverage}")
        print("• Mode Akun             :", "DEMO" if account.trade_mode == 0 else ("CONTEST" if account.trade_mode == 1 else "REAL 🟢"))
    
    if symbol:
        tick = mt5.symbol_info_tick('XAUUSD')
        print("\n--- STATUS LIVE MARKET (XAUUSD) ---")
        print("• Simbol                :", symbol.name)
        print("• Harga Bid             :", tick.bid if tick else 'N/A')
        print("• Harga Ask             :", tick.ask if tick else 'N/A')
        print("• Spread Live           :", symbol.spread, "points")
        print("• Digits Presisi        :", symbol.digits)
        print("• Trade Mode            :", "FULL ACCESS" if symbol.trade_mode == 4 else symbol.trade_mode)
        
    positions = mt5.positions_get()
    print("\n--- STATUS POSISI TERBUKA (OPEN POSITIONS) ---")
    if positions:
        print(f"Total Posisi Aktif      : {len(positions)}")
        for p in positions:
            p_type = "BUY" if p.type == 0 else "SELL"
            print(f"• Ticket #{p.ticket} | {p.symbol} | {p_type} {p.volume} lot @ {p.price_open} | SL: {p.sl} | TP: {p.tp} | Floating: ${p.profit:+,.2f} USD")
    else:
        print("Tidak ada posisi terbuka saat ini (Akun bersih).")
        
    print("="*60)
    mt5.shutdown()
else:
    err = mt5.last_error()
    print("❌ MT5 initialize gagal! Error:", err)
