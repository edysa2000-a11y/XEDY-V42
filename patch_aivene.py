import re

file_path = "backend/engines/aivene_client.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

embedding_func = """
    async def get_embeddings(self, text: str) -> list:
        \"\"\"
        Fetches text embeddings using Qwen3 Embedding via Aivene API.
        Used for Event Shock and semantic Causal parsing.
        \"\"\"
        if self.api_key == "your_key_here" or not self.api_key:
            logger.warning("AIVENE_API_KEY is not set. Returning dummy embeddings.")
            return [0.0] * 1536

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "text-embedding-v3", # Fallback to provider's Qwen/Embedding model
            "input": text
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
            if 'data' in res_json and len(res_json['data']) > 0:
                return res_json['data'][0]['embedding']
            return [0.0] * 1536
        except Exception as e:
            logger.error(f"Failed to fetch embeddings: {e}")
            return [0.0] * 1536
"""

if "def get_embeddings" not in content:
    content += embedding_func
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Added get_embeddings to aivene_client.py")
else:
    print("get_embeddings already exists.")
