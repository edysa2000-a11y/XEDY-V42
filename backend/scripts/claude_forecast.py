import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import email.utils
from dotenv import load_dotenv

# Load local system environment configuration
load_dotenv()

def get_live_multi_asset_prices():
    prices = {"XAUUSD": 0.0, "USOIL": 0.0, "DXY": 0.0, "US10Y": 0.0}
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
        with urllib.request.urlopen(req_tv, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("data"):
                for item in data["data"]:
                    ticker = item["s"]
                    close_price = float(item["d"][0])
                    if "XAUUSD" in ticker: prices["XAUUSD"] = close_price
                    elif "USOIL" in ticker: prices["USOIL"] = close_price
                    elif "DXY" in ticker: prices["DXY"] = close_price
                    elif "US10Y" in ticker: prices["US10Y"] = close_price
    except Exception as e:
        print(f"TradingView fetch failed: {e}")
        
    # Yahoo Fallbacks
    try:
        if prices["XAUUSD"] == 0.0:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/PAXG-USD?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
                prices["XAUUSD"] = float(data['chart']['result'][0]['meta']['regularMarketPrice'])
    except Exception as e:
        print(f"Yahoo fallback failed: {e}")
    return prices

def scrape_rss(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15.0) as r:
            xml_data = r.read()
            root = ET.fromstring(xml_data)
            articles = []
            for item in root.findall('.//item')[:12]:
                title = item.find('title')
                pub_date = item.find('pubDate')
                link = item.find('link')
                if title is not None:
                    raw_pub = pub_date.text if pub_date is not None else ""
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
        print(f"Error RSS: {e}")
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

def get_claude_analysis(api_key, news_text, prices):
    url = "https://api.aivene.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    gold_price = prices.get("XAUUSD", 0.0)
    prices_str = (
        f"Gold (XAUUSD): ${gold_price:.2f}\n"
        f"Crude Oil (USOIL): ${prices.get('USOIL', 0.0):.2f}\n"
        f"DXY Index: {prices.get('DXY', 0.0):.2f}\n"
        f"US 10Y Treasury Yield: {prices.get('US10Y', 0.0):.2f}%\n"
    )

    system_prompt = (
        "You are the Lead Strategist AI (Claude 3.5 Sonnet) for the XEDY algorithmic trading platform.\n"
        "Your task is to analyze the daily news feed and intermarket asset prices to produce a precise multi-timeframe HLC forecast.\n"
        "Respond ONLY with a valid JSON matching this exact schema (no markdown formatting, no code fences):\n"
        "{\n"
        "  \"bias\": \"BUY_ONLY\" | \"SELL_ONLY\" | \"ANY\" | \"WAIT\",\n"
        "  \"regime\": \"NORMAL\" | \"HIGH_NEWS\" | \"SIDEWAYS\",\n"
        "  \"optimal_confidence_threshold\": 0.75,\n"
        "  \"optimal_max_op\": 3,\n"
        "  \"optimal_method\": \"Opsi 5: Scalping 1:1\",\n"
        "  \"economic_releases\": [\"Brief economic event description and impact in INDONESIAN\"],\n"
        "  \"forecast_price_target\": float,\n"
        "  \"forecast_duration_hours\": 24,\n"
        "  \"forecast_high_24h\": float,\n"
        "  \"forecast_low_24h\": float,\n"
        "  \"forecast_close_24h\": float,\n"
        "  \"forecast_reasoning_id\": \"General brief overview in INDONESIAN\",\n"
        "  \"forecasts\": {\n"
        "    \"1d\": {\n"
        "      \"open\": float,\n"
        "      \"high\": float,\n"
        "      \"low\": float,\n"
        "      \"close\": float,\n"
        "      \"reasoning_id\": \"1-day HLC analysis in INDONESIAN\"\n"
        "    },\n"
        "    \"1w\": {\n"
        "      \"open\": float,\n"
        "      \"high\": float,\n"
        "      \"low\": float,\n"
        "      \"close\": float,\n"
        "      \"reasoning_id\": \"1-week HLC analysis in INDONESIAN\"\n"
        "    },\n"
        "    \"2w\": {\n"
        "      \"open\": float,\n"
        "      \"high\": float,\n"
        "      \"low\": float,\n"
        "      \"close\": float,\n"
        "      \"reasoning_id\": \"2-week HLC analysis in INDONESIAN\"\n"
        "    }\n"
        "  },\n"
        "  \"reasoning\": \"Brief technical overview in English\"\n"
        "}"
    )

    payload = {
        "model": "claude-3-5-sonnet", # Direct model override for Claude analysis
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"News headlines:\n{news_text}\nMarket values:\n{prices_str}"}
        ],
        "temperature": 0.15,
        "response_format": {"type": "json_object"}
    }
    
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45.0) as r:
            res_json = json.loads(r.read().decode("utf-8"))
            content = res_json['choices'][0]['message']['content'].strip()
            cleaned_content = clean_json_string(content)
            return json.loads(cleaned_content)
    except Exception as e:
        print(f"Claude API failed: {e}")
        return {}

def main():
    api_key = os.getenv("AIVENE_API_KEY", "")
    if not api_key:
        print("API Key not found.")
        return
        
    prices = get_live_multi_asset_prices()
    google_url = 'https://news.google.com/rss/search?q=(gold+OR+xauusd+OR+dxy+OR+trump+OR+tariff)+(war+OR+geopolitics+OR+fed+OR+inflation+OR+nfp+OR+cpi)&hl=en-US&gl=US&ceid=US:en'
    articles = scrape_rss(google_url)
    
    news_text = ""
    for art in articles[:10]:
        news_text += f"- {art['title']} ({art['pubDate']})\n"
        
    print("Requesting Claude AI Forecast...")
    analysis = get_claude_analysis(api_key, news_text, prices)
    if not analysis:
        return
        
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    news_feed_path = os.path.join(output_dir, "news_feed.json")
    
    local_now = datetime.utcnow() + timedelta(hours=7)
    news_feed_data = {
        "generated_at": local_now.strftime("%Y-%m-%d %H:%M:%S WIB"),
        "news": articles[:10],
        "macro_analysis": analysis
    }
    
    with open(news_feed_path, "w") as f:
        json.dump(news_feed_data, f, indent=2)
    print("Claude daily forecast updated successfully.")

if __name__ == "__main__":
    main()
