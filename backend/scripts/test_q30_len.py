import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.scripts.test_ff_integration import format_upcoming_news_for_q30

for s in ["XAUUSD", "USDJPY", "EURUSD", "GBPUSD", "OIL"]:
    events = format_upcoming_news_for_q30(s)
    q30_text = (
        f"<b>30. Apa yang sedang diantisipasi market?</b>\n"
        f"Katalis rilis data terdekat (Live Forex Factory Calendar):\n{events}\n"
        f"Sikap pasar: Repricing ekspektasi yield & kehati-hatian likuiditas tunai jelang rilis."
    )
    print(f"\n[{s}] Length of Q30: {len(q30_text)} chars")
    print(q30_text)
