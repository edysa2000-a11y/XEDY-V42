import os
import json
import logging
import aiohttp
from dotenv import load_dotenv

load_dotenv()

import time

_CACHE = {"timestamp": 0, "content": ""}

async def rewrite_narrative_with_qwen(raw_ascii: str) -> str:
    """
    Minimal token wrapper that uses Qwen AI purely as a copywriter to 
    beautify and connect the algorithmic data points into a fluid narrative.
    """
    global _CACHE
    current_time = time.time()
    
    # Irit token: Hanya tembak API setiap 5 menit (300 detik)
    if current_time - _CACHE["timestamp"] < 300 and _CACHE["content"]:
        return _CACHE["content"]
        
    # Pisahkan Header ASCII Box agar tidak dirusak oleh AI
    separator = "╚══════════════════════════════════════════════════════════════════════════╝"
    if separator in raw_ascii:
        parts = raw_ascii.split(separator)
        header = parts[0] + separator + "\n\n"
        body = parts[1].strip()
    else:
        header = ""
        body = raw_ascii
        
    api_key = os.getenv("AIVENE_API_KEY")
    base_url = os.getenv("AIVENE_BASE_URL", "https://api.aivene.com/v1")
    model_name = os.getenv("AIVENE_MODEL", "qwen3.7-flash")
    
    if not api_key:
        logging.warning("Qwen API Key not found. Falling back to zero-token ascii.")
        return raw_ascii

    prompt = (
        "Tulis ulang data teknikal dan makro berikut ini menjadi sebuah laporan "
        "finansial makro yang sangat elegan, profesional, dan natural (seperti analis "
        "Wall Street tingkat atas). Tetapkan gaya bahasa yang mengalir.\n\n"
        "ATURAN KETAT:\n"
        "1. JANGAN PERNAH mengubah angka, harga (Target H4 / Target D1), arah trend, maupun persentase probabilitasnya!\n"
        "2. JANGAN mengubah struktur emoji atau garis pembatas (━━━━━━━━━).\n"
        "3. PERTAHANKAN SEMUA SPASI (NEWLINES/ENTER) persis seperti data mentah. Jangan menggabungkan paragraf yang terpisah!\n"
        "4. JANGAN membuat kotak ASCII atau tabel sendiri.\n"
        f"\nDATA MENTAH:\n{body}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a top-tier macroeconomic strategist and elite copywriter. You write in fluent Indonesian using Wall Street institutional terminology."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 1000
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    if content is None:
                        content = ''
                    result = content.strip()
                    
                    if not result:
                        logging.error(f"Qwen Writer API returned empty content: {data}")
                        result = raw_ascii
                    else:
                        # Gabungkan kembali Header utuh dengan Body yang sudah dipercantik
                        result = header + result
                        
                    _CACHE["timestamp"] = current_time
                    _CACHE["content"] = result
                    return result
                else:
                    err = await resp.text()
                    logging.error(f"Qwen Writer API Error: {err}")
                    # Set cache timestamp even on error to prevent spamming the API
                    _CACHE["timestamp"] = current_time
                    return raw_ascii
    except Exception as e:
        logging.error(f"Qwen Writer Connection Error: {e}")
        _CACHE["timestamp"] = current_time
        return raw_ascii
