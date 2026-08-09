import os
import re

def main():
    file_path = "c:/Antigravity/Project/XEDY Mission Control/backend/scripts/scrape_news.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add XML ElementTree import if not present
    if "import xml.etree.ElementTree as ET" not in content:
        content = content.replace("import json", "import json\nimport xml.etree.ElementTree as ET")

    # 2. Inject RAG functions after cosine_similarity
    rag_functions = """
def get_forex_factory_calendar_rag(api_key, target_vector):
    try:
        req = urllib.request.Request("https://nfs.faireconomy.media/ff_calendar_thisweek.xml", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10.0) as r:
            xml_data = r.read()
        root = ET.fromstring(xml_data)
        
        events = []
        for event in root.findall('event'):
            country = event.find('country').text
            impact = event.find('impact').text
            if country == "USD" and impact in ["High", "Medium"]:
                title = event.find('title').text
                date_str = event.find('date').text
                time_str = event.find('time').text
                forecast = event.find('forecast').text or ""
                
                text_to_embed = f"US Economic Event: {title} on {date_str} {time_str}. Forecast: {forecast}. Impact: {impact}."
                vector = get_qwen_embedding(api_key, text_to_embed)
                sim = cosine_similarity(target_vector, vector) if vector else 0.0
                
                events.append({
                    "title": title,
                    "impact": impact,
                    "time": f"{date_str} {time_str}",
                    "sim": sim
                })
                
        events.sort(key=lambda x: x['sim'], reverse=True)
        return events[:3]
    except Exception as e:
        print(f"Failed to fetch FF calendar RAG: {e}")
        return []

def get_trade_history_rag(api_key, current_market_vector):
    try:
        acc_path = "data/forecast_accuracy_stats.json"
        if not os.path.exists(acc_path): return []
        
        with open(acc_path, "r") as f:
            acc_data = json.load(f)
            
        history = acc_data.get("history", [])
        if not history: return []
        
        rag_history = []
        for h in history:
            text = f"Past trade pattern: Start {h.get('start')}, Target {h.get('target')}, Actual Close {h.get('actual_close')}, Status {h.get('status')}."
            vector = get_qwen_embedding(api_key, text)
            sim = cosine_similarity(current_market_vector, vector) if vector else 0.0
            h['sim'] = sim
            rag_history.append(h)
            
        rag_history.sort(key=lambda x: x['sim'], reverse=True)
        return rag_history[:3]
    except Exception as e:
        print(f"Failed RAG history: {e}")
        return []
"""
    if "get_forex_factory_calendar_rag" not in content:
        content = content.replace("def clean_json_string(raw_str):", rag_functions + "\ndef clean_json_string(raw_str):")

    # 3. Update get_qwen_analysis signature and logic
    # Right now, get_qwen_analysis only takes (api_key, news_text, prices)
    # We need to pass target_vector or generate a market vector inside it.
    
    # We will generate market_vector inside get_qwen_analysis
    # And then call the RAG functions.
    
    old_acc_logic = """    # Load forecast accuracy memory for reinforcement learning
    accuracy_summary = ""
    accuracy_path = "data/forecast_accuracy_stats.json"
    if os.path.exists(accuracy_path):
        try:
            with open(accuracy_path, "r") as af:
                acc_data = json.load(af)
                accuracy_summary = (
                    f"\\n[CRITICAL GOAL: TARGET >90% ACCURACY]\\n"
                    f"Your current forecast accuracy statistics:\\n"
                    f"- Average Accuracy: {acc_data.get('avg_accuracy', 0.0)*100:.1f}%\\n"
                    f"- Total Predictions Analyzed: {acc_data.get('total_predictions', 0)}\\n"
                    f"- Successful Targets Hit: {acc_data.get('successful_hits', 0)}\\n"
                    f"Past predictions feedback list (learn from your pricing/duration mistakes):\\n"
                )
                for item in acc_data.get("history", [])[-5:]:
                    accuracy_summary += f"  • Start: ${item.get('start', 0.0):.2f}, Target: ${item.get('target', 0.0):.2f}, Actual: ${item.get('actual_close', 0.0):.2f}, Error: {item.get('error_pct', 0.0)*100:.1f}%, Status: {item.get('status', 'Unknown')}\\n"
        except Exception as e:
            print(f"Failed to load forecast accuracy: {e}")"""
            
    new_acc_logic = """    # FULL RAG IMPLEMENTATION FOR HISTORY & CALENDAR
    market_state_text = f"XAUUSD at {prices.get('XAUUSD', 0.0)}, DXY at {prices.get('DXY', 0.0)}. Market is evaluating current structural trends."
    current_market_vector = get_qwen_embedding(api_key, market_state_text)
    
    accuracy_summary = ""
    if current_market_vector:
        # 1. Trade History RAG
        rag_trades = get_trade_history_rag(api_key, current_market_vector)
        if rag_trades:
            accuracy_summary = "\\n[RAG: TOP 3 MOST CORRELATED HISTORICAL TRADES]\\n"
            for t in rag_trades:
                accuracy_summary += f"  • [Sim: {t.get('sim', 0.0)*100:.1f}%] Start: ${t.get('start', 0.0):.2f}, Target: ${t.get('target', 0.0):.2f}, Actual: ${t.get('actual_close', 0.0):.2f}, Status: {t.get('status', 'Unknown')}\\n"
        
        # 2. Economic Calendar RAG
        rag_events = get_forex_factory_calendar_rag(api_key, current_market_vector)
        calendar_rag_text = ""
        if rag_events:
            calendar_rag_text = "\\n[RAG: UPCOMING ECONOMIC EVENTS CORRELATED TO TREND]\\n"
            for ev in rag_events:
                calendar_rag_text += f"  • {ev['title']} ({ev['impact']}) on {ev['time']} - Correlation: {ev['sim']*100:.1f}%\\n"
            accuracy_summary += calendar_rag_text"""
            
    content = content.replace(old_acc_logic, new_acc_logic)
    
    # 4. Inject RAG calendar text into Telegram message (p3)
    # Right now p3 has hardcoded calendar
    old_p3_cal = """📅 ECONOMIC CALENDAR
NEXT HIGH-IMPACT EVENTS
CPI / PCE       🔴 HIGH
NFP             🔴 HIGH
FOMC            🔴 HIGH
Fed Speech      🟠 HIGH
GDP / ISM       🟡 MEDIUM"""

    # We need to save the rag_events to a global variable or return it.
    # Actually, the scraping is done in the main loop, we can just call it there.
    # Wait, the telegram message generation is in the main loop!
    # I will replace the hardcoded calendar with a placeholder and format it in the main loop.
    
    new_p3_cal = """📅 ECONOMIC CALENDAR (QWEN3 RAG)
{calendar_rag_display}"""
    
    content = content.replace(old_p3_cal, new_p3_cal)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Injected RAG architecture successfully")

if __name__ == "__main__":
    main()
