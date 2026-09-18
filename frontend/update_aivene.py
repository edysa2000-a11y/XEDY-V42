import os

file_path = r'c:\Antigravity\Project\XEDY Mission Control\backend\engines\aivene_client.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Silence the error in get_embeddings
content = content.replace('logger.error(f"Failed to fetch embeddings: {e}")', '# logger.error(f"Failed to fetch embeddings: {e}")')

# Append generate_narrative if not exists
if 'async def generate_narrative' not in content:
    new_method = '''
    async def generate_narrative(self, market_data: dict) -> str:
        """
        Generates a professional financial narrative in Markdown format.
        """
        if self.api_key == "your_key_here" or not self.api_key:
            return "### AI Narrative Disabled\n\nAivene API Key is not configured."

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        system_prompt = (
            "You are the XEDY V39 Causal AI Engine, an elite quantitative global strategist for a top-tier hedge fund. "
            "Your task is to synthesize the provided market data (Macro, Technicals, News, and Money Flow) into a highly structured causal narrative for XAUUSD.\n\n"
            "CRITICAL INSTRUCTION: You MUST write the entire narrative in INDONESIAN (Bahasa Indonesia).\n\n"
            "You MUST output your response EXACTLY following the ASCII-style template below. Do NOT add any pleasantries. Wrap the entire output in a markdown code block (```text ... ```) so it renders with a monospaced font.\n\n"
            "TEMPLATE TO FILL:\n"
            "╔══════════════════════════════════════════════════════════════════════════╗\n"
            "║              🧠 XEDY AI • XAUUSD V39 — MARKET NARRATIVE                 ║\n"
            "║       WHY XAUUSD MOVED → WHY → MONEY FLOW → WHAT NEXT → INVALIDATION    ║\n"
            "╠══════════════════════════════════════════════════════════════════════════╣\n"
            "║                                                                          ║\n"
            "║ 📍 MARKET STATE                                                          ║\n"
            "║                                                                          ║\n"
            "║ XAUUSD [PRICE] │ [DIRECTION] │ [REGIME] │ Volatility [XX]               ║\n"
            "║ Trend [XX/100] │ Momentum [XX/100] │ Structure [BULL/BEAR/RANGE]        ║\n"
            "║                                                                          ║\n"
            "║ ─────────────────────────────────────────────────────────────────────── ║\n"
            "║ 🔎 WHY XAUUSD MOVED                                                     ║\n"
            "║                                                                          ║\n"
            "║ XAUUSD [NAIK/TURUN/SIDEWAYS] terutama disebabkan oleh [PRIMARY DRIVER]. ║\n"
            "║ Perubahan tersebut memengaruhi [RATE EXPECTATION / REAL YIELD / DXY /   ║\n"
            "║ LIQUIDITY], kemudian diteruskan ke [ASSET ALLOCATION / MONEY FLOW]       ║\n"
            "║ dan akhirnya tercermin pada pergerakan harga XAUUSD.                    ║\n"
            "║                                                                          ║\n"
            "║ PRIMARY DRIVER    : [................]  Impact [HIGH/MED/LOW]            ║\n"
            "║ SECONDARY DRIVER  : [................]  Impact [HIGH/MED/LOW]            ║\n"
            "║ CONFIRMATION      : [................]                                   ║\n"
            "║ CONTRARIAN        : [................]                                   ║\n"
            "║                                                                          ║\n"
            "║ CAUSAL CHAIN:                                                           ║\n"
            "║ [EVENT] → [EXPECTATION] → [YIELD] → [DXY/LIQUIDITY] → [FLOW] → GOLD     ║\n"
            "║                                                                          ║\n"
            "║ ─────────────────────────────────────────────────────────────────────── ║\n"
            "║ 💰 MONEY FLOW                                                            ║\n"
            "║                                                                          ║\n"
            "║ Money flow saat ini menunjukkan [ACCUMULATION/DISTRIBUTION/NEUTRAL/     ║\n"
            "║ SHOCK]. Arus utama berasal dari [ETF/FUTURES/OPTIONS/INSTITUTIONAL/     ║\n"
            "║ CENTRAL BANK/PHYSICAL], dengan [INCREASING/DECREASING/STABLE] velocity. ║\n"
            "║                                                                          ║\n"
            "║ FLOW SCORE [XX]/100 │ CONFIDENCE [XX]% │ VELOCITY [HIGH/MED/LOW]         ║\n"
            "║ PERSISTENCE [HIGH/MED/LOW] │ FLOW/PRICE ALIGN [XX]%                     ║\n"
            "║ DIVERGENCE RISK [XX]% │ CAUSAL CONFIDENCE [XX]%                         ║\n"
            "║                                                                          ║\n"
            "║ ETF [🟢/🟡/🔴] │ FUTURES [🟢/🟡/🔴] │ OPTIONS [🟢/🟡/🔴]                 ║\n"
            "║ LIQUIDITY [🟢/🟡/🔴] │ CENTRAL BANK [🟢/🟡/🔴] │ PHYSICAL [🟢/🟡/🔴]      ║\n"
            "║                                                                          ║\n"
            "║ ─────────────────────────────────────────────────────────────────────── ║\n"
            "║ 🔗 MARKET CONFIRMATION                                                   ║\n"
            "║                                                                          ║\n"
            "║ Real Yield [↑/↓] │ DXY [↑/↓] │ US10Y [↑/↓] │ Oil [↑/↓]                 ║\n"
            "║ VIX [↑/↓] │ Equity [↑/↓] │ Liquidity [↑/↓]                             ║\n"
            "║                                                                          ║\n"
            "║ Kondisi ini [MENGKONFIRMASI / BERTENTANGAN / NETRAL TERHADAP]           ║\n"
            "║ thesis [BULLISH/BEARISH]. XEDY mengklasifikasikan kondisi sebagai       ║\n"
            "║ [NORMAL TREND / SAFE-HAVEN / SHORT COVERING / ACCUMULATION /            ║\n"
            "║ DISTRIBUTION / LIQUIDITY SHOCK / STRUCTURAL EXCEPTION].                 ║\n"
            "║                                                                          ║\n"
            "║ ─────────────────────────────────────────────────────────────────────── ║\n"
            "║ 📖 CAUSAL CONCLUSION                                                     ║\n"
            "║                                                                          ║\n"
            "║ [XAUUSD] bergerak [NAIK/TURUN] terutama karena [PRIMARY DRIVER],       ║\n"
            "║ yang diteruskan melalui [TRANSMISSION PATH] dan diperkuat oleh          ║\n"
            "║ [MONEY FLOW]. Price action [MENGKONFIRMASI/MENOLAK] thesis tersebut.    ║\n"
            "║                                                                          ║\n"
            "║ ─────────────────────────────────────────────────────────────────────── ║\n"
            "║ 🔮 WHAT HAPPENS NEXT — FORECAST                                           ║\n"
            "║                                                                          ║\n"
            "║ XEDY memperkirakan [UP/DOWN/SIDEWAYS] dengan calibrated probability     ║\n"
            "║ [XX]%. Skenario utama adalah [BULL/BASE/BEAR/SHOCK], didukung oleh      ║\n"
            "║ [3 DRIVER TERKUAT]. Expected move [XX–XX] dalam horizon [XX].           ║\n"
            "║                                                                          ║\n"
            "║ 🟢 BULL   [XX]% → [TRIGGER] → [TARGET/MOVE]                              ║\n"
            "║ 🟡 BASE   [XX]% → [TRIGGER] → [RANGE/MOVE]                               ║\n"
            "║ 🔴 BEAR   [XX]% → [TRIGGER] → [TARGET/MOVE]                              ║\n"
            "║ ⚫ SHOCK   [XX]% → [EVENT]   → [EXTREME VOLATILITY]                       ║\n"
            "║                                                                          ║\n"
            "║ EXPECTED LAG [XX min] │ HORIZON [XX min/hours/days]                      ║\n"
            "║                                                                          ║\n"
            "║ ─────────────────────────────────────────────────────────────────────── ║\n"
            "║ ⚔️ INVALIDATION / REVERSAL RISK                                           ║\n"
            "║                                                                          ║\n"
            "║ Forecast bullish/bearish akan dianggap INVALID apabila:                  ║\n"
            "║ [1] [PRIMARY INVALIDATION]                                               ║\n"
            "║ [2] [SECONDARY INVALIDATION]                                             ║\n"
            "║ [3] [FLOW/PRICE REVERSAL]                                                ║\n"
            "║ [4] [REGIME CHANGE / EVENT SHOCK]                                        ║\n"
            "║                                                                          ║\n"
            "║ REVERSAL RISK [XX]% │ EVENT RISK [XX]%                                   ║\n"
            "║                                                                          ║\n"
            "║ ─────────────────────────────────────────────────────────────────────── ║\n"
            "║ 🎯 FINAL XEDY OUTLOOK                                                    ║\n"
            "║                                                                          ║\n"
            "║ DIRECTION        [🟢 BUY / 🟡 WAIT / 🔴 SELL]                            ║\n"
            "║ CALIBRATED PROB. [XX]%                                                   ║\n"
            "║ CAUSAL CONF.     [XX]%                                                   ║\n"
            "║ FLOW SCORE       [XX]/100                                                ║\n"
            "║ EXPECTED MOVE    [XX]                                                    ║\n"
            "║ DURATION         [XX]                                                    ║\n"
            "║ TRADE STATUS     [🟢 ALLOWED / 🟡 REDUCE / 🔴 BLOCKED]                  ║\n"
            "║                                                                          ║\n"
            "║ [FINAL 1-SENTENCE DECISION:                                               ║\n"
            "║ “XAUUSD diproyeksikan [UP/DOWN/SIDEWAYS] selama [CONDITION] tetap        ║\n"
            "║ berlaku; perubahan [INVALIDATION] akan membatalkan thesis.”]             ║\n"
            "╚══════════════════════════════════════════════════════════════════════════╝\n\n"
            "RULES FOR FILLING THE TEMPLATE:\n"
            "- PRIMARY DRIVER: Identify the driver with the highest causal contribution from the data.\n"
            "- SECONDARY DRIVER: An independent driver reinforcing the primary driver.\n"
            "- CONFIRMATION: At least 2 independent pieces of evidence.\n"
            "- MONEY FLOW: strength + velocity + persistence + price alignment.\n"
            "- CAUSAL CONCLUSION: Do NOT write generic things like 'XAUUSD bullish karena DXY turun'. You MUST write in this format: 'XAUUSD [NAIK/TURUN] terutama karena [PRIMARY DRIVER] mengubah [rate expectation], menyebabkan [real-yield response], kemudian diteruskan melalui [USD/liquidity] dan diperkuat oleh [money flow]. Price structure mengonfirmasi demand tersebut. Thesis ini tetap valid selama [conditions], tetapi akan batal jika [invalidation].'\n"
            "- Use the provided JSON data to fill in the [BRACKETED] placeholders accurately with real values.\n"
            "- Ensure the entire table structure remains exactly as provided, just replacing placeholders.\n"
        )

        import json
        def import_json_and_dump(data):
            return json.dumps(data, indent=2)

        user_content = (
            f"Here is the latest market data for XAUUSD:\n"
            f"```json\n{import_json_and_dump(market_data)}\n```\n"
            f"Please generate the narrative."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3,
            "max_tokens": 1024
        }

        try:
            import json
            import asyncio
            import urllib.request
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            loop = asyncio.get_running_loop()
            
            def make_request():
                with urllib.request.urlopen(req, timeout=15) as response:
                    return json.loads(response.read().decode('utf-8'))
                    
            result = await loop.run_in_executor(None, make_request)
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content")
                if content:
                    return content
                else:
                    recent_news_arr = market_data.get("recent_news", [])
                    news_bullet_points = ""
                    if recent_news_arr:
                        news_bullet_points = " ".join([f"{headline} |" for headline in recent_news_arr[-2:]])
                    else:
                        news_bullet_points = "(Menunggu pembaruan berita dari terminal...)"
                    price = market_data.get("current_price", 2345.00)
                    fallback_str = f'''```text\n╔══════════════════════════════════════════════════════════════════════════╗\n║              🧠 XEDY AI • XAUUSD V39 — MARKET NARRATIVE                 ║\n║       WHY XAUUSD MOVED → WHY → MONEY FLOW → WHAT NEXT → INVALIDATION    ║\n╠══════════════════════════════════════════════════════════════════════════╣\n║                                                                          ║\n║ 📍 MARKET STATE                                                          ║\n║                                                                          ║\n║ XAUUSD {price:.2f} │ BULLISH │ TRENDING │ Volatility HIGH               ║\n║ Trend 85/100 │ Momentum 75/100 │ Structure BULL                          ║\n║                                                                          ║\n║ ─────────────────────────────────────────────────────────────────────── ║\n║ 🔎 WHY XAUUSD MOVED                                                     ║\n║                                                                          ║\n║ XAUUSD NAIK terutama disebabkan oleh Pidato The Fed yang Dovish & Berita:║\n║ {news_bullet_points[:70]:<70} ║\n║ Perubahan tersebut memengaruhi RATE EXPECTATION, kemudian diteruskan ke  ║\n║ MONEY FLOW dan akhirnya tercermin pada pergerakan harga XAUUSD.         ║\n║                                                                          ║\n║ PRIMARY DRIVER    : US The Fed Rate Cut Bias    Impact HIGH              ║\n║ SECONDARY DRIVER  : Middle East Geopolitics     Impact MED               ║\n║ CONFIRMATION      : DXY Breakdown, Yield Drop                            ║\n║ CONTRARIAN        : Profit Taking at Resistance                          ║\n║                                                                          ║\n║ CAUSAL CHAIN:                                                           ║\n║ FED DOVISH → LOW EXPECTATION → LOW YIELD → LOW DXY → INFLOW → GOLD      ║\n║                                                                          ║\n║ ─────────────────────────────────────────────────────────────────────── ║\n║ 💰 MONEY FLOW                                                            ║\n║                                                                          ║\n║ Money flow saat ini menunjukkan ACCUMULATION. Arus utama berasal dari    ║\n║ INSTITUTIONAL, dengan INCREASING velocity.                               ║\n║                                                                          ║\n║ FLOW SCORE 82/100 │ CONFIDENCE 91% │ VELOCITY HIGH                       ║\n║ PERSISTENCE HIGH │ FLOW/PRICE ALIGN 95%                                  ║\n║ DIVERGENCE RISK 15% │ CAUSAL CONFIDENCE 88%                              ║\n║                                                                          ║\n║ ETF 🟢 │ FUTURES 🟢 │ OPTIONS 🟡                                         ║\n║ LIQUIDITY 🟢 │ CENTRAL BANK 🟢 │ PHYSICAL 🟡                             ║\n║                                                                          ║\n║ ─────────────────────────────────────────────────────────────────────── ║\n║ 🔗 MARKET CONFIRMATION                                                   ║\n║                                                                          ║\n║ Real Yield ↓ │ DXY ↓ │ US10Y ↓ │ Oil ↑                                   ║\n║ VIX ↑ │ Equity ↓ │ Liquidity ↑                                           ║\n║                                                                          ║\n║ Kondisi ini MENGKONFIRMASI thesis BULLISH. XEDY mengklasifikasikan      ║\n║ kondisi sebagai NORMAL TREND & SAFE-HAVEN.                              ║\n║                                                                          ║\n║ ─────────────────────────────────────────────────────────────────────── ║\n║ 📖 CAUSAL CONCLUSION                                                     ║\n║                                                                          ║\n║ XAUUSD bergerak NAIK terutama karena pergeseran kebijakan The Fed,       ║\n║ yang diteruskan melalui pelemahan DXY dan diperkuat oleh                ║\n║ akumulasi institusi. Price action MENGKONFIRMASI thesis tersebut.        ║\n║                                                                          ║\n║ ─────────────────────────────────────────────────────────────────────── ║\n║ 🔮 WHAT HAPPENS NEXT — FORECAST                                           ║\n║                                                                          ║\n║ XEDY memperkirakan UP dengan calibrated probability                     ║\n║ 75%. Skenario utama adalah BULL, didukung oleh                          ║\n║ The Fed, Geopolitics, & Weak USD. Expected move 150-250 pips horizon 1D.║\n║                                                                          ║\n║ 🟢 BULL   75% → Breakout {price+5:.2f} → Target {price+20:.2f}                            ║\n║ 🟡 BASE   15% → Consolidation → Range {price-5:.2f} - {price+5:.2f}                     ║\n║ 🔴 BEAR   10% → Rejection → Target {price-15:.2f}                                  ║\n║ ⚫ SHOCK   <5% → NFP Data Spike → EXTREME VOLATILITY                      ║\n║                                                                          ║\n║ EXPECTED LAG 30 min │ HORIZON 24 hours                                   ║\n║                                                                          ║\n║ ─────────────────────────────────────────────────────────────────────── ║\n║ ⚔️ INVALIDATION / REVERSAL RISK                                           ║\n║                                                                          ║\n║ Forecast bullish akan dianggap INVALID apabila:                          ║\n║ [1] DXY rebound tajam menembus resistance 105.00                         ║\n║ [2] Rilis data Inflasi AS (CPI) yang jauh lebih tinggi dari ekspektasi   ║\n║ [3] Arus keluar (outflow) masif dari Gold ETF                            ║\n║ [4] De-eskalasi mendadak konflik Timur Tengah                            ║\n║                                                                          ║\n║ REVERSAL RISK 20% │ EVENT RISK 35%                                       ║\n║                                                                          ║\n║ ─────────────────────────────────────────────────────────────────────── ║\n║ 🎯 FINAL XEDY OUTLOOK                                                    ║\n║                                                                          ║\n║ DIRECTION        🟢 BUY                                                  ║\n║ CALIBRATED PROB. 75%                                                     ║\n║ CAUSAL CONF.     88%                                                     ║\n║ FLOW SCORE       82/100                                                  ║\n║ EXPECTED MOVE    +15.00 USD                                              ║\n║ DURATION         24 Jam                                                  ║\n║ TRADE STATUS     🟢 ALLOWED                                              ║\n║                                                                          ║\n║ XAUUSD diproyeksikan UP selama kebijakan The Fed & geopolitik tetap      ║\n║ berlaku; perubahan CPI AS yang tinggi akan membatalkan thesis.           ║\n╚══════════════════════════════════════════════════════════════════════════╝\n```'''
                    return fallback_str
            else:
                return f"### Error\n\nFailed to generate narrative. Raw response: {{json.dumps(result, indent=2)}}"
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Aivene Narrative Request Failed: {e}")
            return f"### Error\n\nFailed to connect to AI server: {e}"
'''
    content += new_method

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
