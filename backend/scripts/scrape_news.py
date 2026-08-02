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

def get_live_gold_price():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            return float(price)
    except Exception as e:
        print(f"Failed to fetch gold price from Yahoo: {e}")
        return 0.0

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

def get_qwen_analysis(api_key, news_text, gold_price):
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

    gold_price_str = f"\nThe current live market price of XAUUSD is: ${gold_price:.2f}" if gold_price > 0 else ""

    system_prompt = (
        "You are the Chief Strategist AI (Qwen AI) for the XEDY algorithmic trading platform.\n"
        "Analyze the news headlines, identify any recent US economic calendar data releases (like GDP, PCE, CPI, NFP) mentioned, and decide the macro trading bias.\n"
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
        "  \"reasoning\": \"Brief explanation in English\"\n"
        "}"
    )
    payload = {
        "model": "qwen3.7-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the daily news summary:\n{news_text}\n{gold_price_str}\n{memory_summary}\n{accuracy_summary}"}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30.0) as r:
            res_json = json.loads(r.read().decode("utf-8"))
            content = res_json['choices'][0]['message']['content'].strip()
            return json.loads(content)
    except Exception as e:
        print(f"Error calling Qwen API: {e}")
        return {"bias": "ANY", "regime": "NORMAL", "optimal_confidence_threshold": 0.68, "optimal_max_op": 4, "reasoning": f"API Error: {e}"}

def main():
    api_key = os.getenv("AIVENE_API_KEY", "")
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_chat = os.getenv("TELEGRAM_ADMIN_ID", "")
    
    print("Starting Cloud News Scraper...")
    
    # Fetch live gold price at run time
    gold_price = get_live_gold_price()
    print(f"Current live XAUUSD price fetched: ${gold_price:.2f}")
    
    # 1. Scrape Google News Gold, DXY, geopolitical, and macroeconomic feed
    google_url = 'https://news.google.com/rss/search?q=(gold+OR+xauusd+OR+dxy+OR+\"US+dollar\"+OR+\"treasury+yields\")+(war+OR+geopolitics+OR+conflict+OR+fed+OR+inflation+OR+nfp+OR+gdp+OR+cpi)&hl=en-US&gl=US&ceid=US:en'
    articles = scrape_rss(google_url)
    
    if not articles:
        print("No articles found.")
        return
        
    print(f"Scraped {len(articles)} headlines successfully.")
    
    # Filter and weight articles to last 48 hours (GMT+7)
    local_now = datetime.utcnow() + timedelta(hours=7)
    forty_eight_hours_ago = local_now - timedelta(hours=48)
    twenty_four_hours_ago = local_now - timedelta(hours=24)
    weighted_articles = []
    
    for art in articles:
        try:
            art_dt = datetime.strptime(art["pubDate"], "%Y-%m-%d %H:%M:%S")
            if art_dt >= forty_eight_hours_ago:
                age_hours = int((local_now - art_dt).total_seconds() / 3600)
                if art_dt >= twenty_four_hours_ago:
                    weight = "100% (FRESH)"
                    weight_label = "BARU/KUAT"
                else:
                    weight = "40% (WEAK / DECAYED)"
                    weight_label = "LAMA/LEMAH"
                
                art["weight"] = weight
                art["weight_label"] = weight_label
                art["age_hours"] = age_hours
                weighted_articles.append(art)
        except Exception:
            # Fallback if parse fails
            art["weight"] = "100% (FRESH)"
            art["weight_label"] = "BARU/KUAT"
            art["age_hours"] = 0
            weighted_articles.append(art)
            
    # Fallback to general list if no news in last 48h
    if not weighted_articles:
        print("No new articles in last 48 hours. Falling back to most recent headlines.")
        weighted_articles = articles[:12]
        for art in weighted_articles:
            art["weight"] = "100% (FRESH)"
            art["weight_label"] = "BARU/KUAT"
            art["age_hours"] = 0
    else:
        # Sort by age (newest first)
        weighted_articles = sorted(weighted_articles, key=lambda x: x.get("age_hours", 0))[:12]
        print(f"Filtered to {len(weighted_articles)} headlines from the last 48 hours.")
        
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
        w_badge = "🔴" if "WEAK" in weight else "🟢"
        tg_news_list.append(f"{idx+1}. {w_badge} <b><a href=\"{escaped_link}\">{headline_id}</a></b>\n   <i>Rilis: {pub_t} WIB ({art.get('weight_label')})</i>")
        
    # 3. Analyze with Qwen AI in the Cloud
    print("Calling Qwen AI for Macro Analysis...")
    analysis = get_qwen_analysis(api_key, news_text, gold_price)
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
    releases_str = "\n".join([f"• <code>{r}</code>" for r in releases]) if releases else "• <code>Tidak ada rilis data penting baru</code>"

    # 5. Send Telegram Notification from Cloud in Indonesian (GMT+7)
    optimal_method_str = analysis.get('optimal_method', 'Tidak ditentukan')
    tg_msg = (
        f"<b>📰 LAPORAN INTEL AWAN XEDY</b>\n"
        f"<i>Waktu: {local_now.strftime('%Y-%m-%d %H:%M:%S WIB')}</i>\n\n"
        f"<b>🔍 Berita Utama Teratas (Diterjemahkan):</b>\n" + "\n".join(tg_news_list) + "\n\n"
        f"<b>📅 Rilis Data Kalender Ekonomi Terkini:</b>\n" + releases_str + "\n\n"
        f"<b>🧠 Keputusan Strategis Qwen AI:</b>\n"
        f"• <b>Harga Emas Saat Ini</b>: <code>${gold_price:.2f}</code>\n"
        f"• <b>Target Harga Proyeksi</b>: <code>${analysis.get('forecast_price_target', 0.0):.2f}</code>\n"
        f"• <b>Estimasi Durasi Waktu</b>: <code>{analysis.get('forecast_duration_hours', 0)} Jam</code>\n"
        f"• <b>Arah Bias</b>: <code>{translated_bias}</code>\n"
        f"• <b>Rezim Pasar</b>: <code>{translated_regime}</code>\n"
        f"• <b>Ambang Batas Sinyal</b>: <code>{analysis.get('optimal_confidence_threshold') * 100:.0f}%</code>\n"
        f"• <b>Maksimum Posisi Aktif</b>: <code>{analysis.get('optimal_max_op')}</code>\n"
        f"• <b>Saran Metode Optimal</b>: <code>{optimal_method_str}</code>\n\n"
        f"<b>💡 Analisis & Dasar Pemikiran:</b>\n<i>{reasoning_id}</i>"
    )
    
    if has_changed:
        send_telegram_notification(tg_token, tg_chat, tg_msg)
        print("Strategy change detected! Telegram notification sent.")
    else:
        print("No strategy changes detected. Telegram notification skipped to prevent spam.")
    print("Scraper completed successfully!")

if __name__ == "__main__":
    main()
