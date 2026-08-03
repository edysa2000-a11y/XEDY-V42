"""
backtest_forecast.py
Engine Backtest Validasi Forecast HLC Multi-Timeframe XAUUSD
Sumber Data: MetaTrader 5 (copy_rates_range)
"""

import os
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[WARN] MetaTrader5 not available.")

AIVENE_API_KEY = os.getenv("AIVENE_API_KEY", "")
SYMBOL = "XAUUSD"


def clean_json_string(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def pct_error(predicted: float, actual: float) -> float:
    if actual == 0:
        return 0.0
    return abs(predicted - actual) / abs(actual) * 100.0


def direction_correct(pred_close: float, open_price: float, actual_close: float) -> bool:
    return (pred_close >= open_price) == (actual_close >= open_price)


def fetch_mt5_rates(timeframe, days_back: int = 35):
    if not MT5_AVAILABLE:
        return []
    if not mt5.initialize():
        print(f"[ERROR] MT5 init failed: {mt5.last_error()}")
        return []
    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=days_back)
    rates = mt5.copy_rates_range(SYMBOL, timeframe, date_from, date_to)
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        return []
    result = []
    for r in rates:
        dt = datetime.fromtimestamp(r["time"], tz=timezone.utc)
        result.append({
            "time":  dt.strftime("%Y-%m-%d"),
            "open":  float(r["open"]),
            "high":  float(r["high"]),
            "low":   float(r["low"]),
            "close": float(r["close"]),
        })
    return result


def retroactive_forecast_ai(open_price: float, date_str: str, timeframe_label: str) -> dict:
    mult_map = {"1d": 0.006, "1w": 0.014, "2w": 0.022}
    mult = mult_map.get(timeframe_label, 0.008)

    if not AIVENE_API_KEY:
        return {
            "high":  round(open_price * (1 + mult), 2),
            "low":   round(open_price * (1 - mult), 2),
            "close": round(open_price * (1 + mult * 0.35), 2),
        }

    url = "https://api.aivene.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {AIVENE_API_KEY}",
        "Content-Type":  "application/json",
        "User-Agent":    "Mozilla/5.0",
    }
    tf_desc = {
        "1d": "the next 1 trading day (24 hours)",
        "1w": "the next 1 week (5 trading days)",
        "2w": "the next 2 weeks (10 trading days)",
    }.get(timeframe_label, "the next period")

    system_prompt = (
        "You are a quantitative analyst AI for XAUUSD forecasting.\n"
        "Given the opening price and date, produce a realistic HLC forecast.\n"
        "Respond ONLY with valid JSON (no markdown fences):\n"
        "{\"high\": float, \"low\": float, \"close\": float}"
    )
    user_msg = (
        f"Date: {date_str}\n"
        f"XAUUSD Open Price: ${open_price:.2f}\n"
        f"Forecast for: {tf_desc}\n"
        "Predict realistic High, Low, and Close prices based on typical gold volatility."
    )

    payload = {
        "model": "qwen3.7-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30.0) as r:
            res_json = json.loads(r.read().decode("utf-8"))
            content  = res_json["choices"][0]["message"]["content"]
            pred     = json.loads(clean_json_string(content))
            return {
                "high":  safe_float(pred.get("high"),  open_price * (1 + mult)),
                "low":   safe_float(pred.get("low"),   open_price * (1 - mult)),
                "close": safe_float(pred.get("close"), open_price * (1 + mult * 0.35)),
            }
    except Exception as e:
        print(f"[WARN] AI forecast failed {date_str} ({timeframe_label}): {e}")
        return {
            "high":  round(open_price * (1 + mult), 2),
            "low":   round(open_price * (1 - mult), 2),
            "close": round(open_price * (1 + mult * 0.35), 2),
        }


def calc_metrics(records: list) -> dict:
    if not records:
        return {}
    n = len(records)
    errors_close = []
    hits_1pct = hits_2pct = direction_hits = 0
    sum_mae_close = sum_mae_high = sum_mae_low = 0.0
    for r in records:
        ec = pct_error(r["pred_close"], r["actual_close"])
        errors_close.append(ec)
        sum_mae_close += abs(r["pred_close"] - r["actual_close"])
        sum_mae_high  += abs(r["pred_high"]  - r["actual_high"])
        sum_mae_low   += abs(r["pred_low"]   - r["actual_low"])
        if ec <= 1.0: hits_1pct += 1
        if ec <= 2.0: hits_2pct += 1
        if r.get("direction_correct", False): direction_hits += 1
    return {
        "total_candles":      n,
        "mae_close":          round(sum_mae_close / n, 2),
        "mae_high":           round(sum_mae_high  / n, 2),
        "mae_low":            round(sum_mae_low   / n, 2),
        "mape_close":         round(sum(errors_close) / n, 3),
        "hit_rate_1pct":      round(hits_1pct  / n * 100, 1),
        "hit_rate_2pct":      round(hits_2pct  / n * 100, 1),
        "direction_accuracy": round(direction_hits / n * 100, 1),
    }


def build_detail(rates, timeframe_label):
    detail = []
    label_map = {"1d": len(rates), "1w": len(rates), "2w": len(rates)}
    total = len(rates)
    for i, candle in enumerate(rates):
        print(f"  {timeframe_label.upper()} [{i+1}/{total}] {candle['time']} open=${candle['open']:.2f}")
        pred   = retroactive_forecast_ai(candle["open"], candle["time"], timeframe_label)
        dir_ok = direction_correct(pred["close"], candle["open"], candle["close"])
        ec     = pct_error(pred["close"], candle["close"])
        detail.append({
            "date":            candle["time"],
            "open":            candle["open"],
            "pred_high":       pred["high"],
            "pred_low":        pred["low"],
            "pred_close":      pred["close"],
            "actual_high":     candle["high"],
            "actual_low":      candle["low"],
            "actual_close":    candle["close"],
            "error_close_pct": round(ec, 3),
            "direction_correct": dir_ok,
            "status": "HIT" if ec <= 1.0 else ("NEAR" if ec <= 2.0 else "MISS"),
        })
    return detail


def run_backtest(days: int = 30) -> dict:
    print(f"[INFO] Starting backtest – {days} days – symbol: {SYMBOL}")
    if not MT5_AVAILABLE:
        return {"error": "MetaTrader5 library not available on this system"}

    print("[INFO] Fetching D1 candles from MT5...")
    d1_rates = fetch_mt5_rates(mt5.TIMEFRAME_D1, days_back=days + 5)[-days:]

    print("[INFO] Fetching W1 candles from MT5...")
    w1_rates = fetch_mt5_rates(mt5.TIMEFRAME_W1, days_back=days + 14)[-6:]

    tw_rates = []
    for i in range(0, len(w1_rates) - 1, 2):
        c1 = w1_rates[i]
        c2 = w1_rates[i + 1] if i + 1 < len(w1_rates) else c1
        tw_rates.append({
            "time":  c1["time"],
            "open":  c1["open"],
            "high":  max(c1["high"], c2["high"]),
            "low":   min(c1["low"],  c2["low"]),
            "close": c2["close"],
        })

    print(f"[INFO] Forecasting {len(d1_rates)} D1 candles...")
    detail_1d = build_detail(d1_rates, "1d")

    print(f"[INFO] Forecasting {len(w1_rates)} W1 candles...")
    detail_1w = build_detail(w1_rates, "1w")

    print(f"[INFO] Forecasting {len(tw_rates)} 2W periods...")
    detail_2w = build_detail(tw_rates, "2w")

    chart_data = {
        "dates":              [r["date"]         for r in detail_1d],
        "actual_close":       [r["actual_close"]  for r in detail_1d],
        "predicted_close_1d": [r["pred_close"]    for r in detail_1d],
        "actual_high":        [r["actual_high"]   for r in detail_1d],
        "predicted_high_1d":  [r["pred_high"]     for r in detail_1d],
        "actual_low":         [r["actual_low"]    for r in detail_1d],
        "predicted_low_1d":   [r["pred_low"]      for r in detail_1d],
    }

    period_from = d1_rates[0]["time"]  if d1_rates else (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    period_to   = d1_rates[-1]["time"] if d1_rates else datetime.now().strftime("%Y-%m-%d")

    result = {
        "backtest_period": f"{period_from} to {period_to}",
        "symbol":          SYMBOL,
        "days_requested":  days,
        "results": {
            "1d": calc_metrics(detail_1d),
            "1w": calc_metrics(detail_1w),
            "2w": calc_metrics(detail_2w),
        },
        "chart_data": chart_data,
        "detail_1d":  detail_1d,
        "detail_1w":  detail_1w,
        "detail_2w":  detail_2w,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB"),
    }

    cache_path = "data/backtest_cache.json"
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Cache saved to {cache_path}")
    except Exception as e:
        print(f"[WARN] Cache save failed: {e}")

    print("[INFO] Backtest complete.")
    return result


if __name__ == "__main__":
    result = run_backtest(days=30)
    print(json.dumps({
        "period":     result.get("backtest_period"),
        "metrics_1d": result["results"].get("1d"),
        "metrics_1w": result["results"].get("1w"),
        "metrics_2w": result["results"].get("2w"),
    }, indent=2))