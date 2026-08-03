import os
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import time
import email.utils
from dotenv import load_dotenv

# Load local environment variables from .env file
load_dotenv()

def send_telegram_notification(token, chat_id, text):
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data_bytes, 
            headers={"Content-Type": "application/json"}, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10.0) as r:
            r.read()
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

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

def get_live_multi_asset_prices():
    prices = {"XAUUSD": 0.0, "USOIL": 0.0, "DXY": 0.0, "US10Y": 0.0}
    
    # 1. Prioritas 1: Ambil dari TradingView CFD Scan untuk semua aset (Batch Request)
    try:
        url_tv = "https://scanner.tradingview.com/cfd/scan"
        payload_tv = {
            "symbols": {
                "tickers": ["FX_IDC:XAUUSD", "TVC:USOIL", "TVC:DXY", "TVC:US10Y"],
                "query": { "types": [] }
            },
            "columns": ["close"]
        }
        req_tv = urllib.request.Request(
            url_tv, 
            data=json.dumps(payload_tv).encode("utf-8"), 
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req_tv, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("data"):
                for item in data["data"]:
                    ticker = item["s"]
                    close_price = float(item["d"][0])
                    if "XAUUSD" in ticker: prices["XAUUSD"] = close_price
                    elif "USOIL" in ticker: prices["USOIL"] = close_price
                    elif "DXY" in ticker: prices["DXY"] = close_price
                    elif "US10Y" in ticker: prices["US10Y"] = close_price
                print(f"Fetched live multi-asset prices from TradingView: {prices}")
                if prices["XAUUSD"] > 0:
                    return prices
    except Exception as e:
        print(f"Failed to fetch batch prices from TradingView: {e}")

    # 2. Fallback: Ambil secara terpisah menggunakan Yahoo Finance
    try:
        # Fallback XAUUSD via PAXG-USD
        if prices["XAUUSD"] == 0.0:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/PAXG-USD?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
                prices["XAUUSD"] = float(data['chart']['result'][0]['meta']['regularMarketPrice'])
        
        # Fallback USOIL via CL=F
        if prices["USOIL"] == 0.0:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/CL=F?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
                prices["USOIL"] = float(data['chart']['result'][0]['meta']['regularMarketPrice'])

        # Fallback DXY via DX-Y.NYB
        if prices["DXY"] == 0.0:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
                prices["DXY"] = float(data['chart']['result'][0]['meta']['regularMarketPrice'])

        # Fallback US10Y via ^TNX
        if prices["US10Y"] == 0.0:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/^TNX?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
                prices["US10Y"] = float(data['chart']['result'][0]['meta']['regularMarketPrice'])
                
        print(f"Fetched live multi-asset prices using Yahoo fallbacks: {prices}")
    except Exception as e:
        print(f"Failed to fetch Yahoo fallback prices: {e}")

    return prices

def scrape_rss(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10.0) as r:
            xml_data = r.read()
            root = ET.fromstring(xml_data)
            articles = []
            for item in root.findall('.//item')[:5]:
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
        with open(EMBEDDING_CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Failed to save embedding cache: {e}")

def get_qwen_embedding(api_key, text):
    """
    Calls Aivene embeddings API using Qwen3 Embedding 8B model with local cache.
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
        "model": "qwen3-embedding-8b",
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

def get_qwen_analysis(api_key, news_text, prices):
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
            
    # Load forecast accuracy memory for reinforcement learning
    accuracy_summary = ""
    accuracy_path = "data/forecast_accuracy_stats.json"
    if os.path.exists(accuracy_path):
        try:
            with open(accuracy_path, "r") as af:
                acc_data = json.load(af)
                accuracy_summary = (
                    f"\n[CRITICAL GOAL: TARGET >90% ACCURACY]\n"
                    f"Your current forecast accuracy statistics:\n"
                    f"- Average Accuracy: {acc_data.get('avg_accuracy', 0.0)*100:.1f}%\n"
                    f"- Total Predictions Analyzed: {acc_data.get('total_predictions', 0)}\n"
                    f"- Successful Targets Hit: {acc_data.get('successful_hits', 0)}\n"
                    f"Past predictions feedback list (learn from your pricing/duration mistakes):\n"
                )
                for item in acc_data.get("history", [])[-5:]:
                    accuracy_summary += f"  • Start: ${item.get('start', 0.0):.2f}, Target: ${item.get('target', 0.0):.2f}, Actual: ${item.get('actual_close', 0.0):.2f}, Error: {item.get('error_pct', 0.0)*100:.1f}%, Status: {item.get('status', 'Unknown')}\n"
        except Exception as e:
            print(f"Failed to load forecast accuracy: {e}")

    # Build multi-asset live pricing string
    gold_price = prices.get("XAUUSD", 0.0)
    prices_str = (
        f"\nHere are the current live market prices for key correlated macro assets:\n"
        f"- Spot Gold (XAUUSD): ${gold_price:.2f}\n"
        f"- Crude Oil WTI (USOIL): ${prices.get('USOIL', 0.0):.2f}\n"
        f"- US Dollar Index (DXY): {prices.get('DXY', 0.0):.2f}\n"
        f"- US 10Y Treasury Yield: {prices.get('US10Y', 0.0):.2f}%\n"
    )

    system_prompt = (
        "You are the Chief Strategist AI (Qwen AI) for the XEDY algorithmic trading platform.\n"
        "Analyze the news headlines, identify any recent US economic calendar data releases (like GDP, PCE, CPI, NFP) mentioned, study the cross-market prices (Gold vs DXY, Yields, and Oil), and decide the macro trading bias.\n"
        "You MUST respond ONLY with a valid JSON object matching this structure, without markdown code fences:\n"
        "{\n"
        "  \"bias\": \"BUY_ONLY\" | \"SELL_ONLY\" | \"ANY\" | \"WAIT\",\n"
        "  \"regime\": \"NORMAL\" | \"HIGH_NEWS\" | \"SIDEWAYS\",\n"
        "  \"optimal_confidence_threshold\": float (value between 0.60 and 0.85),\n"
        "  \"optimal_max_op\": int (value between 2 and 6),\n"
        "  \"optimal_method\": \"Opsi X: [Method Name] (e.g. Opsi 5: Scalping 1:1, Opsi 2: Breakout Stop-Entry, Opsi 8: H1 Pyramid)\",\n"
        "  \"economic_releases\": [\"Release 1 with value and brief impact in INDONESIAN\", \"Release 2 in INDONESIAN\"],\n"
        "  \"forecast_price_target\": float (Estimated target price for XAUUSD, e.g. 2425.50. Make it realistic based on news impact),\n"
        "  \"forecast_duration_hours\": int (Estimated duration in hours to reach target price, e.g. 24),\n"
        "  \"forecast_high_24h\": float (Estimated 24-hour HIGH price for XAUUSD),\n"
        "  \"forecast_low_24h\": float (Estimated 24-hour LOW price for XAUUSD),\n"
        "  \"forecast_close_24h\": float (Estimated 24-hour CLOSE price for XAUUSD),\n"
        "  \"forecast_reasoning_id\": \"Detailed explanation in INDONESIAN explaining the analysis and causes of these forecast price targets so it is easy to understand\",\n"
        "  \"forecasts\": {\n"
        "    \"1d\": {\n"
        "      \"open\": float (Current Gold price, e.g. 4058.50),\n"
        "      \"high\": float (Expected 1-day highest price),\n"
        "      \"low\": float (Expected 1-day lowest price),\n"
        "      \"close\": float (Expected 1-day closing price),\n"
        "      \"reasoning_id\": \"Detailed explanation in INDONESIAN for 1-day perspective\"\n"
        "    },\n"
        "    \"1w\": {\n"
        "      \"open\": float (Current Gold price),\n"
        "      \"high\": float (Expected 1-week highest price),\n"
        "      \"low\": float (Expected 1-week lowest price),\n"
        "      \"close\": float (Expected 1-week closing price),\n"
        "      \"reasoning_id\": \"Detailed explanation in INDONESIAN for 1-week perspective\"\n"
        "    },\n"
        "    \"2w\": {\n"
        "      \"open\": float (Current Gold price),\n"
        "      \"high\": float (Expected 2-week highest price),\n"
        "      \"low\": float (Expected 2-week lowest price),\n"
        "      \"close\": float (Expected 2-week closing price),\n"
        "      \"reasoning_id\": \"Detailed explanation in INDONESIAN for 2-week perspective\"\n"
        "    }\n"
        "  },\n"
        "  \"reasoning\": \"Brief explanation in English\"\n"
        "}"
    )
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
                return json.loads(cleaned_content)
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
    
    # 1. Scrape Google News Gold, DXY, geopolitical, macroeconomic, and US Presidential Speech feed
    google_url = 'https://news.google.com/rss/search?q=(gold+OR+xauusd+OR+dxy+OR+\"US+dollar\"+OR+\"treasury+yields\"+OR+trump+OR+\"president+speech\"+OR+\"trump+comments\")+(war+OR+geopolitics+OR+conflict+OR+fed+OR+inflation+OR+nfp+OR+gdp+OR+cpi+OR+tariff)&hl=en-US&gl=US&ceid=US:en'
    articles = scrape_rss(google_url)
    
    if not articles:
        print("No articles found.")
        return
        
    print(f"Scraped {len(articles)} headlines successfully.")
    
    # Fetch target semantic vector once for cross-market alignment reference
    target_macro_query = "gold price xauusd dollar index dxy treasury yields federal reserve cpi nfp rate decision geopolitics US president Donald Trump speech tariff comments war"
    target_vector = get_qwen_embedding(api_key, target_macro_query)
    if target_vector:
        print(f"Generated target Qwen3 embedding vector for macro alignment: size {len(target_vector)}")
    
    # Filter and weight articles to last 48 hours (GMT+7) with semantic relevance boost
    local_now = datetime.utcnow() + timedelta(hours=7)
    forty_eight_hours_ago = local_now - timedelta(hours=48)
    twenty_four_hours_ago = local_now - timedelta(hours=24)
    weighted_articles = []
    
    for art in articles:
        try:
            art_dt = datetime.strptime(art["pubDate"], "%Y-%m-%d %H:%M:%S")
            if art_dt >= forty_eight_hours_ago:
                age_hours = int((local_now - art_dt).total_seconds() / 3600)
                
                title_upper = art["title"].upper()
                is_presidential = "TRUMP" in title_upper or "PRESIDENT" in title_upper
                
                # Fetch headline vector and check semantic alignment
                sim_score = 0.50 # default fallback
                if target_vector:
                    art_vector = get_qwen_embedding(api_key, art["title"])
                    if art_vector:
                        sim_score = cosine_similarity(target_vector, art_vector)
                        
                        # Boost presidential speech relevance semantically
                        if is_presidential:
                            sim_score = min(1.0, sim_score + 0.15)
                        
                        print(f"Headline: '{art['title'][:45]}...' | Semantic Similarity: {sim_score:.4f}")
                
                # Ignore articles below 0.35 similarity (noise filter), unless it's presidential comments
                if target_vector and sim_score < 0.35 and not is_presidential:
                    print(f"Skipping unrelated headline (noise): '{art['title'][:40]}...' (Similarity: {sim_score:.4f})")
                    continue

                # Set custom high priority weights for presidential speeches containing critical market topics
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
                weighted_articles.append(art)
        except Exception as e:
            # Fallback if parse fails
            art["weight"] = "100% (FRESH)"
            art["weight_label"] = "BARU/KUAT"
            art["age_hours"] = 0
            art["similarity"] = 0.5
            weighted_articles.append(art)
            
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
        
    # 3. Analyze with Qwen AI in the Cloud
    print("Calling Qwen AI for Macro Analysis...")
    analysis = get_qwen_analysis(api_key, news_text, prices)
    print(f"Qwen Bias Result: {analysis.get('bias')}")
    
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
            
    # Check for changes in key decision fields
    has_changed = True
    if prev_analysis:
        prev_bias = prev_analysis.get("bias", "")
        prev_regime = prev_analysis.get("regime", "")
        prev_method = prev_analysis.get("optimal_method", "")
        
        curr_bias = analysis.get("bias", "")
        curr_regime = analysis.get("regime", "")
        curr_method = analysis.get("optimal_method", "")
        
        if prev_bias == curr_bias and prev_regime == curr_regime and prev_method == curr_method:
            has_changed = False
    
    local_now = datetime.utcnow() + timedelta(hours=7)
    news_feed_data = {
        "generated_at": local_now.strftime("%Y-%m-%d %H:%M:%S WIB"),
        "news": weighted_articles,
        "macro_analysis": analysis
    }
    
    with open(news_feed_path, "w") as f:
        json.dump(news_feed_data, f, indent=2)
        
    # Append to Qwen Decisions Log for self-learning
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
         
    # Translate structural terms
    bias_map = {
        "BUY_ONLY": "KHUSUS_BELI (BUY_ONLY)",
        "SELL_ONLY": "KHUSUS_JUAL (SELL_ONLY)",
        "ANY": "BEBAS (BUY/SELL - ANY)",
        "WAIT": "TUNGGU (WAIT/NC)"
    }
    regime_map = {
        "NORMAL": "NORMAL (TREN STABIL)",
        "HIGH_NEWS": "VOLATILITAS TINGGI (BERITA)",
        "SIDEWAYS": "SIDEWAYS (KONSOLIDASI)"
    }
    
    translated_bias = bias_map.get(analysis.get('bias', 'ANY'), analysis.get('bias', 'ANY'))
    translated_regime = regime_map.get(analysis.get('regime', 'NORMAL'), analysis.get('regime', 'NORMAL'))
         
    # Format economic releases
    releases = analysis.get('economic_releases', [])
    releases_str = "\n".join([f"• {r}" for r in releases]) if releases else "• Tidak ada rilis data penting baru"

    # 5. Send Telegram Notification from Cloud in Indonesian (GMT+7)
    optimal_method_str = analysis.get('optimal_method', 'Tidak ditentukan')
    tg_msg = (
        f"LAPORAN INTEL AWAN XEDY\n"
        f"Waktu: {local_now.strftime('%Y-%m-%d %H:%M:%S WIB')}\n\n"
        f"Berita Utama Teratas (Diterjemahkan):\n" + "\n".join(tg_news_list) + "\n\n"
        f"Rilis Data Kalender Ekonomi Terkini:\n" + releases_str + "\n\n"
        f"Keputusan Strategis Qwen AI:\n"
        f"• Harga Emas Saat Ini: ${gold_price:.2f}\n"
        f"• Target Harga Proyeksi: ${analysis.get('forecast_price_target', 0.0):.2f}\n"
        f"• Estimasi Durasi Waktu: {analysis.get('forecast_duration_hours', 0)} Jam\n"
        f"• Arah Bias: {translated_bias}\n"
        f"• Rezim Pasar: {translated_regime}\n"
        f"• Ambang Batas Sinyal: {analysis.get('optimal_confidence_threshold') * 100:.0f}%\n"
        f"• Maksimum Posisi Aktif: {analysis.get('optimal_max_op')}\n"
        f"• Saran Metode Optimal: {optimal_method_str}\n\n"
        f"Analisis & Dasar Pemikiran:\n{reasoning_id}"
    )
    
    if has_changed:
        send_telegram_notification(tg_token, tg_chat, tg_msg)
        print("Strategy change detected! Telegram notification sent.")
    else:
        print("No strategy changes detected. Telegram notification skipped to prevent spam.")
    print("Scraper completed successfully!")

if __name__ == "__main__":
    main()
