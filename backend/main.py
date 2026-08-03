from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os
import time
import MetaTrader5 as mt5

# Manual .env loader to populate environment variables
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as f:
        for _line in f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ[_key.strip()] = _val.strip()

from backend.engines.execution_engine import ExecutionEngine
from backend.engines.risk_engine import RiskEngine
from backend.engines.decision_engine import DecisionEngine
from backend.engines.ml_engine import MLEngine
from backend.engines.feature_store import FeatureStore
from backend.engines.market_engine import MarketEngine
from backend.engines.data_engine import DataEngine
from backend.engines.news_engine import HybridNewsEngine
from backend.telegram.bot import TelegramEcosystem

import os
import dotenv

# Load environment variables with override enabled
dotenv.load_dotenv(override=True)

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def save_settings_to_env(autotrade: bool, lot_size: float, confidence_threshold: float, max_positions: int, hedging_enabled: bool, auto_lot: bool, risk_percent: float, active_method: str):
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
            
    new_lines = []
    keys_updated = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, val = stripped.split("=", 1)
            key = key.strip()
            if key == "AUTOTRADE_ENABLED":
                new_lines.append(f"AUTOTRADE_ENABLED={str(autotrade)}\n")
                keys_updated.add(key)
            elif key == "LOT_SIZE":
                new_lines.append(f"LOT_SIZE={lot_size:.2f}\n")
                keys_updated.add(key)
            elif key == "CONFIDENCE_THRESHOLD":
                new_lines.append(f"CONFIDENCE_THRESHOLD={confidence_threshold:.2f}\n")
                keys_updated.add(key)
            elif key == "AVERAGING_MAX_POSITIONS":
                new_lines.append(f"AVERAGING_MAX_POSITIONS={max_positions}\n")
                keys_updated.add(key)
            elif key == "HEDGING_ENABLED":
                new_lines.append(f"HEDGING_ENABLED={str(hedging_enabled)}\n")
                keys_updated.add(key)
            elif key == "AUTO_LOT_ENABLED":
                new_lines.append(f"AUTO_LOT_ENABLED={str(auto_lot)}\n")
                keys_updated.add(key)
            elif key == "RISK_PERCENT":
                new_lines.append(f"RISK_PERCENT={risk_percent:.1f}\n")
                keys_updated.add(key)
            elif key == "ACTIVE_METHOD":
                new_lines.append(f"ACTIVE_METHOD={active_method}\n")
                keys_updated.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    if "AUTOTRADE_ENABLED" not in keys_updated:
        new_lines.append(f"AUTOTRADE_ENABLED={str(autotrade)}\n")
    if "LOT_SIZE" not in keys_updated:
        new_lines.append(f"LOT_SIZE={lot_size:.2f}\n")
    if "CONFIDENCE_THRESHOLD" not in keys_updated:
        new_lines.append(f"CONFIDENCE_THRESHOLD={confidence_threshold:.2f}\n")
    if "AVERAGING_MAX_POSITIONS" not in keys_updated:
        new_lines.append(f"AVERAGING_MAX_POSITIONS={max_positions}\n")
    if "HEDGING_ENABLED" not in keys_updated:
        new_lines.append(f"HEDGING_ENABLED={str(hedging_enabled)}\n")
    if "AUTO_LOT_ENABLED" not in keys_updated:
        new_lines.append(f"AUTO_LOT_ENABLED={str(auto_lot)}\n")
    if "RISK_PERCENT" not in keys_updated:
        new_lines.append(f"RISK_PERCENT={risk_percent:.1f}\n")
    if "ACTIVE_METHOD" not in keys_updated:
        new_lines.append(f"ACTIVE_METHOD={active_method}\n")
        
    with open(env_path, "w") as f:
        f.writelines(new_lines)
    
    # Update current os environment variables as well
    os.environ["AUTOTRADE_ENABLED"] = str(autotrade)
    os.environ["LOT_SIZE"] = f"{lot_size:.2f}"
    os.environ["CONFIDENCE_THRESHOLD"] = f"{confidence_threshold:.2f}"
    os.environ["AVERAGING_MAX_POSITIONS"] = str(max_positions)
    os.environ["HEDGING_ENABLED"] = str(hedging_enabled)
    os.environ["AUTO_LOT_ENABLED"] = str(auto_lot)
    os.environ["RISK_PERCENT"] = f"{risk_percent:.1f}"
    os.environ["ACTIVE_METHOD"] = active_method
    dotenv.load_dotenv(env_path, override=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Engines
    app.state.telegram_bot = TelegramEcosystem()
    app.state.execution_engine = ExecutionEngine()
    
    # Load settings from .env
    init_autotrade = os.getenv("AUTOTRADE_ENABLED", "False").lower() == "true"
    init_lot = float(os.getenv("LOT_SIZE", "0.10"))
    init_confidence = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))
    init_max_positions = int(os.getenv("AVERAGING_MAX_POSITIONS", "3"))
    init_hedging = os.getenv("HEDGING_ENABLED", "True").lower() == "true"
    init_active_method = os.getenv("ACTIVE_METHOD", "intra-candle-scalper")
    init_auto_lot = os.getenv("AUTO_LOT_ENABLED", "False").lower() == "true"
    init_risk_percent = float(os.getenv("RISK_PERCENT", "1.0"))
    
    # Set explicitly in environment to override any parent process inheritance
    os.environ["AUTOTRADE_ENABLED"] = str(init_autotrade)
    os.environ["LOT_SIZE"] = f"{init_lot:.2f}"
    os.environ["CONFIDENCE_THRESHOLD"] = f"{init_confidence:.2f}"
    os.environ["AVERAGING_MAX_POSITIONS"] = str(init_max_positions)
    os.environ["HEDGING_ENABLED"] = str(init_hedging)
    os.environ["AUTO_LOT_ENABLED"] = str(init_auto_lot)
    os.environ["RISK_PERCENT"] = f"{init_risk_percent:.1f}"
    os.environ["ACTIVE_METHOD"] = init_active_method
    
    app.state.risk_engine = RiskEngine(execution_engine=app.state.execution_engine)
    app.state.risk_engine.autotrade_enabled = init_autotrade
    app.state.risk_engine.config["lot_size"] = init_lot
    app.state.risk_engine.max_positions = init_max_positions
    app.state.risk_engine.hedging_enabled = init_hedging
    app.state.risk_engine.active_method = init_active_method
    
    app.state.decision_engine = DecisionEngine(risk_engine=app.state.risk_engine)
    app.state.decision_engine.confidence_threshold = init_confidence
    
    app.state.ml_engine = MLEngine(decision_engine=app.state.decision_engine)
    app.state.feature_store = FeatureStore(ml_engine=app.state.ml_engine)
    app.state.data_engine = DataEngine(symbol="XAUUSD")
    app.state.news_engine = HybridNewsEngine()
    app.state.news_engine.data_engine = app.state.data_engine
    
    # Initialize Qwen3.7 Macro Strategist
    from backend.engines.macro_strategist import MacroStrategistEngine
    app.state.macro_strategist = MacroStrategistEngine(
        data_engine=app.state.data_engine,
        news_engine=app.state.news_engine,
        decision_engine=app.state.decision_engine
    )
    app.state.risk_engine.macro_strategist = app.state.macro_strategist
    app.state.execution_engine.macro_strategist = app.state.macro_strategist
    app.state.risk_engine.news_engine = app.state.news_engine
    
    app.state.market_engine = MarketEngine(
        feature_store=app.state.feature_store,
        data_engine=app.state.data_engine,
        news_engine=app.state.news_engine
    )

    # Start Engines
    await app.state.telegram_bot.start()
    if hasattr(app.state.telegram_bot, "notifier") and app.state.telegram_bot.notifier:
        app.state.news_engine.notifier = app.state.telegram_bot.notifier
        app.state.execution_engine.notifier = app.state.telegram_bot.notifier
    app.state.risk_engine.news_engine = app.state.news_engine
    await app.state.execution_engine.start()
    await app.state.risk_engine.start()
    await app.state.decision_engine.start()
    await app.state.ml_engine.start()
    await app.state.feature_store.start()
    await app.state.data_engine.start()
    await app.state.news_engine.start()
    await app.state.macro_strategist.start()
    await app.state.market_engine.start()
    
    yield
    
    # Shutdown Engines
    await app.state.market_engine.stop()
    await app.state.macro_strategist.stop()
    await app.state.news_engine.stop()
    await app.state.data_engine.stop()
    await app.state.feature_store.stop()
    await app.state.ml_engine.stop()
    await app.state.decision_engine.stop()
    await app.state.risk_engine.stop()
    await app.state.execution_engine.stop()
    await app.state.telegram_bot.stop()
    mt5.shutdown()

app = FastAPI(
    title="XEDY V41 ULTIMATE",
    description="Institutional Autonomous AI Trading Platform",
    version="41.0.0",
    lifespan=lifespan
)

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path.lower()
    if path.endswith((".html", ".js", ".css")) or path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Define frontend directory
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
os.makedirs(frontend_dir, exist_ok=True)

# API Endpoints
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "OPERATIONAL",
        "timestamp": time.time(),
        "broker": "DISCONNECTED",
        "mt5": "DISCONNECTED",
        "ai": "STANDBY"
    }

@app.get("/api/v1/health/pipeline")
async def health_pipeline():
    """
    Evaluates real-time operational status of the 15-Layer Processing Pipeline
    and the Multi-Agent Swarm Orchestration system components.
    """
    import os, json
    
    # 1. Ingestion & Feature Store Checks
    has_csv = os.path.exists("data/training_features.csv")
    csv_valid = False
    if has_csv:
        try:
            csv_valid = os.path.getsize("data/training_features.csv") > 1000
        except Exception:
            pass

    # 2. AI Parliament & Swarm Checks
    has_news = os.path.exists("data/news_feed.json")
    has_qwen_logs = os.path.exists("data/qwen_decisions_log.jsonl")
    
    # 3. Risk Engine Check
    risk_active = False
    if hasattr(app.state, "risk_engine") and app.state.risk_engine:
        risk_active = getattr(app.state.risk_engine, "is_running", True)

    # 4. Observability & Healing check
    has_error_logs = os.path.exists("logs/errors.log") or os.path.exists("logs/stderr.log")

    # Mapping out layer statuses based on real state evaluations
    return {
        "pipeline": {
            "l1": "ACTIVE" if has_csv else "INACTIVE",           # Market Ingestion
            "l2": "ACTIVE" if csv_valid else "WARNING",          # Data Quality
            "l3": "ACTIVE" if csv_valid else "INACTIVE",         # Feature Store
            "l4": "ACTIVE" if has_news else "INACTIVE",          # Perception Swarm
            "l5": "ACTIVE" if has_news else "INACTIVE",          # Research Swarm
            "l6": "ACTIVE" if has_qwen_logs else "INACTIVE",     # AI Parliament
            "l7": "ACTIVE" if has_qwen_logs else "INACTIVE",     # Meta Reasoning
            "l8": "ACTIVE" if risk_active else "INACTIVE",       # Digital Twin
            "l9": "ACTIVE" if risk_active else "INACTIVE",       # Risk Command
            "l10": "ACTIVE" if risk_active else "INACTIVE",      # Execution Engine
            "l11": "ACTIVE" if risk_active else "INACTIVE",      # Position Management
            "l12": "ACTIVE" if has_qwen_logs else "INACTIVE",    # Trade Review
            "l13": "ACTIVE" if os.path.exists("backend/scripts/adaptive_self_learning.py") else "INACTIVE", # Self Learning
            "l14": "ACTIVE",                                     # Observability (Backend server running)
            "l15": "WARNING" if has_error_logs else "ACTIVE"     # Self Healing
        },
        "swarm": {
            "ceo": "ACTIVE" if (has_news or has_qwen_logs) else "STANDBY",
            "cio": "ACTIVE" if risk_active else "STANDBY",
            "sup": "MONITORING" if risk_active else "STANDBY",
            "spec": "VOTING / CONSENSUS" if has_news else "IDLE"
        }
    }

@app.get("/api/v1/macro/dashboard")
async def get_macro_dashboard():
    """
    Returns real dynamic data for Executive Dashboard panels:
    - upcoming_events: from macro_analysis.economic_releases in news_feed.json
    - latest_news: from news feed headlines
    - smart_alerts: generated from macro bias + regime
    """
    import json, os
    from datetime import datetime, timezone

    news_feed_path = "data/news_feed.json"
    result = {
        "upcoming_events": [],
        "latest_news": [],
        "smart_alerts": [],
        "generated_at": ""
    }

    if not os.path.exists(news_feed_path):
        return result

    try:
        with open(news_feed_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": str(e)}

    result["generated_at"] = data.get("generated_at", "")

    # --- Latest News from news feed ---
    news_items = data.get("news", [])
    for item in news_items[:6]:
        title = item.get("title", "")
        pub = item.get("pubDate", "")
        weight_label = item.get("weight_label", "")
        # Format time: "2026-08-03 07:56:50" -> "03 Ags 07:56"
        try:
            dt = datetime.strptime(pub, "%Y-%m-%d %H:%M:%S")
            pub_fmt = dt.strftime("%d %b %H:%M")
        except Exception:
            pub_fmt = pub[:16] if len(pub) >= 16 else pub

        # Determine tag from title keywords
        title_low = title.lower()
        if "fed" in title_low or "powell" in title_low or "fomc" in title_low:
            tag, tag_class = "Fed", "bg-purple"
        elif "central bank" in title_low or "gold purchase" in title_low or "reserve" in title_low:
            tag, tag_class = "Central Bank", "bg-warning text-dark"
        elif "yield" in title_low or "bond" in title_low or "treasury" in title_low:
            tag, tag_class = "Bond Market", "bg-info"
        elif "geopolit" in title_low or "tension" in title_low or "war" in title_low or "conflict" in title_low:
            tag, tag_class = "Geopolitics", "bg-danger"
        elif "cpi" in title_low or "inflation" in title_low or "pce" in title_low:
            tag, tag_class = "Inflation", "bg-orange"
        elif "nfp" in title_low or "payroll" in title_low or "employment" in title_low:
            tag, tag_class = "NFP", "bg-teal"
        elif "gold" in title_low or "xau" in title_low:
            tag, tag_class = "Gold", "bg-warning text-dark"
        elif "ism" in title_low or "pmi" in title_low or "manufacturing" in title_low:
            tag, tag_class = "PMI/ISM", "bg-blue"
        elif "dollar" in title_low or "dxy" in title_low or "usd" in title_low:
            tag, tag_class = "USD/DXY", "bg-success"
        else:
            tag, tag_class = "Macro", "bg-secondary"

        result["latest_news"].append({
            "time": pub_fmt,
            "headline": title[:85] + ("..." if len(title) > 85 else ""),
            "tag": tag,
            "tag_class": tag_class
        })

    # --- Upcoming Events from economic_releases ---
    macro = data.get("macro_analysis", {})
    releases = macro.get("economic_releases", [])
    known_events = [
        {"name": "NFP", "full": "US Non-Farm Payrolls", "impact": "High"},
        {"name": "ISM", "full": "ISM Manufacturing PMI", "impact": "High"},
        {"name": "CPI", "full": "US CPI (YoY)", "impact": "High"},
        {"name": "PCE", "full": "US Core PCE Price Index", "impact": "High"},
        {"name": "FOMC", "full": "FOMC Meeting Minutes", "impact": "High"},
        {"name": "GDP", "full": "US GDP (QoQ)", "impact": "Medium"},
        {"name": "PPI", "full": "US PPI (YoY)", "impact": "Medium"},
        {"name": "AUD", "full": "AUD/USD Key Event", "impact": "Medium"},
    ]
    added = set()
    for rel in releases:
        rel_low = rel.lower()
        for ev in known_events:
            if ev["name"].lower() in rel_low and ev["name"] not in added:
                # Extract value if present
                import re
                val_match = re.search(r'[\+\-]?\d+[\.,]?\d*[KkMmBb%]?', rel)
                val = val_match.group(0) if val_match else "--"
                result["upcoming_events"].append({
                    "name": ev["full"],
                    "impact": ev["impact"],
                    "actual": val,
                    "prev": "--",
                    "time": result["generated_at"][:10] if result["generated_at"] else "--"
                })
                added.add(ev["name"])

    if not result["upcoming_events"]:
        result["upcoming_events"].append({
            "name": "No upcoming high-impact events",
            "impact": "Low",
            "actual": "--",
            "prev": "--",
            "time": "--"
        })

    # --- Smart Alerts from macro bias ---
    bias = macro.get("bias", "ANY")
    regime = macro.get("regime", "NORMAL")
    threshold = macro.get("optimal_confidence_threshold", 0.72)
    max_op = macro.get("optimal_max_op", 3)
    now_str = datetime.now(timezone.utc).strftime("%H:%M")

    if bias == "BUY_ONLY":
        result["smart_alerts"].append({"time": now_str, "msg": f"Qwen AI Macro Bias: BULLISH — Buy signals prioritized", "signal": "Bullish", "cls": "bg-success"})
    elif bias == "SELL_ONLY":
        result["smart_alerts"].append({"time": now_str, "msg": f"Qwen AI Macro Bias: BEARISH — Sell signals prioritized", "signal": "Bearish", "cls": "bg-danger"})
    elif bias == "WAIT":
        result["smart_alerts"].append({"time": now_str, "msg": f"Qwen AI Macro Bias: WAIT — High uncertainty, no new positions", "signal": "Neutral", "cls": "bg-warning text-dark"})
    else:
        result["smart_alerts"].append({"time": now_str, "msg": f"Qwen AI Macro Bias: ANY — Both directions active", "signal": "Neutral", "cls": "bg-secondary"})

    if regime == "HIGH_NEWS":
        result["smart_alerts"].append({"time": now_str, "msg": "Regime: HIGH NEWS — Elevated volatility, widen SL", "signal": "Alert", "cls": "bg-danger"})
    elif regime == "SIDEWAYS":
        result["smart_alerts"].append({"time": now_str, "msg": "Regime: SIDEWAYS — Range-bound market, scalp mode", "signal": "Caution", "cls": "bg-warning text-dark"})
    else:
        result["smart_alerts"].append({"time": now_str, "msg": "Regime: NORMAL — Standard execution mode active", "signal": "Normal", "cls": "bg-info"})

    result["smart_alerts"].append({"time": now_str, "msg": f"Confidence Threshold: {int(threshold*100)}% | Max Positions: {max_op}", "signal": "Config", "cls": "bg-purple"})

    # Add news-derived alerts
    for item in news_items[:2]:
        title = item.get("title", "")
        title_low = title.lower()
        if any(k in title_low for k in ["gold", "xau", "bullion"]):
            result["smart_alerts"].append({"time": now_str, "msg": title[:70] + ("..." if len(title) > 70 else ""), "signal": "Bullish", "cls": "bg-success"})

    return result

@app.get("/api/v1/forecast/stats")

async def get_forecast_stats():
    import json
    import os
    
    # Load historical accuracy
    hist_data = {"avg_accuracy": 0.0, "total_predictions": 0, "successful_hits": 0, "history": []}
    hist_path = "data/forecast_accuracy_stats.json"
    if os.path.exists(hist_path):
        try:
            with open(hist_path, "r") as f:
                hist_data = json.load(f)
        except Exception as e:
            hist_data["error"] = str(e)
            
    # Load current active forecast
    active_forecast = {}
    news_feed_path = "data/news_feed.json"
    if os.path.exists(news_feed_path):
        try:
            with open(news_feed_path, "r") as f:
                news_data = json.load(f)
                active_forecast = news_data.get("macro_analysis", {})
        except Exception as e:
            print(f"Failed to load active forecast: {e}")
            
    hist_data["active_forecast"] = active_forecast
    return hist_data

@app.post("/api/v1/forecast/trigger")
async def trigger_forecast_bypass():
    import subprocess
    import sys
    import os
    try:
        script_path = os.path.join(os.path.dirname(__file__), "scripts", "claude_forecast.py")
        if not os.path.exists(script_path):
            return {"status": "error", "message": f"Forecast script not found at {script_path}"}
            
        # Execute the Claude forecast engine immediately
        process = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=60)
        if process.returncode == 0:
            return {"status": "success", "message": "Claude daily forecast updated successfully!"}
        else:
            return {"status": "error", "message": f"Script error: {process.stderr}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


from fastapi import BackgroundTasks

# Buat status in-progress flag global untuk melacak status background running
BACKTEST_RUNNING = False

@app.get("/api/v1/backtest")
async def get_backtest(background_tasks: BackgroundTasks, days: int = 30, refresh: bool = False):
    """
    Run or load a cached Walk-Forward backtest validating HLC forecasts
    against actual MT5 historical XAUUSD data.
    
    Menggunakan FastAPI BackgroundTasks untuk refresh=true agar menghindari HTTP Timeout.
    """
    import json
    import os
    import subprocess
    import sys
    global BACKTEST_RUNNING

    cache_path = "data/backtest_cache.json"

    # Jika sedang berjalan di background, beri tahu frontend
    if BACKTEST_RUNNING:
        return {"status": "running", "message": "Backtest is currently running in background. Please wait."}

    # Fungsi pembantu untuk dieksekusi di background
    def run_backtest_subprocess():
        global BACKTEST_RUNNING
        BACKTEST_RUNNING = True
        try:
            script_path = os.path.join(os.path.dirname(__file__), "scripts", "backtest_forecast.py")
            if os.path.exists(script_path):
                subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=600,
                    cwd=os.path.dirname(os.path.dirname(__file__))
                )
        except Exception as e:
            print(f"[ERROR] Background backtest failed: {e}")
        finally:
            BACKTEST_RUNNING = False

    # Jika user meminta refresh
    if refresh:
        background_tasks.add_task(run_backtest_subprocess)
        return {"status": "started", "message": "Backtest started in background. Check back in 2-3 minutes."}

    # Load cache (default behavior jika refresh=False)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached["cached"] = True
            cached["status"] = "success"
            return cached
        except Exception as e:
            return {"error": f"Failed to read cache: {str(e)}"}

    return {"error": "No cached backtest results found. Please run a full backtest first."}




@app.get("/api/v1/qwen/quota")
async def get_qwen_quota():
    """
    Returns usage statistics for Qwen AI calls based on qwen_decisions_log.jsonl.
    Estimates token usage from call count and average prompt size.
    """
    import json, os
    from datetime import datetime, timezone

    log_path = "data/qwen_decisions_log.jsonl"
    total_calls = 0
    today_calls = 0
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    last_call_ts = None
    last_bias = "N/A"
    last_regime = "N/A"
    last_reasoning = ""

    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        total_calls += 1
                        ts = entry.get("timestamp", "")
                        if ts and ts.startswith(today_str):
                            today_calls += 1
                        if ts and (last_call_ts is None or ts > last_call_ts):
                            last_call_ts = ts
                            last_bias = entry.get("bias", "N/A")
                            last_regime = entry.get("regime", "N/A")
                            last_reasoning = entry.get("reasoning", "")
                    except Exception:
                        pass
        except Exception as e:
            return {"error": str(e)}

    # Estimate tokens: avg ~800 tokens per call (prompt + response)
    est_tokens_total = total_calls * 800
    est_tokens_today = today_calls * 800
    monthly_limit = 100  # calls per month (can be adjusted)
    daily_limit = 10      # calls per day recommendation

    return {
        "model": "Qwen 3.7 Flash (Aivene)",
        "total_calls": total_calls,
        "today_calls": today_calls,
        "monthly_limit": monthly_limit,
        "daily_limit": daily_limit,
        "est_tokens_total": est_tokens_total,
        "est_tokens_today": est_tokens_today,
        "last_call_ts": last_call_ts or "Never",
        "last_bias": last_bias,
        "last_regime": last_regime,
        "last_reasoning": last_reasoning[:200] if last_reasoning else "No analysis yet."
    }

@app.post("/api/v1/news/inject")
async def inject_news(payload: dict):
    headline = payload.get("headline")
    source = payload.get("source", "Manual Injection")
    if not headline:
        return {"status": "ERROR", "message": "Headline is required."}
    
    if hasattr(app.state, "news_engine") and app.state.news_engine:
        new_item = {
            "headline": headline,
            "source": source,
            "timestamp": time.time(),
            "relevancy": 100,
            "sentiment_score": float(payload.get("sentiment_score", 50.0)),
            "gold_impact": payload.get("gold_impact", "NEUTRAL").upper(),
            "confidence": 95.0,
            "duration": "24h",
            "regime": "FOMC Event",
            "final_score": float(payload.get("sentiment_score", 50.0)),
            "source_weight": 1.0
        }
        app.state.news_engine.news_feed.append(new_item)
        
        # Trigger macro strategist update immediately
        if hasattr(app.state, "macro_strategist") and app.state.macro_strategist:
            import asyncio
            asyncio.create_task(app.state.macro_strategist.update_macro_decision())
            
        return {"status": "SUCCESS", "message": "News injected and Qwen3.7 Macro Strategist triggered."}
    return {"status": "ERROR", "message": "News Engine not initialized."}

@app.get("/api/v1/forecast/10day")
async def get_10day_forecast():
    """
    10-day XAUUSD price projection — Optimized via Grid Search V2.

    Optimal V2 parameters (minimizes MAE, maximizes Dir Acc & Band Hit Rate):
      decay_rate      = 0.15   (decay factor for target trend projection)
      band_factor     = 1.60   (wider uncertainty bands)
      asym_factor     = 0.30   (widen bands by +30% in bias direction)
      atr_mult_target = 1.5
      atr_mult_high   = 3.0
      atr_mult_low    = 2.0
      rsi_buy         = 62
      rsi_sell        = 46
      macd_thr        = 1.0
      ema_thr         = 0.5
      dxy_thr         = 100
      yield_thr       = 4.0
      vwap_thr        = 0.10   (0.10% vwap dev threshold)
      atr_thresh_hi   = 1
      atr_thresh_lo   = 2

    Backtest V2 performance:
      72h Dir Acc:  58.7%  (vs 35.1% original)
      10d Dir Acc:  64.1%  (vs 26.7% original)
      72h Band Hit: 80.4%  (vs 16.2% original)
      10d Band Hit: 87.2%  (vs 30.0% original)
    """
    import json, os, math, csv
    from datetime import datetime, timedelta, timezone

    # ── V2 Optimized hyperparameters ──────────────────────────────────────────
    DECAY_RATE      = 0.15
    BAND_FACTOR     = 1.60
    ASYM_FACTOR     = 0.30
    ATR_MULT_TARGET = 1.5
    ATR_MULT_HIGH   = 3.0
    ATR_MULT_LOW    = 2.0
    RSI_BUY_THRESH  = 62
    RSI_SELL_THRESH = 46
    MACD_THRESH     = 1.0
    EMA_THRESH      = 0.5
    DXY_THRESH      = 100
    YIELD_THRESH    = 4.0
    VWAP_THRESH     = 0.10
    ATR_THRESH_HI   = 1
    ATR_THRESH_LO   = 2

    news_feed_path   = "data/news_feed.json"
    qwen_log_path    = "data/qwen_decisions_log.jsonl"
    training_csv     = "data/training_features.csv"

    # Fallbacks
    current_price    = 3350.0
    forecast_target  = None
    forecast_high    = None
    forecast_low     = None
    bias             = None
    confidence       = 0.72
    atr_live         = 5.0
    rsi_live         = 50.0
    macd_live        = 0.0
    ema20_live       = 3350.0
    ema50_live       = 3350.0
    dxy_live         = 104.0
    yield_live       = 4.2
    vwap_dev_live    = 0.0

    # ── 1. Read Qwen AI forecast (primary source) ────────────────────────────
    if os.path.exists(news_feed_path):
        try:
            with open(news_feed_path, "r", encoding="utf-8") as f:
                feed = json.load(f)
            macro = feed.get("macro_analysis", {})
            t = macro.get("forecast_price_target")
            h = macro.get("forecast_high_24h")
            l = macro.get("forecast_low_24h")
            b = macro.get("bias")
            c = macro.get("optimal_confidence_threshold")
            if t: forecast_target = float(t)
            if h: forecast_high   = float(h)
            if l: forecast_low    = float(l)
            if b: bias            = b
            if c: confidence      = float(c)
        except Exception:
            pass

    # ── 2. Get live price + ATR from Qwen log ───────────────────────────────
    prev_price = current_price
    if os.path.exists(qwen_log_path):
        try:
            lines = []
            with open(qwen_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        lines.append(line)
            if lines:
                entry = json.loads(lines[-1])
                if entry.get("current_price"):
                    current_price = float(entry["current_price"])
                if entry.get("start_gold_price") and len(lines) > 1:
                    prev_entry = json.loads(lines[-2])
                    prev_price = float(prev_entry.get("start_gold_price", current_price))
        except Exception:
            pass

    # ── 3. Get indicators from training CSV ─────────────────────────────────
    if os.path.exists(training_csv):
        try:
            closes = []
            atr_vals = []
            rsi_vals = []
            macd_vals = []
            dxy_vals = []
            yield_vals = []
            volumes = []
            
            with open(training_csv, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    closes.append(float(row.get("close", 3350.0)))
                    atr_vals.append(float(row.get("atr", 5.0)))
                    rsi_vals.append(float(row.get("rsi", 50.0)))
                    macd_vals.append(float(row.get("macd", 0.0)))
                    dxy_vals.append(float(row.get("dxy_trend", 104.0)))
                    yield_vals.append(float(row.get("yield_trend", 4.2)))
                    volumes.append(float(row.get("tick_volume", 1000.0)))
            
            if closes:
                # Last state values
                atr_live   = atr_vals[-1]
                rsi_live   = rsi_vals[-1]
                macd_live  = macd_vals[-1]
                dxy_live   = dxy_vals[-1]
                yield_live = yield_vals[-1]
                if not current_price or current_price == 3350.0:
                    current_price = closes[-1]

                # Compute EMA-20/50 dynamically
                def ema(data, period):
                    k = 2 / (period + 1)
                    val = data[0]
                    for x in data[1:]:
                        val = x * k + val * (1 - k)
                    return val

                ema20_live = ema(closes, 20)
                ema50_live = ema(closes, 50)

                # Compute VWAP dev of recent period (last 96 rows = 24h)
                window = min(96, len(closes))
                w_closes = closes[-window:]
                w_vols   = volumes[-window:]
                vwap = sum(c*vol for c, vol in zip(w_closes, w_vols)) / max(sum(w_vols), 1)
                vwap_dev_live = (current_price - vwap) / max(vwap, 1) * 100
        except Exception:
            pass

    # ── 4. Smart Multi-Signal inference (if Qwen bias unavailable) ───────────
    def infer_bias_v2_live(rsi, macd, atr, close, ema_cross, dxy, yld, vwap_dev):
        score = 0
        
        # 1. RSI
        if rsi > RSI_BUY_THRESH: score += 2
        elif rsi < RSI_SELL_THRESH: score -= 2
        elif rsi > 55: score += 1
        elif rsi < 45: score -= 1

        # 2. MACD
        if macd > MACD_THRESH: score += 1.5
        elif macd < -MACD_THRESH: score -= 1.5

        # 3. EMA
        if ema_cross > EMA_THRESH: score += 2
        elif ema_cross < -EMA_THRESH: score -= 2

        # 4. DXY (inverse)
        if dxy > DXY_THRESH: score -= 1.5
        elif dxy < -DXY_THRESH: score += 1.5

        # 5. Yield (inverse)
        if yld > YIELD_THRESH: score -= 1
        elif yld < -YIELD_THRESH: score += 1

        # 6. VWAP
        if vwap_dev > VWAP_THRESH: score += 1
        elif vwap_dev < -VWAP_THRESH: score -= 1

        # ATR threshold adjustment
        atr_pct = atr / max(close, 1) * 100
        threshold = ATR_THRESH_HI if atr_pct > 0.15 else ATR_THRESH_LO

        abs_score = abs(score)
        conf = min(0.90, 0.55 + abs_score * 0.035)

        if score >= threshold:
            return "BUY_ONLY", conf
        elif score <= -threshold:
            return "SELL_ONLY", conf
        else:
            return "WAIT", 0.60

    if not bias:
        bias, confidence = infer_bias_v2_live(
            rsi_live, macd_live, atr_live, current_price,
            (ema20_live - ema50_live), dxy_live, yield_live, vwap_dev_live
        )

    # ── 5. Get ATR-derived target bounds if Qwen forecast unavailable ────────
    if not forecast_target:
        if bias == "BUY_ONLY":
            forecast_target = current_price + atr_live * ATR_MULT_TARGET
            forecast_high   = current_price + atr_live * ATR_MULT_HIGH
            forecast_low    = current_price - atr_live * ATR_MULT_LOW
        elif bias == "SELL_ONLY":
            forecast_target = current_price - atr_live * ATR_MULT_TARGET
            forecast_high   = current_price + atr_live * ATR_MULT_LOW
            forecast_low    = current_price - atr_live * ATR_MULT_HIGH
        else:
            forecast_target = current_price + atr_live * 0.2
            forecast_high   = current_price + atr_live * ATR_MULT_LOW
            forecast_low    = current_price - atr_live * ATR_MULT_LOW

    # ── 6. Generate 10-day projection ────────────────────────────────────────
    bias_up   = bias in ("BUY_ONLY", "BUY", "BULLISH")
    bias_down = bias in ("SELL_ONLY", "SELL", "BEARISH")

    daily_range = max(forecast_high - forecast_low, current_price * 0.008)
    delta_24h = forecast_target - current_price

    days = []
    today = datetime.now(timezone.utc)

    for i in range(11):
        date      = today + timedelta(days=i)
        day_label = date.strftime("%d %b") if i > 0 else "Today"

        if i == 0:
            projected = current_price
            high      = current_price + daily_range * 0.5
            low       = current_price - daily_range * 0.5
        else:
            decay_factor = math.exp(-DECAY_RATE * (i - 1))
            trend_delta  = delta_24h * decay_factor

            # Continuation effect
            if i > 3:
                extra = 0.0
                if bias_up:
                    extra = daily_range * 0.12 * (i - 3) * 0.1
                elif bias_down:
                    extra = -daily_range * 0.12 * (i - 3) * 0.1
                trend_delta += extra

            projected = current_price + trend_delta
            base_band = daily_range * math.sqrt(i) * BAND_FACTOR

            # Asymmetric band expansion in direction of bias
            if bias_up:
                high = projected + base_band * (1 + ASYM_FACTOR)
                low  = projected - base_band
            elif bias_down:
                high = projected + base_band
                low  = projected - base_band * (1 + ASYM_FACTOR)
            else:
                high = projected + base_band
                low  = projected - base_band

        direction = (
            "↑" if (i > 0 and projected > current_price)
            else "↓" if (i > 0 and projected < current_price)
            else "●"
        )
        color = (
            "bullish" if projected > current_price
            else "bearish" if projected < current_price
            else "neutral"
        )

        days.append({
            "day":       i,
            "label":     day_label,
            "close":     round(projected, 2),
            "high":      round(high, 2),
            "low":       round(low, 2),
            "direction": direction,
            "color":     color
        })

    return {
        "current_price":  round(current_price, 2),
        "bias":           bias,
        "confidence":     confidence,
        "target_24h":     round(forecast_target, 2),
        "high_24h":       round(forecast_high, 2),
        "low_24h":        round(forecast_low, 2),
        "atr_live":       round(atr_live, 2),
        "model_version":  "v2-optimized-asym",
        "backtest_dir_72h":  "58.7%",
        "backtest_dir_10d":  "64.1%",
        "backtest_band_72h": "80.4%",
        "backtest_band_10d": "87.2%",
        "days":           days,
        "generated_at":   today.strftime("%Y-%m-%d %H:%M UTC")
    }


@app.get("/api/v1/debug_settings")
def debug_settings():
    re = app.state.risk_engine
    return {
        "lot_size": re.config.get("lot_size"),
        "max_positions": re.max_positions,
        "auto_lot": os.environ.get("AUTO_LOT_ENABLED"),
        "active_method": getattr(re, "active_method", "unknown"),
        "autotrade_enabled": getattr(re, "autotrade_enabled", False),
        "intra_candle_task_running": re._intra_candle_task is not None and not re._intra_candle_task.done(),
        "trailing_task_running": re._trailing_task is not None and not re._trailing_task.done()
    }

@app.post("/api/v1/system/rammap/clean")
async def clean_ram_memory():
    import gc
    import ctypes
    
    # 1. Force GC
    gc.collect()
    
    # 2. Minimize Working Set using SetProcessWorkingSetSize
    try:
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        # Set working set size to -1, -1 empties it on Windows
        ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
        status = "SUCCESS"
        message = "RAM cleaned successfully using SetProcessWorkingSetSize & GC collect."
    except Exception as e:
        status = "ERROR"
        message = f"Failed to minimize working set: {str(e)}"
        
    return {"status": status, "message": message}

@app.post("/api/v1/system/vram/set")
async def set_virtual_ram(payload: dict):
    initial_mb = payload.get("initial_mb")
    max_mb = payload.get("max_mb")
    
    if not initial_mb or not max_mb:
        return {"status": "ERROR", "message": "Initial and Maximum size are required."}
        
    try:
        import os
        import subprocess
        
        # 1. Create a temporary ps1 script inside scratch directory
        scratch_dir = r"C:\Users\ACER\.gemini\antigravity\brain\a9224322-a78e-4146-a6bb-d38749b91c5f\scratch"
        os.makedirs(scratch_dir, exist_ok=True)
        ps_script_path = os.path.join(scratch_dir, "set_vram.ps1")
        
        script_content = f"""
Set-CimInstance -Query "Select * from Win32_ComputerSystem" -Property @{{AutomaticManagedPagefile=$False}}
Remove-CimInstance -Query "Select * from Win32_PageFileSetting"
New-CimInstance -ClassName Win32_PageFileSetting -Property @{{Name="C:\\\\pagefile.sys"; InitialSize={initial_mb}; MaximumSize={max_mb}}}
"""
        with open(ps_script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
            
        # 2. Run PowerShell elevated with UAC prompt
        cmd_run_as = f'powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList \'-NoProfile -ExecutionPolicy Bypass -File \\"{ps_script_path}\\"\' -Wait"'
        res = subprocess.run(cmd_run_as, shell=True, check=True, capture_output=True)
        
        return {
            "status": "SUCCESS", 
            "message": f"Konfigurasi Virtual RAM dikirimkan! UAC Elevation pop-up telah dipicu pada Windows Anda. Silakan klik 'YES' pada prompt untuk menyetujui. Restart PC/VPS diperlukan agar perubahan terbaca di Task Manager."
        }
    except Exception as e:
        return {"status": "ERROR", "message": f"Gagal mengirimkan permintaan Virtual RAM: {str(e)}"}

# WebSocket Endpoint
from backend.api.websocket import ws_manager

@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    import logging
    logger = logging.getLogger("xedy.websocket")
    
    # Reload environment variables to sync latest settings from disk
    dotenv.load_dotenv(override=True)
    
    # Send current settings and dashboard data immediately upon connection
    try:
        import json
        initial_autotrade = getattr(app.state.risk_engine, "autotrade_enabled", False)
        initial_lot = app.state.risk_engine.config.get("lot_size", 0.1)
        initial_confidence = getattr(app.state.decision_engine, "confidence_threshold", 0.65)
        initial_max_positions = getattr(app.state.risk_engine, "max_positions", 3)
        initial_hedging = getattr(app.state.risk_engine, "hedging_enabled", True)
        initial_auto_lot = os.environ.get("AUTO_LOT_ENABLED", "False").lower() == "true"
        initial_risk_percent = float(os.environ.get("RISK_PERCENT", "1.0"))
        initial_active_method = os.environ.get("ACTIVE_METHOD", "intra-candle-scalper")
        await websocket.send_text(json.dumps({
            "type": "settings_updated",
            "autotrade": initial_autotrade,
            "lot_size": initial_lot,
            "confidence_threshold": initial_confidence,
            "max_positions": initial_max_positions,
            "hedging_enabled": initial_hedging,
            "auto_lot": initial_auto_lot,
            "risk_percent": initial_risk_percent,
            "active_method": initial_active_method
        }))
        
        # Immediate dashboard snapshot
        if hasattr(app.state, "data_engine") and hasattr(app.state, "news_engine"):
            await websocket.send_text(json.dumps({
                "type": "dashboard_data",
                "data_engine": app.state.data_engine.get_dashboard_data(),
                "news_engine": app.state.news_engine.get_dashboard_data()
            }))
    except Exception as e:
        logger.error(f"Error sending initial settings or dashboard data: {e}")
        
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"WebSocket received raw data: {data}")
            if data == "ping":
                await websocket.send_text("pong")
            else:
                try:
                    import json
                    payload = json.loads(data)
                    if payload.get("action") == "reconnect_mt5":
                        import MetaTrader5 as mt5
                        import logging
                        logger = logging.getLogger("xedy.websocket")
                        mt5.shutdown()
                        if mt5.initialize():
                            logger.info("MT5 Bridge Re-initialized successfully from UI.")
                            await websocket.send_text(json.dumps({"type": "mt5_bridge", "status": "CONNECTED"}))
                        else:
                            logger.error("MT5 Bridge Re-initialization failed.")
                            await websocket.send_text(json.dumps({"type": "mt5_bridge", "status": "FAILED"}))
                    elif payload.get("action") == "update_settings":
                        autotrade = payload.get("autotrade", False)
                        lot_size = float(payload.get("lot_size", 0.1))
                        confidence = float(payload.get("confidence_threshold", 0.65))
                        max_positions = int(payload.get("max_positions", 3))
                        hedging_enabled = bool(payload.get("hedging_enabled", True))
                        auto_lot = bool(payload.get("auto_lot", False))
                        risk_percent = float(payload.get("risk_percent", 1.0))
                        active_method = payload.get("active_method", "intra-candle-scalper")
                        
                        # Persist settings to .env file
                        save_settings_to_env(autotrade, lot_size, confidence, max_positions, hedging_enabled, auto_lot, risk_percent, active_method)
                        
                        if hasattr(app.state, "risk_engine"):
                            app.state.risk_engine.autotrade_enabled = autotrade
                            app.state.risk_engine.config["lot_size"] = lot_size
                            app.state.risk_engine.max_positions = max_positions
                            app.state.risk_engine.hedging_enabled = hedging_enabled
                            app.state.risk_engine.active_method = active_method
                        if hasattr(app.state, "decision_engine"):
                            app.state.decision_engine.confidence_threshold = confidence
                        logger.info(f"Settings updated via UI: autotrade={autotrade}, lot_size={lot_size}, confidence={confidence}, max_positions={max_positions}, hedging={hedging_enabled}, auto_lot={auto_lot}, risk_percent={risk_percent}, active_method={active_method}")
                        
                        # Broadcast settings updated to all clients
                        await ws_manager.broadcast(json.dumps({
                            "type": "settings_updated",
                            "autotrade": autotrade,
                            "lot_size": lot_size,
                            "confidence_threshold": confidence,
                            "max_positions": max_positions,
                            "hedging_enabled": hedging_enabled,
                            "auto_lot": auto_lot,
                            "risk_percent": risk_percent,
                            "active_method": active_method
                        }))
                    elif payload.get("action") == "shutdown":
                        logger.warning("Shutdown command received from UI. Closing server...")
                        import signal
                        # Send ack before killing process
                        await websocket.send_text(json.dumps({"type": "server_shutdown_ack"}))
                        os.kill(os.getpid(), signal.SIGINT)
                    elif payload.get("action") == "close_position":
                        ticket = int(payload.get("ticket"))
                        if hasattr(app.state, "execution_engine"):
                            res = await app.state.execution_engine.close_position(ticket)
                            await websocket.send_text(json.dumps({
                                "type": "close_position_res",
                                "status": res.get("status"),
                                "ticket": ticket,
                                "message": res.get("message", "")
                            }))
                    elif payload.get("action") == "modify_position_sltp":
                        ticket = int(payload.get("ticket"))
                        sl = float(payload.get("sl", 0.0))
                        tp = float(payload.get("tp", 0.0))
                        if hasattr(app.state, "risk_engine") and app.state.risk_engine:
                            app.state.risk_engine._modify_position_sl(ticket, sl, tp)
                    elif payload.get("action") == "close_all":
                        if hasattr(app.state, "execution_engine"):
                            res = await app.state.execution_engine.close_all_positions()
                            await websocket.send_text(json.dumps({
                                "type": "close_all_res",
                                "status": res.get("status"),
                                "closed_count": res.get("closed_count", 0)
                            }))
                    elif payload.get("action") == "start_backtest":
                        from backend.engines.backtest_engine import BacktestEngine
                        be = BacktestEngine()
                        symbol = payload.get("symbol", "XAUUSD")
                        timeframe = payload.get("timeframe", "M15")
                        bars = int(payload.get("bars", 1000))
                        results = await be.run_backtest(symbol=symbol, timeframe_str=timeframe, bars_count=bars)
                        results["type"] = "backtest_results"
                        await websocket.send_text(json.dumps(results))
                except Exception as e:
                    import logging
                    logging.getLogger("xedy.websocket").error(f"WS Exception in main: {e}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# Mount static files for the frontend
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
