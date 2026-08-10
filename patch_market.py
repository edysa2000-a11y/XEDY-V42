import re

# 1. Patch Market Engine
market_path = "backend/engines/market_engine.py"
with open(market_path, "r", encoding="utf-8") as f:
    m_content = f.read()

m_content = m_content.replace(
    "def __init__(self, config=None, feature_stores=None, data_engine=None, news_engine=None, symbols=None):",
    "def __init__(self, config=None, feature_stores=None, data_engine=None, news_engine=None, symbols=None, v39_engines=None):"
)
m_content = m_content.replace(
    "self.symbols = symbols if symbols else [\"XAUUSD\"]",
    "self.symbols = symbols if symbols else [\"XAUUSD\"]\n        self.v39_engines = v39_engines"
)

broadcast_logic = """
                    # Fetch detailed dashboard data if engines exist
                    if self.data_engine and self.news_engine:
                        dashboard_payload = {
                            "type": "dashboard_data",
                            "data_engine": self.data_engine.get_dashboard_data(),
                            "news_engine": self.news_engine.get_dashboard_data()
                        }
                        await ws_manager._broadcast_json(dashboard_payload)
                        
                    # Broadcast V39 Causal Engine Data
                    if self.v39_engines and "XAUUSD" in self.v39_engines:
                        v39 = self.v39_engines["XAUUSD"]
                        
                        # Mock triggering for UI broadcast purposes
                        event_res = await v39["v39_event"].process_news("CPI inflation data exceeds expectations")
                        macro_res = await v39["v39_macro"].calculate_yield_dxy(event_res)
                        
                        # Use actual OANDA tick volume if available
                        tick_vol = 500
                        if self.data_engine:
                            df = self.data_engine.get_historical_data("XAUUSD", "M5", 1)
                            if not df.empty and 'tick_volume' in df.columns:
                                tick_vol = int(df['tick_volume'].iloc[-1])
                                
                        flow_res = await v39["v39_flow"].aggregate_flow_channels(0.005, tick_vol)
                        
                        div_res = await v39["v39_div"].check_divergence(1.5, flow_res, macro_res)
                        gate_res = await v39["v39_consensus"].final_trade_gate(event_res, macro_res, flow_res, div_res, 81.0)
                        
                        v39_payload = {
                            "event": event_res,
                            "macro": macro_res,
                            "flow": flow_res,
                            "div": div_res,
                            "gate": gate_res
                        }
                        await ws_manager.broadcast_v39_causal(v39_payload)
"""
m_content = re.sub(
    r'                    # Fetch detailed dashboard data if engines exist.*?await ws_manager\._broadcast_json\(dashboard_payload\)',
    broadcast_logic.strip(),
    m_content,
    flags=re.DOTALL
)

with open(market_path, "w", encoding="utf-8") as f:
    f.write(m_content)


# 2. Patch main.py to pass v39_engines
main_path = "backend/main.py"
with open(main_path, "r", encoding="utf-8") as f:
    main_content = f.read()

main_content = main_content.replace(
    "app.state.market_engine = MarketEngine(\n        feature_stores=feature_stores_dict,\n        data_engine=app.state.data_engine,\n        news_engine=app.state.news_engine,\n        symbols=target_assets\n    )",
    "app.state.market_engine = MarketEngine(\n        feature_stores=feature_stores_dict,\n        data_engine=app.state.data_engine,\n        news_engine=app.state.news_engine,\n        symbols=target_assets,\n        v39_engines=app.state.asset_engines\n    )"
)

with open(main_path, "w", encoding="utf-8") as f:
    f.write(main_content)

print("market_engine.py and main.py patched for broadcasting V39 data.")
