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

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def save_settings_to_env(autotrade: bool, lot_size: float, confidence_threshold: float, max_positions: int, hedging_enabled: bool, auto_lot: bool, risk_percent: float):
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Engines
    app.state.telegram_bot = TelegramEcosystem()
    app.state.execution_engine = ExecutionEngine()
    
    # Load settings from .env
    init_autotrade = os.getenv("AUTOTRADE_ENABLED", "False").lower() == "true"
    init_lot = float(os.getenv("LOT_SIZE", "0.10"))
    init_confidence = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))
    
    app.state.risk_engine = RiskEngine(execution_engine=app.state.execution_engine)
    app.state.risk_engine.autotrade_enabled = init_autotrade
    app.state.risk_engine.config["lot_size"] = init_lot
    
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
        await websocket.send_text(json.dumps({
            "type": "settings_updated",
            "autotrade": initial_autotrade,
            "lot_size": initial_lot,
            "confidence_threshold": initial_confidence,
            "max_positions": initial_max_positions,
            "hedging_enabled": initial_hedging,
            "auto_lot": initial_auto_lot,
            "risk_percent": initial_risk_percent
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
                        
                        # Persist settings to .env file
                        save_settings_to_env(autotrade, lot_size, confidence, max_positions, hedging_enabled, auto_lot, risk_percent)
                        
                        if hasattr(app.state, "risk_engine"):
                            app.state.risk_engine.autotrade_enabled = autotrade
                            app.state.risk_engine.config["lot_size"] = lot_size
                            app.state.risk_engine.max_positions = max_positions
                            app.state.risk_engine.hedging_enabled = hedging_enabled
                        if hasattr(app.state, "decision_engine"):
                            app.state.decision_engine.confidence_threshold = confidence
                        logger.info(f"Settings updated via UI: autotrade={autotrade}, lot_size={lot_size}, confidence={confidence}, max_positions={max_positions}, hedging={hedging_enabled}, auto_lot={auto_lot}, risk_percent={risk_percent}")
                        
                        # Broadcast settings updated to all clients
                        await ws_manager.broadcast(json.dumps({
                            "type": "settings_updated",
                            "autotrade": autotrade,
                            "lot_size": lot_size,
                            "confidence_threshold": confidence,
                            "max_positions": max_positions,
                            "hedging_enabled": hedging_enabled,
                            "auto_lot": auto_lot,
                            "risk_percent": risk_percent
                        }))
                    elif payload.get("action") == "shutdown":
                        logger.warning("Shutdown command received from UI. Closing server...")
                        import os
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
