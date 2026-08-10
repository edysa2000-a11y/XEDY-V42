import MetaTrader5 as mt5
from datetime import datetime, timedelta

if not mt5.initialize():
    print("MT5 init failed")
    quit()

from_date = datetime.now() - timedelta(days=30)
to_date = datetime.now() + timedelta(days=1)
deals = mt5.history_deals_get(from_date, to_date)
if deals:
    losses = [d._asdict() for d in deals if d.entry == 1 and d.profit < 0]
    print(f"Total Losing Deals (last 30 days): {len(losses)}")
    for d in losses:
        dt = datetime.fromtimestamp(d['time']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{dt}] Symbol: {d['symbol']} | Profit: {d['profit']} | Ticket: {d['position_id']}")
else:
    print("No deals found")
mt5.shutdown()
