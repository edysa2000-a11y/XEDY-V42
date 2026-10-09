import urllib.request
import xml.etree.ElementTree as ET
import os, json, time

def fetch_ff_events():
    url = 'https://nfs.faireconomy.media/ff_calendar_thisweek.xml'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=5) as r:
        xml_data = r.read()

    root = ET.fromstring(xml_data)
    events = []
    for event in root.findall('event'):
        title = event.findtext('title') or ""
        country = event.findtext('country') or ""
        date_str = event.findtext('date') or ""
        time_str = event.findtext('time') or ""
        impact = event.findtext('impact') or ""
        forecast = event.findtext('forecast') or ""
        previous = event.findtext('previous') or ""
        events.append({
            'title': title,
            'country': country,
            'date': date_str,
            'time': time_str,
            'impact': impact,
            'forecast': forecast,
            'previous': previous
        })
    return events

if __name__ == "__main__":
    evs = fetch_ff_events()
    print(f"Total parsed: {len(evs)}")
    high_med = [e for e in evs if e['impact'] in ('High', 'Medium') and e['country'] in ('USD', 'EUR', 'GBP', 'JPY', 'All')]
    print(f"Total High/Med major: {len(high_med)}")
    for e in high_med[:10]:
        print(f"• [{e['country']}] {e['title']} ({e['impact']}) | Date: {e['date']} {e['time']} | Fcst: {e['forecast']} | Prev: {e['previous']}")
