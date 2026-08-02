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
        print(f"Translation failed: {e}")
        return text

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

def get_qwen_analysis(api_key, news_text):
    if not api_key:
        return {"bias": "ANY", "regime": "NORMAL", "optimal_confidence_threshold": 0.68, "optimal_max_op": 4, "reasoning": "No API Key"}
        
    url = "https://api.aivene.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
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
        "  \"reasoning\": \"Brief explanation\"\n"
        "}"
    )
    payload = {
        "model": "qwen3.7-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the daily news summary:\n{news_text}"}
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
    
    # 1. Scrape Google News Gold, DXY, geopolitical, and macroeconomic feed
    google_url = 'https://news.google.com/rss/search?q=(gold+OR+xauusd+OR+dxy+OR+\"US+dollar\"+OR+\"treasury+yields\")+(war+OR+geopolitics+OR+conflict+OR+fed+OR+inflation+OR+nfp+OR+gdp+OR+cpi)&hl=en-US&gl=US&ceid=US:en'
    articles = scrape_rss(google_url)
    
    if not articles:
        print("No articles found.")
        return
        
    print(f"Scraped {len(articles)} headlines successfully.")
    
    # 2. Compile and translate headlines
    news_text = ""
    tg_news_list = []
    for idx, art in enumerate(articles[:5]):
        headline_en = art["title"]
        pub_t = art["pubDate"]
        
        # Translate headline to Indonesian
        headline_id = translate_to_id(headline_en)
        
        escaped_link = art['link'].replace("&", "&amp;")
        news_text += f"- {headline_en} ({pub_t})\n"
        tg_news_list.append(f"{idx+1}. <b><a href=\"{escaped_link}\">{headline_id}</a></b>\n   <i>Rilis: {pub_t} WIB</i>")
        
    # 3. Analyze with Qwen AI in the Cloud
    print("Calling Qwen AI for Macro Analysis...")
    analysis = get_qwen_analysis(api_key, news_text)
    print(f"Qwen Bias Result: {analysis.get('bias')}")
    
    # Translate Qwen's reasoning to Indonesian
    reasoning_en = analysis.get('reasoning', '')
    reasoning_id = translate_to_id(reasoning_en)
    
    # 4. Save results to JSON (timestamp in GMT+7 for local PC sync)
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    
    local_now = datetime.utcnow() + timedelta(hours=7)
    news_feed_data = {
        "generated_at": local_now.strftime("%Y-%m-%d %H:%M:%S WIB"),
        "news": articles[:5],
        "macro_analysis": analysis
    }
    
    with open(os.path.join(output_dir, "news_feed.json"), "w") as f:
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
        f"• <b>Arah Bias</b>: <code>{translated_bias}</code>\n"
        f"• <b>Rezim Pasar</b>: <code>{translated_regime}</code>\n"
        f"• <b>Ambang Batas Sinyal</b>: <code>{analysis.get('optimal_confidence_threshold') * 100:.0f}%</code>\n"
        f"• <b>Maksimum Posisi Aktif</b>: <code>{analysis.get('optimal_max_op')}</code>\n"
        f"• <b>Saran Metode Optimal</b>: <code>{optimal_method_str}</code>\n\n"
        f"<b>💡 Analisis & Dasar Pemikiran:</b>\n<i>{reasoning_id}</i>"
    )
    
    send_telegram_notification(tg_token, tg_chat, tg_msg)
    print("Scraper completed successfully!")

if __name__ == "__main__":
    main()
