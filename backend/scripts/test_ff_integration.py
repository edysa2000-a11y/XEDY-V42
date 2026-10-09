import urllib.request
import xml.etree.ElementTree as ET
import os, json, time
from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))
EDT = timezone(timedelta(hours=-4))

_LAST_FETCH_ATTEMPT = 0
_CACHED_EVENTS = []

DEFAULT_EVENTS = [
    {"title": "FOMC Meeting Minutes", "country": "USD", "date": "10-07-2026", "time": "6:00pm", "impact": "High", "forecast": "", "previous": ""},
    {"title": "BOE Gov Bailey Speaks", "country": "GBP", "date": "10-08-2026", "time": "12:15pm", "impact": "High", "forecast": "", "previous": ""},
    {"title": "Unemployment Claims", "country": "USD", "date": "10-08-2026", "time": "12:30pm", "impact": "Medium", "forecast": "200K", "previous": "197K"},
    {"title": "Prelim UoM Consumer Sentiment", "country": "USD", "date": "10-09-2026", "time": "2:00pm", "impact": "Medium", "forecast": "47.5", "previous": "47.8"},
    {"title": "BOJ Gov Ueda Speaks", "country": "JPY", "date": "10-06-2026", "time": "6:35am", "impact": "High", "forecast": "", "previous": ""},
    {"title": "OPEC-JMMC Meetings", "country": "All", "date": "10-04-2026", "time": "9:15am", "impact": "Medium", "forecast": "", "previous": ""}
]

def fetch_ff_events_cached() -> list:
    global _LAST_FETCH_ATTEMPT, _CACHED_EVENTS
    now = time.time()
    
    # 1. In-memory check
    if _CACHED_EVENTS and (now - _LAST_FETCH_ATTEMPT < 1800):
        return _CACHED_EVENTS

    # 2. File-cache check
    cache_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ff_calendar_cache.json")
    if os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if now - mtime < 3600:
                with open(cache_file, "r") as f:
                    _CACHED_EVENTS = json.load(f)
                if _CACHED_EVENTS:
                    _LAST_FETCH_ATTEMPT = now
                    return _CACHED_EVENTS
        except Exception:
            pass

    # 3. Rate-limit backoff (do not retry web fetch if last attempt was less than 300s ago)
    if now - _LAST_FETCH_ATTEMPT < 300:
        return _CACHED_EVENTS if _CACHED_EVENTS else DEFAULT_EVENTS

    _LAST_FETCH_ATTEMPT = now

    # 4. Fetch from Forex Factory XML
    try:
        url = 'https://nfs.faireconomy.media/ff_calendar_thisweek.xml'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=5) as r:
            xml_data = r.read()
        root = ET.fromstring(xml_data)
        parsed = []
        for event in root.findall('event'):
            title = (event.findtext('title') or "").strip()
            country = (event.findtext('country') or "").strip()
            date_str = (event.findtext('date') or "").strip()
            time_str = (event.findtext('time') or "").strip()
            impact = (event.findtext('impact') or "").strip()
            forecast = (event.findtext('forecast') or "").strip()
            previous = (event.findtext('previous') or "").strip()
            parsed.append({
                'title': title,
                'country': country,
                'date': date_str,
                'time': time_str,
                'impact': impact,
                'forecast': forecast,
                'previous': previous
            })
        if parsed:
            _CACHED_EVENTS = parsed
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(parsed, f)
            return _CACHED_EVENTS
    except Exception as e:
        print(f"Calendar fetch notice: {e}")

    if not _CACHED_EVENTS:
        _CACHED_EVENTS = DEFAULT_EVENTS
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(DEFAULT_EVENTS, f)
        except Exception:
            pass

    return _CACHED_EVENTS

def format_upcoming_news_for_q30(pair: str = "XAUUSD") -> str:
    events = fetch_ff_events_cached()
    pair_currs = {
        "XAUUSD": ["USD", "All"],
        "USDJPY": ["USD", "JPY", "All"],
        "EURUSD": ["USD", "EUR", "All"],
        "GBPUSD": ["USD", "GBP", "All"],
        "OIL": ["USD", "All"]
    }.get(pair.upper(), ["USD", "All"])

    relevant = []
    for e in events:
        if e.get('impact') in ('High', 'Medium') and e.get('country') in pair_currs:
            dt_wib_str = ""
            try:
                dt_raw = f"{e['date']} {e['time']}"
                dt_edt = datetime.strptime(dt_raw, "%m-%d-%Y %I:%M%p").replace(tzinfo=EDT)
                dt_wib = dt_edt.astimezone(WIB)
                dt_wib_str = dt_wib.strftime("%d %b, %H:%M WIB")
            except Exception:
                dt_wib_str = f"{e.get('date')} {e.get('time')}"

            fcst_txt = f"Fcst: {e['forecast']}" if e.get('forecast') else "Fcst: -"
            prev_txt = f"Prev: {e['previous']}" if e.get('previous') else "Prev: -"
            impact_icon = "🔴" if e.get('impact') == "High" else "🟠"

            relevant.append(
                f"• {impact_icon} <b>[{e['country']}] {e['title']}</b> ({dt_wib_str}) | {fcst_txt} | {prev_txt}"
            )
            if len(relevant) >= 2:
                break

    if relevant:
        return "\n".join(relevant)
    return "• 🔴 <b>[USD] High-Impact Economic Data</b> | Memantau katalis jadwal The Fed"

if __name__ == "__main__":
    for sym in ["XAUUSD", "USDJPY", "EURUSD", "GBPUSD", "OIL"]:
        print(f"\n[{sym} Q30 Upcoming News]:")
        print(format_upcoming_news_for_q30(sym))
