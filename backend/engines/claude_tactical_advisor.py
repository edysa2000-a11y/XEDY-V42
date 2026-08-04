import os
import urllib.request
import json
import logging
import asyncio
import time

logger = logging.getLogger("xedy.claude_advisor")


class ClaudeTacticalAdvisor:
    """
    Claude AI Tactical Advisor Engine.
    
    Provides precise BUY/SELL instructions with TP targets using multi-layer analysis:
    1. Technical Analysis (RSI, MACD, EMA, ATR, VWAP)
    2. Smart Money Concepts (Liquidity Sweeps, Order Blocks, FVG)
    3. Intermarket Analysis (DXY, US10Y, Oil correlation)
    4. News Sentiment Analysis
    5. Recovery Scenarios if primary target fails
    
    Target: ALWAYS PROFIT. If primary TP fails, execute recovery plan.
    """
    
    def __init__(self):
        self.api_key = os.getenv("AIVENE_API_KEY", "")
        self.base_url = os.getenv("AIVENE_BASE_URL", "https://api.aivene.com/v1").rstrip("/")
        self.model = "claude-3-5-sonnet"
        
        # Active instruction state
        self.active_instruction = None
        self.instruction_timestamp = 0
        self.instruction_ttl = 3600  # 1 hour validity
        self.last_call_time = 0
        self.call_cooldown = 300  # 5 minutes between calls
        
    async def get_tactical_instruction(self, technicals: dict, news_text: str, 
                                        open_positions: list, closed_trades_today: list,
                                        current_price: float, atr: float) -> dict:
        """
        Call Claude 3.5 Sonnet to get a tactical BUY/SELL instruction
        with multi-analysis TP targets and mandatory recovery scenarios.
        """
        
        # Cooldown check
        now = time.time()
        if now - self.last_call_time < self.call_cooldown:
            remaining = int(self.call_cooldown - (now - self.last_call_time))
            logger.info(f"Claude Advisor: Cooldown active, {remaining}s remaining. Using cached instruction.")
            if self.active_instruction and (now - self.instruction_timestamp) < self.instruction_ttl:
                return self.active_instruction
            return {"action": "HOLD", "reasoning": "Cooldown active, no cached instruction available."}
        
        if not self.api_key or self.api_key == "your_key_here":
            logger.warning("Claude Advisor: API key not configured.")
            return {"action": "HOLD", "reasoning": "API key not configured."}
        
        # Build position context
        pos_context = "Tidak ada posisi aktif."
        if open_positions:
            pos_lines = []
            for p in open_positions:
                p_type = "BUY" if p.get("type") == 0 else "SELL"
                pos_lines.append(
                    f"  - {p_type} {p.get('volume', 0)} lot @ {p.get('price_open', 0):.2f} "
                    f"(Floating: ${p.get('profit', 0):.2f})"
                )
            pos_context = "Posisi aktif saat ini:\n" + "\n".join(pos_lines)
            
        # Build today's PnL context
        today_pnl = sum(t.get("profit", 0) for t in closed_trades_today)
        today_wins = sum(1 for t in closed_trades_today if t.get("profit", 0) > 0)
        today_losses = sum(1 for t in closed_trades_today if t.get("profit", 0) < 0)
        pnl_context = (
            f"Performa hari ini: {len(closed_trades_today)} trade, "
            f"{today_wins} Win / {today_losses} Loss, "
            f"Total PnL: ${today_pnl:.2f}"
        )
        
        system_prompt = (
            "Kamu adalah Claude Tactical Advisor — AI analis senior untuk platform trading XEDY.\n"
            "Tugasmu adalah memberikan INSTRUKSI TRADING yang PRESISI dan WAJIB MENGHASILKAN PROFIT.\n\n"
            "ATURAN WAJIB:\n"
            "1. Setiap instruksi HARUS memiliki target profit (TP) yang realistis berdasarkan analisa multi-layer.\n"
            "2. Stop Loss (SL) WAJIB lebih kecil dari TP dengan rasio minimal 1:2.\n"
            "3. Jika target utama gagal, WAJIB sertakan skenario pemulihan (recovery) agar tetap profit.\n"
            "4. Analisa WAJIB mencakup: Technical, Smart Money, Intermarket, dan Sentiment.\n"
            "5. Jika kondisi tidak mendukung entry, instruksikan HOLD dan jelaskan alasannya.\n\n"
            "Respond ONLY dengan valid JSON (tanpa markdown/code fences) sesuai schema:\n"
            "{\n"
            '  "action": "BUY" | "SELL" | "HOLD",\n'
            '  "entry_price": float,\n'
            '  "tp_primary": float,\n'
            '  "tp_conservative": float,\n'
            '  "sl_price": float,\n'
            '  "lot_size_pct": float (0.30 = 30% of base lot),\n'
            '  "confidence": float (0-100),\n'
            '  "analysis": {\n'
            '    "technical": "Analisa RSI, MACD, EMA, ATR dalam Bahasa Indonesia",\n'
            '    "smart_money": "Analisa Liquidity Sweep, Order Block, FVG dalam Bahasa Indonesia",\n'
            '    "intermarket": "Analisa korelasi DXY, US10Y, Oil dalam Bahasa Indonesia",\n'
            '    "sentiment": "Analisa sentimen berita dan geopolitik dalam Bahasa Indonesia"\n'
            '  },\n'
            '  "recovery_scenarios": [\n'
            '    {\n'
            '      "trigger": "Deskripsi kondisi pemicu skenario recovery",\n'
            '      "action": "BUY" | "SELL" | "HEDGE" | "AVERAGE",\n'
            '      "target_price": float,\n'
            '      "lot_adjustment": float,\n'
            '      "explanation": "Penjelasan strategi recovery dalam Bahasa Indonesia"\n'
            '    }\n'
            '  ],\n'
            '  "reasoning": "Ringkasan keputusan dan alasan utama dalam Bahasa Indonesia"\n'
            "}"
        )
        
        user_content = (
            f"=== DATA TEKNIKAL ===\n"
            f"Harga saat ini: ${current_price:.2f}\n"
            f"ATR (14): ${atr:.2f}\n"
            f"{json.dumps(technicals, indent=2)}\n\n"
            f"=== POSISI & PERFORMA ===\n"
            f"{pos_context}\n"
            f"{pnl_context}\n\n"
            f"=== BERITA TERKINI ===\n"
            f"{news_text}\n\n"
            f"Berikan instruksi trading PRESISI dengan target WAJIB PROFIT. "
            f"Sertakan minimal 2 skenario recovery jika target utama gagal."
        )
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.15,
            "response_format": {"type": "json_object"}
        }
        
        loop = asyncio.get_running_loop()
        try:
            def _call_api():
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=60.0) as response:
                    return response.read().decode("utf-8")
                    
            logger.info("Claude Advisor: Requesting tactical instruction from Claude 3.5 Sonnet...")
            res_text = await loop.run_in_executor(None, _call_api)
            res_json = json.loads(res_text)
            content = res_json['choices'][0]['message']['content'].strip()
            
            # Clean markdown fences if present
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
                
            instruction = json.loads(content)
            
            # Validate mandatory fields
            action = instruction.get("action", "HOLD").upper()
            if action not in ["BUY", "SELL", "HOLD"]:
                action = "HOLD"
            instruction["action"] = action
            
            # Log the instruction
            logger.info(
                f"Claude Advisor Instruction: {action} | "
                f"Entry: {instruction.get('entry_price', 'N/A')} | "
                f"TP1: {instruction.get('tp_primary', 'N/A')} | "
                f"TP2: {instruction.get('tp_conservative', 'N/A')} | "
                f"SL: {instruction.get('sl_price', 'N/A')} | "
                f"Confidence: {instruction.get('confidence', 0)}%"
            )
            
            # Cache the instruction
            self.active_instruction = instruction
            self.instruction_timestamp = time.time()
            self.last_call_time = time.time()
            
            # Save to file for dashboard display
            instruction_path = "data/claude_tactical_instruction.json"
            save_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "instruction": instruction
            }
            with open(instruction_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
                
            return instruction
            
        except Exception as e:
            logger.error(f"Claude Advisor: API call failed: {e}")
            return {"action": "HOLD", "reasoning": f"Claude API error: {e}"}
    
    def get_cached_instruction(self) -> dict:
        """Get the currently cached instruction if still valid."""
        if self.active_instruction and (time.time() - self.instruction_timestamp) < self.instruction_ttl:
            return self.active_instruction
        return None
    
    def is_instruction_valid(self) -> bool:
        """Check if the cached instruction is still within its TTL."""
        return (self.active_instruction is not None and 
                (time.time() - self.instruction_timestamp) < self.instruction_ttl)
