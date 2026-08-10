import re

html_path = "frontend/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Sub Tab Navigation
nav_injection = """                <li class="nav-item"><a class="nav-link" data-target="tab-moneyflow" href="#" style="color: #00ffaa;">💸 Money Flow V39</a></li>
                <li class="nav-item ms-3"><a class="nav-link" data-target="tab-moneyflow-engine" href="#" style="color: #00ccaa; font-size: 0.8rem; border-left: 1px solid #334455; border-radius: 0;">↳ Engine V39 Console</a></li>"""

content = content.replace('<li class="nav-item"><a class="nav-link" data-target="tab-moneyflow" href="#" style="color: #00ffaa;">💸 Money Flow V39</a></li>', nav_injection)

# 2. Add Tab Content
ascii_content = """
            <!-- MONEY FLOW ENGINE V39 SUB-TAB -->
            <div id="tab-moneyflow-engine" class="spa-tab d-none h-100 w-100" style="padding: 1rem; background: #050b14; overflow-y: auto;">
                <div class="bg-dark-panel p-3 rounded border border-success" style="box-shadow: 0 0 15px rgba(0,255,204,0.1);">
                    <pre style="color: #00ffcc; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.9rem; line-height: 1.3; white-space: pre-wrap; width: 100%; margin: 0;">
╔══════════════════════════════════════════════════════════════════════════════╗
║              🧠 XEDY AI • XAUUSD MONEY FLOW ENGINE V39                       ║
║       EVENT → EXPECTATION → YIELD → LIQUIDITY → FLOW → PRICE → DECISION      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ① ⚡ EVENT SHOCK                                                               ║
║                                                                              ║
║ CPI/PCE │ FOMC │ Fed Speech │ NFP │ GDP/ISM │ Tariff │ Geopolitics           ║
║                                                                              ║
║ Impact Score │ Surprise vs Consensus │ Event Severity │ Historical Analog    ║
║                         ↓                                                    ║
║                 EVENT SHOCK SCORE                                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ② 🧠 RATE EXPECTATION ENGINE                                                   ║
║                                                                              ║
║ Fed Funds │ SOFR │ OIS │ Rate Cut/Hike Probability │ Forward Guidance        ║
║                                                                              ║
║ Δ EXPECTATION → Δ YIELD → Δ USD → Δ GOLD                                     ║
║                                                                              ║
║ Expected Direction │ Expected Magnitude │ Expected Transmission Lag          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ③ 📊 YIELD & REAL-YIELD ENGINE                                                 ║
║                                                                              ║
║ US2Y │ US10Y │ US30Y │ TIPS │ Breakeven Inflation                            ║
║                                                                              ║
║                 REAL YIELD = NOMINAL YIELD − INFLATION                       ║
║                                                                              ║
║ Real Yield Direction │ Velocity │ Acceleration │ Gold Sensitivity            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ④ 💵 USD + GLOBAL LIQUIDITY                                                    ║
║                                                                              ║
║ DXY │ USD Strength │ Fed Balance Sheet │ TGA │ RRP │ M2 │ Credit             ║
║ Treasury Liquidity │ Money Market │ VIX/MOVE │ Cross-Currency Flow           ║
║                                                                              ║
║              LIQUIDITY REGIME → RISK APPETITE → GOLD                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑤ 💰 PARALLEL MONEY-FLOW CHANNELS                                              ║
║                                                                              ║
║ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐                  ║
║ │ ETF        │ │ FUTURES    │ │ OPTIONS    │ │ EQUITY     │                  ║
║ │ GLD / IAU  │ │ COMEX/COT  │ │ IV/SKEW    │ │ S&P/NQ     │                  ║
║ │ In/Outflow │ │ OI/CTA     │ │ Gamma      │ │ Risk Flow  │                  ║
║ └────────────┘ └────────────┘ └────────────┘ └────────────┘                  ║
║                                                                              ║
║ ┌────────────┐ ┌────────────┐ ┌────────────┐                                 ║
║ │ CENTRAL    │ │ PHYSICAL   │ │ LIQUIDITY  │                                 ║
║ │ BANK       │ │ MARKET     │ │ FLOW       │                                 ║
║ │ Structural │ │ India/China│ │ Global M2  │                                 ║
║ └────────────┘ └────────────┘ └────────────┘                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑥ 🔬 FLOW INTELLIGENCE                                                         ║
║                                                                              ║
║ FLOW STRENGTH       ██████████████████░░  88/100                             ║
║ FLOW VELOCITY       ███████████████████░  94/100                             ║
║ FLOW PERSISTENCE    ██████████████░░░░░░  72/100                             ║
║ FLOW/PRICE ALIGN    █████████████████░░░  87/100                             ║
║ CAUSAL CONFIDENCE   ██████████████████░░  89%                                ║
║                                                                              ║
║ FLOW REGIME         🟢 ACCUMULATION                                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑦ ⚔️ DIVERGENCE ENGINE                                                         ║
║                                                                              ║
║ Gold ↑ / DXY ↑                  → SAFE-HAVEN CHECK                           ║
║ Gold ↑ / Real Yield ↑           → STRUCTURAL FLOW CHECK                      ║
║ ETF ↓ / Price ↑                 → ABSORPTION CHECK                           ║
║ COMEX Short ↑ / Price ↑         → SHORT-COVERING CHECK                       ║
║ Flow ↑ / Price ↓                → DISTRIBUTION WARNING                       ║
║                                                                              ║
║ DIVERGENCE RISK                         🟢 18%                               ║
║ FLOW / PRICE STATUS                     🟢 ALIGNED                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑧ ⏱️ TRANSMISSION-LAG INTELLIGENCE                                            ║
║                                                                              ║
║ EVENT → EXPECTATION       Expected 0–10m    Actual 4m    🟢                  ║
║ EXPECTATION → YIELD       Expected 5–20m    Actual 8m    🟢                  ║
║ YIELD → DXY               Expected 5–20m    Actual 9m    🟢                  ║
║ DXY → FUTURES             Expected 10–30m   Actual 17m   🟢                  ║
║ FLOW → GOLD               Expected 10–30m   Actual 21m   🟢                  ║
║                                                                              ║
║ DYNAMIC LAG LEARNING → ENABLED                                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑨ 📈 PRICE DISCOVERY ENGINE                                                    ║
║                                                                              ║
║ Order Flow │ Liquidity Sweep │ Volume Profile │ Market Structure             ║
║ Momentum │ Volatility │ S/R │ Breakout │ Rejection │ SNR                     ║
║                                                                              ║
║ PRICE RESPONSE                         🟢 CONFIRMED                          ║
║ TREND                                  🟢 UP                                 ║
║ MOMENTUM                               🟢 STRONG                             ║
║ STRUCTURE                              🟢 BULLISH                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑩ 🧬 REGIME-ADAPTIVE WEIGHTING                                                 ║
║                                                                              ║
║ TREND │ RANGE │ HIGH VOL │ EVENT SHOCK │ SAFE-HAVEN │ LIQUIDITY SHOCK        ║
║                                                                              ║
║ Current Regime: 🟢 BULL TREND                                                ║
║                                                                              ║
║ Bobot otomatis berubah berdasarkan regime — bukan fixed weighting.           ║
║ Causal clustering mencegah FED → Yield → DXY dihitung sebagai 3x evidence.   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑪ 🧠 CAUSAL + MULTI-AGENT CONSENSUS                                            ║
║                                                                              ║
║ MACRO          🟢 84/100                                                     ║
║ MONEY FLOW     🟢 88/100                                                     ║
║ TECHNICAL      🟢 81/100                                                     ║
║ INTERMARKET    🟢 87/100                                                     ║
║ REGIME         🟢 90/100                                                     ║
║                                                                              ║
║ CAUSAL CHAIN                                                                 ║
║ Fed → Rate Expectation → Real Yield → DXY → Flow → XAUUSD                    ║
║                                                                              ║
║ CONSENSUS SCORE                         🟢 85.7/100                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑫ 🎯 CONFIDENCE CALIBRATION ENGINE                                             ║
║                                                                              ║
║ RAW CONFIDENCE                         91%                                   ║
║        ↓                                                                     ║
║ Divergence Adjustment                 -7%                                    ║
║ Regime Adjustment                     -3%                                    ║
║ Historical Calibration                -5%                                    ║
║        ↓                                                                     ║
║ CALIBRATED PROBABILITY                🟢 76%                                 ║
║                                                                              ║
║ ⚠️ RAW CONFIDENCE ≠ TRUE TRADE PROBABILITY                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑬ 💎 EXPECTED VALUE ENGINE                                                     ║
║                                                                              ║
║ Direction Probability                  76%                                   ║
║ Expected R:R                           1 : 2.4                               ║
║ Expected Value                         🟢 +0.82R                             ║
║ Expected Move                          +$25 – $45                            ║
║ Expected Duration                      4 – 12 HOURS                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑭ 🛡️ RISK + CONTRARIAN ENGINE                                                  ║
║                                                                              ║
║ Event Risk             🟡 22%                                                ║
║ Contrarian Risk        🟢 18%                                                ║
║ Liquidity Risk         🟢 LOW                                                ║
║ Positioning Risk       🟢 LOW                                                ║
║ Gap Risk               🟢 LOW                                                ║
║                                                                              ║
║ BEAR CASE: DXY ↑ + Real Yield ↑ + Hawkish Fed + Flow Reversal                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑮ 🚪 FINAL TRADE GATE                                                          ║
║                                                                              ║
║ Trend Probability       ≥70%              🟢 PASS                            ║
║ Calibrated Probability  ≥70%              🟢 76%                             ║
║ Data Quality            ≥90%              🟢 PASS                            ║
║ Statistical Edge        >0                🟢 +0.82R                          ║
║ Divergence Risk         <30%              🟢 18%                             ║
║ Event Risk              Acceptable        🟢 PASS                            ║
║ Flow/Price Alignment    ≥70%              🟢 87%                             ║
║                                                                              ║
║                       🟢 TRADE ALLOWED                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑯ 💼 DYNAMIC TRADE MANAGEMENT                                                  ║
║                                                                              ║
║ Position Size = Probability × Edge × Volatility × Event Risk                 ║
║                                                                              ║
║ ENTRY              4380.00                                                   ║
║ SL                 4310.00                                                   ║
║ TP1                4395.00                                                   ║
║ TP2                4410.00                                                   ║
║ DURATION           4–12 H                                                    ║
║                                                                              ║
║ Confidence ↓ → Size ↓ / Exit                                                 ║
║ Event Risk ↑  → Size ↓                                                       ║
║ Regime Change → Recalculate                                                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⑰ 🔄 SELF-LEARNING ENGINE                                                      ║
║                                                                              ║
║ FORECAST → ACTUAL → DIRECTION ERROR → TIMING ERROR → MAGNITUDE ERROR         ║
║                         ↓                                                    ║
║ ROOT CAUSE → FLOW ERROR → CAUSAL ERROR → LAG ERROR                           ║
║                         ↓                                                    ║
║ WEIGHT OPTIMIZATION → LAG OPTIMIZATION → REGIME LEARNING                     ║
║                         ↓                                                    ║
║ BACKTEST → WALK-FORWARD → OOS → CHAMPION / CHALLENGER                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                         🏆 FINAL OUTPUT                                      ║
║                                                                              ║
║              🟢 XAUUSD BULLISH / BUY CONTINUATION                            ║
║                                                                              ║
║ FLOW SCORE              88/100                                               ║
║ FLOW CONFIDENCE         91%                                                  ║
║ CALIBRATED PROBABILITY  76%                                                  ║
║ CONSENSUS SCORE         85.7/100                                             ║
║ EXPECTED VALUE          +0.82R                                               ║
║ DIVERGENCE RISK         18%                                                  ║
║                                                                              ║
║       PREDICT → COMPARE → ATTRIBUTE → LEARN → VALIDATE → DEPLOY              ║
╚══════════════════════════════════════════════════════════════════════════════╝
                    </pre>
                </div>
            </div>
"""

start_insert = content.find('<div id="tab-forecast"')
if start_insert != -1:
    content = content[:start_insert] + ascii_content + content[start_insert:]

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Sub-tab injected successfully.")
