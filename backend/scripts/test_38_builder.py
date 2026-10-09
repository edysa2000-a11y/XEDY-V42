import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.telegram.narrative_engine import get_canonical_pair, fetch_live_market_snapshot

def test_all_pairs():
    for sym in ["XAUUSD", "USDJPY", "EURUSD", "GBPUSD", "OIL"]:
        c = get_canonical_pair(sym)
        snap = fetch_live_market_snapshot(c)
        print(f"[{c}] Price: {snap['price']} | High: {snap['high']} | Low: {snap['low']} | Pos: {snap['pos_pct']}% | DXY: {snap['dxy']}")

if __name__ == "__main__":
    test_all_pairs()
