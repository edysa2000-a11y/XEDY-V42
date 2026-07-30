import os
import urllib.request
import urllib.parse
import json
import logging
import asyncio

logger = logging.getLogger("xedy.aivene")

class AiveneClient:
    """
    Aivene API Client to communicate with Qwen3.7 Flash for Macro analysis.
    Uses standard library urllib to guarantee compatibility with Python 3.14 (cgi-safe).
    """
    def __init__(self):
        self.api_key = os.getenv("AIVENE_API_KEY", "your_key_here")
        self.base_url = os.getenv("AIVENE_BASE_URL", "https://api.aivene.com/v1").rstrip("/")
        self.model = "qwen3.7-flash"

    async def get_macro_analysis(self, news_text: str, technicals: dict, mae_mfe_data: dict = None) -> dict:
        """
        Sends macro indicators, news, and historical MAE/MFE feedback to Qwen3.7 Flash.
        Returns a dictionary containing 'bias', 'regime', and 'reasoning'.
        """
        if self.api_key == "your_key_here" or not self.api_key:
            logger.warning("AIVENE_API_KEY is not set. Falling back to default Macro Bias (ANY) and Regime (NORMAL).")
            return {"bias": "ANY", "regime": "NORMAL", "reasoning": "Aivene API Key is not configured."}

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "XEDY/v41"
        }

        system_prompt = (
            "You are the Chief Strategist AI (Macro Brain) for the XEDY algorithmic trading platform.\n"
            "Your task is to analyze the market context and recent trade feedback (MAE/MFE) and output a JSON decision structure.\n"
            "You MUST respond ONLY with a valid JSON object matching this structure, without markdown code fences:\n"
            "{\n"
            "  \"bias\": \"BUY_ONLY\" | \"SELL_ONLY\" | \"ANY\" | \"WAIT\",\n"
            "  \"regime\": \"NORMAL\" | \"HIGH_NEWS\" | \"SIDEWAYS\",\n"
            "  \"optimal_confidence_threshold\": float (value between 0.60 and 0.78, e.g. 0.68),\n"
            "  \"optimal_max_op\": int (value between 2 and 6, e.g. 4),\n"
            "  \"reasoning\": \"Brief explanation of the decision including justification for threshold and max OP based on recent MAE/MFE\"\n"
            "}"
        )

        user_content = (
            f"Here is the current market technical data:\n{json.dumps(technicals, indent=2)}\n\n"
            f"Here is the compiled daily news sentiment summary:\n{news_text}\n\n"
        )
        
        if mae_mfe_data:
            user_content += f"Here is the performance feedback (MAE/MFE) of recent closed trades:\n{json.dumps(mae_mfe_data, indent=2)}\n\n"
            
        user_content += "Review the feedback of the previous trades to optimize your next decision. Determine the macro trading bias, regime, optimal confidence threshold, and optimal max OP."

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        loop = asyncio.get_running_loop()
        try:
            def _call_api():
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=30.0) as response:
                    return response.read().decode("utf-8")

            res_text = await loop.run_in_executor(None, _call_api)
            res_json = json.loads(res_text)
            content = res_json['choices'][0]['message']['content'].strip()
            data = json.loads(content)
            logger.info(f"Qwen3.7 Macro Analysis complete: bias={data.get('bias')}, regime={data.get('regime')}, threshold={data.get('optimal_confidence_threshold')}, max_op={data.get('optimal_max_op')}")
            return {
                "bias": data.get("bias", "ANY"),
                "regime": data.get("regime", "NORMAL"),
                "optimal_confidence_threshold": data.get("optimal_confidence_threshold", None),
                "optimal_max_op": data.get("optimal_max_op", None),
                "reasoning": data.get("reasoning", "")
            }
        except Exception as e:
            logger.error(f"Failed to connect to Aivene API: {e}")
            return {"bias": "ANY", "regime": "NORMAL", "reasoning": f"Connection Exception: {e}"}
