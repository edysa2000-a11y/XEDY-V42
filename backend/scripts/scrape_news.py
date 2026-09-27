import os
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import time
import email.utils
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from utils import get_live_multi_asset_prices
from telegram_template import generate_dashboard_msg

# Load local environment variables from .env file
load_dotenv()

# --- V38.5 RISK SETTINGS ---
ACTIVE_RISK_PROFILE = 'MODERATE' # CONSERVATIVE, NORMAL, MODERATE, EXTREME

def send_telegram_photo(token, chat_id, photo_path):
    if not token or not chat_id:
        return
    import subprocess
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    cmd = ["curl", "-s", "-X", "POST", url, "-F", f"chat_id={chat_id}", "-F", f"photo=@{photo_path}"]
    try:
        subprocess.run(cmd, timeout=30)
    except subprocess.TimeoutExpired:
        print("Telegram photo upload timed out.")

def render_report_image(template_data, output_path="data/report.png"):
    try:
        from jinja2 import Environment, FileSystemLoader
        from html2image import Html2Image
        import os
        
        env = Environment(loader=FileSystemLoader("backend/templates"))
        template = env.get_template("report.html")
        html_out = template.render(**template_data)
        
        # Write temporary HTML file (html2image handles files better with relative paths sometimes)
        tmp_html = "data/tmp_report.html"
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html_out)
            
        hti = Html2Image(output_path=os.path.dirname(output_path), custom_flags=['--no-sandbox', '--disable-gpu'])
        hti.screenshot(html_file=tmp_html, save_as=os.path.basename(output_path), size=(1200, 1100))
        if os.path.exists(tmp_html):
            os.remove(tmp_html)
        return True
    except Exception as e:
        print(f"Failed to render image: {e}")
        return False

def send_telegram_notification(token, chat_id, text):
    # Muted: Telegram is reserved exclusively for AI S/R Monitor (XAUUSD & USDJPY)
    return

def translate_to_id(text):
    if not text:
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=id&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5.0) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            translated = "".join([part[0] for part in res_data[0] if part[0]])
            return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def scrape_rss(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10.0) as r:
            xml_data = r.read()
            root = ET.fromstring(xml_data)
            articles = []
            for item in root.findall('.//item')[:15]:
                title = item.find('title')
                pub_date = item.find('pubDate')
                link = item.find('link')
                if title is not None:
                    raw_pub = pub_date.text if pub_date is not None else ""
                    # Normalize time to GMT+7 (Asia/Jakarta)
                    gmt7_pub = ""
                    if raw_pub:
                        try:
                            dt = email.utils.parsedate_to_datetime(raw_pub)
                            gmt7_dt = dt.astimezone(timezone(timedelta(hours=7)))
                            gmt7_pub = gmt7_dt.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception:
                            gmt7_pub = raw_pub
                    
                    articles.append({
                        "title": title.text,
                        "pubDate": gmt7_pub,
                        "link": link.text if link is not None else ""
                    })
            return articles
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

EMBEDDING_CACHE_FILE = "data/embedding_cache.json"

def load_embedding_cache():
    if os.path.exists(EMBEDDING_CACHE_FILE):
        try:
            with open(EMBEDDING_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_embedding_cache(cache_data):
    try:
        os.makedirs("data", exist_ok=True)
        # Prune cache to keep only the latest 2000 items to prevent GitHub repository bloat
        if len(cache_data) > 2000:
            keys_to_keep = list(cache_data.keys())[-2000:]
            cache_data = {k: cache_data[k] for k in keys_to_keep}
            
        with open(EMBEDDING_CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Failed to save embedding cache: {e}")

def get_qwen_embedding(api_key, text):
    """
    Calls Aivene embeddings API using Qwen3 Embedding 0.6B model with local cache.
    """
    if not api_key or not text:
        return []
    
    # Clean text to use as key
    cache_key = text.strip()
    cache = load_embedding_cache()
    if cache_key in cache:
        return cache[cache_key]

    url = "https://api.aivene.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "model": "qwen3-embedding-0.6b",
        "input": text
    }
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15.0) as r:
            res_json = json.loads(r.read().decode("utf-8"))
            vector = res_json["data"][0]["embedding"]
            
            # Save to cache
            cache[cache_key] = vector
            save_embedding_cache(cache)
            return vector
    except Exception as e:
        print(f"Failed to generate Qwen3 embedding: {e}")
        return []

def cosine_similarity(v1, v2):
    """
    Helper to calculate cosine similarity between two vectors.
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    import numpy as np
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return float(dot_product / (norm_v1 * norm_v2))


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

def clean_json_string(raw_str):
    raw_str = raw_str.strip()
    # Remove markdown code fences if present
    if raw_str.startswith("```"):
        lines = raw_str.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw_str = "\n".join(lines).strip()
    return raw_str

def get_qwen_analysis(api_key, news_text, prices, target_asset):
    if not api_key:
        return {"bias": "ANY", "regime": "NORMAL", "optimal_confidence_threshold": 0.68, "optimal_max_op": 4, "reasoning": "No API Key"}
        
    url = "https://api.aivene.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    # Load historical keyword memory
    memory_summary = ""
    memory_path = "data/keyword_impact_memory.json"
    if os.path.exists(memory_path):
        try:
            with open(memory_path, "r") as mf:
                mem_data = json.load(mf)
                # Sort memory by net profit to get top historical drivers
                top_mem = sorted(mem_data.items(), key=lambda x: x[1].get('net_profit', 0.0), reverse=True)[:5]
                if top_mem:
                    memory_summary = "\nHere is your historical trade memory for similar macro keyword drivers:\n" + "\n".join([
                        f"- {k}: Net Profit ${v['net_profit']:.2f}, Trade Count {v['trade_count']}, Winrate {v['winrate']*100:.0f}%" for k, v in top_mem
                    ])
        except Exception as e:
            print(f"Failed to load keyword memory in scraper: {e}")
            
    # FULL RAG IMPLEMENTATION FOR HISTORY & CALENDAR
    target_price = prices.get(target_asset, prices.get("XAUUSD", 0.0))
    market_state_text = f"{target_asset} at {target_price}, DXY at {prices.get('DXY', 0.0)}. Market is evaluating current structural trends for {target_asset}."
    current_market_vector = get_qwen_embedding(api_key, market_state_text)
    
    accuracy_summary = ""
    if current_market_vector:
        # 1. Trade History RAG
        rag_trades = get_trade_history_rag(api_key, current_market_vector)
        if rag_trades:
            accuracy_summary = "\n[RAG: TOP 3 MOST CORRELATED HISTORICAL TRADES]\n"
            for t in rag_trades:
                accuracy_summary += f"  • [Sim: {t.get('sim', 0.0)*100:.1f}%] Start: ${t.get('start', 0.0):.2f}, Target: ${t.get('target', 0.0):.2f}, Actual: ${t.get('actual_close', 0.0):.2f}, Status: {t.get('status', 'Unknown')}\n"
        
        # 2. Economic Calendar RAG
        rag_events = get_forex_factory_calendar_rag(api_key, current_market_vector)
        calendar_rag_text = ""
        if rag_events:
            calendar_rag_text = "\n[RAG: UPCOMING ECONOMIC EVENTS CORRELATED TO TREND]\n"
            for ev in rag_events:
                calendar_rag_text += f"  • {ev['title']} ({ev['impact']}) on {ev['time']} - Correlation: {ev['sim']*100:.1f}%\n"
            accuracy_summary += calendar_rag_text

    # Build multi-asset live pricing string
    gold_price = prices.get("XAUUSD", 0.0)
    prices_str = (
        f"\nHere are the current live market prices for key correlated macro assets:\n"
        f"- Target Asset ({target_asset}): ${prices.get(target_asset, 0.0)}\n"
        f"- Spot Gold (XAUUSD): ${gold_price:.2f}\n"
        f"- Spot Silver (XAGUSD): ${prices.get('XAGUSD', 0.0):.2f}\n"
        f"- Crude Oil WTI (USOIL): ${prices.get('USOIL', 0.0):.2f}\n"
        f"- EUR/USD: ${prices.get('EURUSD', 0.0):.4f}\n"
        f"- AUD/USD: ${prices.get('AUDUSD', 0.0):.4f}\n"
        f"- USD/CAD: ${prices.get('USDCAD', 0.0):.4f}\n"
        f"- NZD/USD: ${prices.get('NZDUSD', 0.0):.4f}\n"
        f"- US Dollar Index (DXY): {prices.get('DXY', 0.0):.2f}\n"
        f"- US 10Y Treasury Yield: {prices.get('US10Y', 0.0):.2f}%\n"
    )

    system_prompt = """You are the Chief Strategist AI (Qwen AI) for the XEDY algorithmic trading platform.
Analyze the news headlines, identify any recent US economic calendar data releases, study the cross-market prices, and decide the macro trading bias specifically for the asset: {target_asset}.
Write your explanation (ai_narrative_id) in strictly formal Indonesian (EYD/KBBI) like a top-tier Global Professional Economist, using advanced terminology and deep causal logic regarding how the news impacts {target_asset}. Ensure perfect spelling (e.g., use 'korelasi', 'fundamental'). Keep the narrative concise, impactful, and structured (maximum 4 sentences).
You MUST respond ONLY with a valid JSON object matching this structure, without markdown code fences:
{
  "ai_narrative_id": "Detailed explanation in INDONESIAN like a Professional Economist",
  "forward_implication": "2-3 sentences predicting future conditions in Indonesian",
  "fundamental_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "capital_flow": "INFLOW" | "OUTFLOW" | "MIXED",
  "driver_fed": {"bias": "Bullish|Bearish|Neutral", "impact": "HIGH|MEDIUM|LOW", "conf": 82},
  "driver_geopolitics": {"bias": "Bullish|Bearish|Neutral", "impact": "HIGH|MEDIUM|LOW", "conf": 86},
  "driver_dxy": {"bias": "Bullish|Bearish|Neutral", "impact": "HIGH|MEDIUM|LOW", "conf": 91},
  "driver_us10y": {"bias": "Bullish|Bearish|Neutral", "impact": "HIGH|MEDIUM|LOW", "conf": 88},
  "driver_structure": {"bias": "Bullish|Bearish|Neutral", "impact": "HIGH|MEDIUM|LOW", "conf": 94},
  "driver_money_flow": {"bias": "Bullish|Bearish|Neutral", "impact": "HIGH|MEDIUM|LOW", "conf": 79},
  "driver_energy": {"bias": "Bullish|Bearish|Neutral", "impact": "HIGH|MEDIUM|LOW", "conf": 67},
  "driver_data": {"bias": "Bullish|Bearish|Neutral", "impact": "HIGH|MEDIUM|LOW", "conf": 71},
  "tertiary_driver": "e.g. POLICY UNCERTAINTY",
  "next_regime_sideway_prob": 24,
  "next_regime_bear_prob": 8,
  "bias": "BUY_ONLY" | "SELL_ONLY" | "ANY" | "WAIT",
  "regime": "TRENDING BULL" | "TRENDING BEAR" | "SIDEWAY" | "HIGH VOLATILITY",
  "primary_driver": "e.g. FED INDEPENDENCE RISK",
  "secondary_driver": "e.g. SAFE-HAVEN DEMAND",
  "causality_score": float (e.g. 0.63 or -0.80),
  "causal_confidence": float (e.g. 0.78),
  "intermarket_dxy": "Bullish | Bearish | Neutral",
  "intermarket_us10y": "Bullish | Bearish | Neutral",
  "news_event_impact": "HIGH | MEDIUM | LOW",
  "fed_shock_level": int (1 to 5),
  "mtf_alignment_score": float (e.g. 0.72),
  "invalidation_criteria": ["Reason 1", "Reason 2", "Reason 3"],
  "conf_fundamental": float (0 to 1),
  "conf_news": float (0 to 1),
  "conf_fed_shock": float (0 to 1),
  "forecast_price_target": float,
  "forecast_duration_hours": int,
  "tp1_price": float,
  "tp2_price": float,
  "sl_price": float,
  "win_rate_pct": int (e.g. 78),
  "profit_factor": float (e.g. 2.14),
  "expectancy_r": float (e.g. 0.42),
  "max_drawdown_pct": float (e.g. 7.2),
  "sharpe_ratio": float (e.g. 1.86),
  "sortino_ratio": float (e.g. 2.31),
  "bull_case_score": int (e.g. 91),
  "bear_case_score": int (e.g. 13),
  "contrarian_risk_pct": int (e.g. 31),
  "edge_structure_dxy": float (e.g. 0.82),
  "edge_fed": float (e.g. 0.76),
  "edge_momentum": float (e.g. 0.71),
  "reasoning": "Brief explanation in English"
}"""
    system_prompt = system_prompt.replace('{target_asset}', target_asset)
    payload = {
        "model": "qwen3.7-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the daily news summary:\n{news_text}\n{prices_str}\n{memory_summary}\n{accuracy_summary}"}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    # Try calling API with up to 3 retries and exponential backoff
    for attempt in range(1, 4):
        try:
            print(f"Calling Qwen API (Attempt {attempt}/3)...")
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60.0) as r:
                res_json = json.loads(r.read().decode("utf-8"))
                content = res_json['choices'][0]['message']['content'].strip()
                cleaned_content = clean_json_string(content)
                result_json = json.loads(cleaned_content)
                result_json['calendar_rag_display'] = calendar_rag_text if 'calendar_rag_text' in locals() else "No calendar RAG data available."
                return result_json
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < 3:
                sleep_time = attempt * 3
                print(f"Waiting {sleep_time}s before retrying...")
                time.sleep(sleep_time)
            else:
                print("All Qwen API retry attempts exhausted.")
                return {"bias": "ANY", "regime": "NORMAL", "optimal_confidence_threshold": 0.68, "optimal_max_op": 4, "reasoning": f"API Retry Error: {e}"}

def main():
    api_key = os.getenv("AIVENE_API_KEY", "")
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_chat = os.getenv("TELEGRAM_ADMIN_ID", "")
    
    print("Starting Cloud News Scraper...")
    
    # Fetch live multi-asset prices at run time
    prices = get_live_multi_asset_prices()
    gold_price = prices.get("XAUUSD", 0.0)
    print(f"Current live Spot Gold price: ${gold_price:.2f} | Oil: ${prices.get('USOIL', 0.0):.2f} | DXY: {prices.get('DXY', 0.0):.2f}")
    
    # 1. Scrape Google News Gold, DXY, geopolitical, macroeconomic, and US Presidential Speech
    google_url = 'https://news.google.com/rss/search?q=(gold+OR+xauusd+OR+dxy+OR+\"US+dollar\"+OR+ecb+OR+boe+OR+boj+OR+rba+OR+\"reserve+bank+of+australia\"+OR+boc+OR+\"bank+of+canada\"+OR+rbnz+OR+fomc+OR+\"jerome+powell\")+(war+OR+geopolitics+OR+fed+OR+inflation+OR+nfp+OR+gdp+OR+cpi+OR+tariff+OR+oil+OR+australia+OR+canada+OR+\"new+zealand\")&hl=en-US&gl=US&ceid=US:en'
    articles = scrape_rss(google_url)
    
    if not articles:
        print("No articles found.")
        return
        
    print(f"Scraped {len(articles)} headlines successfully.")
    
    # Fetch target semantic vector once for cross-market alignment reference
    target_macro_query = "gold price xauusd dollar index dxy treasury yields federal reserve cpi nfp rate decision geopolitics US president Donald Trump tariff war ecb eurozone boe uk boj japan rba australia boc canada rbnz new zealand"
    target_vector = get_qwen_embedding(api_key, target_macro_query)
    if target_vector:
        print(f"Generated target Qwen3 embedding vector for macro alignment: size {len(target_vector)}")
    
    # Filter and weight articles to last 48 hours (GMT+7) with semantic relevance boost
    local_now = datetime.utcnow() + timedelta(hours=7)
    forty_eight_hours_ago = local_now - timedelta(hours=48)
    twenty_four_hours_ago = local_now - timedelta(hours=24)
    weighted_articles = []
    
    def process_article(art):
        try:
            art_dt = datetime.strptime(art["pubDate"], "%Y-%m-%d %H:%M:%S")
            if art_dt >= forty_eight_hours_ago:
                age_hours = int((local_now - art_dt).total_seconds() / 3600)
                title_upper = art["title"].upper()
                is_presidential = "TRUMP" in title_upper or "PRESIDENT" in title_upper
                
                sim_score = 0.50
                if target_vector:
                    art_vector = get_qwen_embedding(api_key, art["title"])
                    if art_vector:
                        sim_score = cosine_similarity(target_vector, art_vector)
                        if is_presidential:
                            sim_score = min(1.0, sim_score + 0.15)
                
                if target_vector and sim_score < 0.35 and not is_presidential:
                    return None
                    
                critical_topics = ["WAR", "GEOPOLITICS", "CONFLICT", "TARIFF", "GOLD", "XAUUSD", "CHINA", "TRADE"]
                if is_presidential and any(topic in title_upper for topic in critical_topics):
                    weight = "150% (CRITICAL / HIGH PRIORITY)"
                    weight_label = "PIDATO PRESIDEN / GEOPOLITIK"
                elif art_dt >= twenty_four_hours_ago:
                    weight = "100% (FRESH)"
                    weight_label = "BARU/KUAT"
                else:
                    weight = "40% (WEAK / DECAYED)"
                    weight_label = "LAMA/LEMAH"
                
                art["weight"] = weight
                art["weight_label"] = weight_label
                art["age_hours"] = age_hours
                art["similarity"] = sim_score
                return art
        except Exception as e:
            print(f"Error processing article '{art.get('title', 'Unknown')}': {e}")
        return None

    # Use ThreadPoolExecutor to fetch embeddings for all articles concurrently
    print(f"Starting multi-threaded embedding extraction for {len(articles)} articles (Max workers: 25)...")
    with ThreadPoolExecutor(max_workers=25) as executor:
        results = executor.map(process_article, articles)
        
    for res in results:
        if res:
            weighted_articles.append(res)
            
    print(f"Finished processing. {len(weighted_articles)} articles passed the semantic filter.")
            
    # Fallback to general list if no news in last 48h
    if not weighted_articles:
        print("No new articles in last 48 hours. Falling back to most recent headlines.")
        weighted_articles = articles[:8]
        for art in weighted_articles:
            art["weight"] = "100% (FRESH)"
            art["weight_label"] = "BARU/KUAT"
            art["age_hours"] = 0
    else:
        # Sort by similarity descending (most relevant first) to feed the best market drivers to Qwen
        weighted_articles = sorted(weighted_articles, key=lambda x: x.get("similarity", 0.0), reverse=True)[:8]
        print(f"Filtered and sorted to {len(weighted_articles)} semantically aligned headlines.")
        
    # 2. Compile and translate headlines
    news_text = ""
    tg_news_list = []
    for idx, art in enumerate(weighted_articles):
        headline_en = art["title"]
        pub_t = art["pubDate"]
        weight = art.get("weight", "100% (FRESH)")
        age = art.get("age_hours", 0)
        
        # Translate headline to Indonesian
        headline_id = translate_to_id(headline_en)
        
        escaped_link = art['link'].replace("&", "&amp;")
        news_text += f"- {headline_en} ({pub_t}) [Age: {age}h, Weight: {weight}]\n"
        tg_news_list.append(f"{idx+1}. <a href=\"{escaped_link}\">{headline_id}</a>\n   Rilis: {pub_t} WIB ({art.get('weight_label')})")
        
    # 3. Analyze with Qwen AI in the Cloud for 4 Assets Concurrently
    print("Calling Qwen AI for Macro Analysis on Target Assets...")
    target_assets = ["XAUUSD", "AUDUSD", "USDCAD", "NZDUSD"]
    results_dict = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_asset = {executor.submit(get_qwen_analysis, api_key, news_text, prices, ta): ta for ta in target_assets}
        for future in concurrent.futures.as_completed(future_to_asset):
            ta = future_to_asset[future]
            try:
                results_dict[ta] = future.result()
            except Exception as exc:
                print(f"{ta} analysis generated an exception: {exc}")
                results_dict[ta] = {"bias": "WAIT"}

    # Assign XAUUSD analysis to 'analysis' variable so the old reflection loop doesn't crash
    analysis = results_dict.get("XAUUSD", {"bias": "WAIT"})
    print(f"Qwen Initial Bias Result for Gold: {analysis.get('bias')}")
    
    # 3.5. AGENTIC REFLECTION LOOP (Validate AI vs Real Market Price)
    xau_change = prices.get("XAUUSD_CHANGE", 0.0)
    actual_trend = "BULLISH" if xau_change > 0 else "BEARISH"
    ai_bias = analysis.get("bias", "")
    
    # If AI says BUY but market is dropping, or SELL but market is rising, challenge the AI
    if (ai_bias == "BUY_ONLY" and actual_trend == "BEARISH") or (ai_bias == "SELL_ONLY" and actual_trend == "BULLISH"):
        print(f"[!] VALIDATION FAILURE: AI predicted {ai_bias} but actual market trend is {actual_trend} (Change: {xau_change:.2f}). Triggering Reflection Loop...")
        reflection_prompt = (
            f"TUNGGU! Analisismu sebelumnya menyimpulkan BIAS = {ai_bias}. "
            f"Namun, FAKTA di pasar saat ini harga Emas justru bergerak {actual_trend} (Perubahan: {xau_change:.2f}). "
            f"Apakah kamu melewatkan sesuatu? Apakah pasar melakukan 'Buy the Rumor Sell the Fact'? "
            f"Tolong review ulang berita dan korelasinya dengan pergerakan harga nyata ini. Sesuaikan BIAS dan MARKET_SUMMARY_ID-mu!"
        )
        
        # Inject reflection into the news text so Qwen re-evaluates
        reflected_news_text = news_text + f"\n\n[SYSTEM OVERRIDE/REFLECTION]\n{reflection_prompt}\n"
        analysis = get_qwen_analysis(api_key, reflected_news_text, prices, "XAUUSD")
        print(f"Qwen Reflected Bias Result: {analysis.get('bias')}")
    
    # Translate Qwen's reasoning to Indonesian
    reasoning_en = analysis.get('reasoning', '')
    reasoning_id = translate_to_id(reasoning_en)
    
    # 4. Save results to JSON (timestamp in GMT+7 for local PC sync)
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Load previous macro analysis to check for changes (Anti-Spam Filter)
    prev_analysis = {}
    news_feed_path = os.path.join(output_dir, "news_feed.json")
    if os.path.exists(news_feed_path):
        try:
            with open(news_feed_path, "r") as f:
                prev_data = json.load(f)
                prev_analysis = prev_data.get("macro_analysis", {})
        except Exception as e:
            print(f"Failed to load previous news feed: {e}")
            
    # 5. Telegram Notification Logic & Data Saving
    local_now = datetime.utcnow() + timedelta(hours=7)
    
    # Save the new analysis to disk
    news_feed_data = {
        "generated_at": local_now.strftime("%Y-%m-%d %H:%M:%S WIB"),
        "news": weighted_articles,
        "macro_analysis": results_dict
    }
    tmp_feed_path = news_feed_path + ".tmp"
    with open(tmp_feed_path, "w") as f:
        json.dump(news_feed_data, f, indent=2)
    os.replace(tmp_feed_path, news_feed_path)
    
    # Build and send Telegram Message
    try:
        tg_msgs = generate_dashboard_msg(news_feed_data, results_dict, prices)
        for msg in tg_msgs:
            send_telegram_notification(tg_token, tg_chat, msg)
            time.sleep(1.0)
    except Exception as e:
        print(f"Failed to send telegram macro update: {e}")
    
    # Append to Qwen Decisions Log for self-learning (We still log XAUUSD specifically for the Digital Twin engine)
    gold_price = prices.get("XAUUSD", 0.0)
    analysis = results_dict.get("XAUUSD", {})
    log_entry = {
        "timestamp": local_now.strftime("%Y-%m-%d %H:%M:%S"),
        "bias": analysis.get("bias"),
        "regime": analysis.get("regime"),
        "optimal_confidence_threshold": analysis.get("optimal_confidence_threshold"),
        "optimal_max_op": analysis.get("optimal_max_op"),
        "optimal_method": analysis.get("optimal_method"),
        "economic_releases": analysis.get("economic_releases", []),
        "forecast_price_target": analysis.get("forecast_price_target", 0.0),
        "forecast_duration_hours": analysis.get("forecast_duration_hours", 0),
        "forecast_high_24h": analysis.get("forecast_high_24h", 0.0),
        "forecast_low_24h": analysis.get("forecast_low_24h", 0.0),
        "forecast_close_24h": analysis.get("forecast_close_24h", 0.0),
        "forecast_reasoning_id": analysis.get("forecast_reasoning_id", ""),
        "forecasts": analysis.get("forecasts", {}),
        "start_gold_price": gold_price,
        "reasoning": analysis.get("reasoning")
    }
    log_file_path = os.path.join(output_dir, "qwen_decisions_log.jsonl")
    with open(log_file_path, "a") as lf:
        lf.write(json.dumps(log_entry) + "\n")

if __name__ == "__main__":
    main()
