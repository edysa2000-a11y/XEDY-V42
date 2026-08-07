import os
import urllib.request
import json
import logging
import asyncio
import time

logger = logging.getLogger("xedy.decision_priority")

class DecisionPriorityEngine:
    """
    Decision Priority Engine for Autotrade.
    Evaluates 14 layers to determine the Unified Edge Score (UES).
    """
    
    def __init__(self):
        self.api_key = os.getenv("AIVENE_API_KEY", "")
        self.base_url = os.getenv("AIVENE_BASE_URL", "https://api.aivene.com/v1").rstrip("/")
        self.model = os.getenv("AIVENE_MODEL", "qwen3.7-flash")
        self.last_call_time = 0
        self.call_cooldown = 300 # 5 minutes cooldown to avoid spamming
        
        self.active_decision = None
        
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "decision_priority_engine.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = "You are the Decision Priority Engine. Analyze and return JSON."

    async def evaluate_market(self, technicals: dict, news_text: str, current_price: float, atr: float) -> dict:
        """
        Calls the LLM to evaluate the 14 layers and generate a trading decision.
        """
        now = time.time()
        if now - self.last_call_time < self.call_cooldown:
            logger.info("Decision Priority Engine: Cooldown active. Skipping re-evaluation.")
            return self.active_decision or {"decision": "WAIT", "reasoning": "Cooldown"}
            
        if not self.api_key or self.api_key == "your_key_here":
            logger.warning("Decision Priority Engine: API key not configured.")
            return {"decision": "WAIT", "reasoning": "No API Key"}

        user_content = (
            f"=== CURRENT MARKET DATA ===\n"
            f"Symbol: XAUUSD\n"
            f"Current Price: ${current_price:.2f}\n"
            f"ATR (14): ${atr:.2f}\n\n"
            f"=== TECHNICALS ===\n"
            f"{json.dumps(technicals, indent=2)}\n\n"
            f"=== NEWS & MACRO SENTIMENT (COT PROXY) ===\n"
            f"{news_text}\n\n"
            f"CRITICAL INSTRUCTION: Validate the Cumulative_Volume_Delta_20 (Orderflow) against the NEWS & MACRO SENTIMENT. "
            f"If CVD shows Bullish Absorption but Macro is Bearish, treat it as a trap. "
            f"If CVD and Macro align, boost your Confidence Score significantly.\n\n"
            f"Evaluate all 14 layers and output the strictly formatted JSON response."
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
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1
        }

        loop = asyncio.get_running_loop()
        try:
            def _call_api():
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=60.0) as response:
                    return response.read().decode("utf-8")
                    
            logger.info("Decision Priority Engine: Evaluating 14-Layer Unified Edge Score...")
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
                
            decision_data = json.loads(content)
            
            # Normalize decision
            action = decision_data.get("decision", "WAIT").upper()
            if action not in ["WAIT", "MARKET_BUY", "MARKET_SELL", "LIMIT_BUY", "LIMIT_SELL", "BUY_STOP", "SELL_STOP"]:
                action = "WAIT"
            decision_data["decision"] = action
            
            logger.info(
                f"Decision Priority Result: {action} | UES: {decision_data.get('unified_edge_score', 0)} | "
                f"Entry: {decision_data.get('entry_zone', 'N/A')} | "
                f"SL: {decision_data.get('sl_price', 'N/A')} | "
                f"TP1: {decision_data.get('tp1_price', 'N/A')} | "
                f"Confidence: {decision_data.get('confidence', 0)}%"
            )
            
            self.active_decision = decision_data
            self.last_call_time = time.time()
            
            # Save log
            with open("data/decision_priority_log.jsonl", "a", encoding="utf-8") as f:
                log_entry = decision_data.copy()
                log_entry["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(json.dumps(log_entry) + "\n")
                
            return decision_data
            
        except Exception as e:
            if hasattr(e, 'read'):
                err_body = e.read().decode('utf-8')
                logger.error(f"Decision Priority Engine API call failed: {e}. Body: {err_body}")
                return {"decision": "WAIT", "reasoning": f"API error: {e}. Body: {err_body}"}
            logger.error(f"Decision Priority Engine API call failed: {e}")
            return {"decision": "WAIT", "reasoning": f"API error: {e}"}
