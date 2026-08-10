import re

html_path = "frontend/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Exact PNG replication for tab-moneyflow
exact_html = """
            <!-- V39 EXACT REPLICA DASHBOARD (TAB-MONEYFLOW) -->
            <div id="tab-moneyflow" class="spa-tab d-none h-100 w-100" style="overflow: hidden; padding: 0.2rem; background: #050b14; color: #a0b0c0; font-family: 'Consolas', 'Courier New', monospace;">
                
                <!-- HEADER -->
                <div class="d-flex justify-content-between align-items-center mb-1 border-bottom border-secondary pb-1" style="height: 3%; padding-left: 0.5rem;">
                    <div style="color: #00ffcc; font-size: 0.75rem; font-weight: bold; letter-spacing: 1px;">
                        <span style="color: #ff9900;">⚡ XEDY AI</span> • XAUUSD • MONEY FLOW ENGINE V39
                    </div>
                    <div style="font-size: 0.65rem;">
                        <span style="color: #555;">STATUS: </span><span style="color: #00ffcc;">LIVE MODE</span>
                    </div>
                </div>

                <!-- MAIN GRID: 4 columns, 4 rows -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: 25% 25% 25% 22%; gap: 0.25rem; height: 95%; padding: 0.25rem;">
                    
                    <!-- PANEL 1: CAUSAL TRANSMISSION CHAIN (Col 1-2, Row 1) -->
                    <div style="grid-column: 1 / 3; grid-row: 1 / 2; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem; position: relative;">
                        <div style="color: #00ffcc; font-size: 0.55rem; letter-spacing: 1px; margin-bottom: 0.4rem;">1. CAUSAL TRANSMISSION CHAIN</div>
                        <div class="d-flex justify-content-between h-75 text-center align-items-center" style="font-size: 0.55rem;">
                            <div style="border: 1px solid #334455; padding: 0.3rem; border-top: 2px solid #ff3366; width: 15%;">EVENT<br><span style="color:#ff3366">CPI/PCE</span><br><span style="color:#445566; font-size:0.45rem">Impact High</span></div>
                            <div style="color: #00ffcc;">→</div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; border-top: 2px solid #00ffcc; width: 15%;">EXPECTATION<br><span style="color:#00ffcc">Bullish</span><br><span style="color:#445566; font-size:0.45rem">Rate Cut Prob</span></div>
                            <div style="color: #00ffcc;">→</div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; border-top: 2px solid #00ffcc; width: 15%;">BOND YIELD<br><span style="color:#00ffcc">Bullish</span><br><span style="color:#445566; font-size:0.45rem">US 10Y Down</span></div>
                            <div style="color: #00ffcc;">→</div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; border-top: 2px solid #00ffcc; width: 15%;">USD (DXY)<br><span style="color:#00ffcc">Bullish</span><br><span style="color:#445566; font-size:0.45rem">DXY Welemah</span></div>
                            <div style="color: #00ffcc;">→</div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; border-top: 2px solid #ffcc00; width: 15%;">ASSET ALLOC<br><span style="color:#ffcc00">Bullish</span><br><span style="color:#445566; font-size:0.45rem">Risk Off</span></div>
                        </div>
                    </div>

                    <!-- PANEL 2: MONEY FLOW CHANNELS (Col 1-2, Row 2) -->
                    <div style="grid-column: 1 / 3; grid-row: 2 / 3; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem;">
                        <div style="color: #00ffcc; font-size: 0.55rem; letter-spacing: 1px; margin-bottom: 0.4rem;">2. MONEY FLOW CHANNELS (PARALLEL CONFIRMATION)</div>
                        <div class="d-flex flex-wrap gap-1 justify-content-between h-75 align-items-center" style="font-size: 0.55rem; text-align: center;">
                            <div style="border: 1px solid #334455; padding: 0.3rem; width: 23%; border-left: 2px solid #ff9900;">ETF FLOW<br><span style="color:#00ffcc">+3.25T</span></div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; width: 23%; border-left: 2px solid #ff9900;">COMEX POS<br><span style="color:#00ffcc">+124K</span></div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; width: 23%; border-left: 2px solid #ff9900;">PHYSICAL<br><span style="color:#00ffcc">Strong</span></div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; width: 23%; border-left: 2px solid #ff3366;">OPTIONS<br><span style="color:#ff3366">Bearish</span></div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; width: 23%; border-left: 2px solid #00ffcc;">EQUITY<br><span style="color:#00ffcc">Risk Off</span></div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; width: 23%; border-left: 2px solid #00ffcc;">CENTRAL BANK<br><span style="color:#00ffcc">Buy</span></div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; width: 23%; border-left: 2px solid #00ffcc;">LIQUIDITY<br><span style="color:#00ffcc">Exp</span></div>
                            <div style="border: 1px solid #334455; padding: 0.3rem; width: 23%; border-left: 2px solid #555;">OTC<br><span style="color:#555">Neutral</span></div>
                        </div>
                    </div>

                    <!-- PANEL 3: FLOW SCORECARD (Col 3-4, Row 1-2) -->
                    <div style="grid-column: 3 / 5; grid-row: 1 / 3; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem; display: flex; flex-direction: column;">
                        <div style="color: #00ffcc; font-size: 0.55rem; letter-spacing: 1px; margin-bottom: 0.4rem;">3. FLOW SCORECARD</div>
                        <div class="d-flex flex-column justify-content-around flex-fill" style="font-size: 0.6rem;">
                            <div class="d-flex justify-content-between"><span>Real Yield</span><span style="color:#00ffcc">+24</span></div>
                            <div class="progress bg-dark mb-1" style="height: 3px;"><div class="progress-bar" style="width: 80%; background: #00ffcc;"></div></div>
                            <div class="d-flex justify-content-between"><span>DXY</span><span style="color:#00ffcc">+18</span></div>
                            <div class="progress bg-dark mb-1" style="height: 3px;"><div class="progress-bar" style="width: 70%; background: #00ffcc;"></div></div>
                            <div class="d-flex justify-content-between"><span>Futures</span><span style="color:#00ffcc">+10</span></div>
                            <div class="progress bg-dark mb-1" style="height: 3px;"><div class="progress-bar" style="width: 40%; background: #00ffcc;"></div></div>
                            <div class="d-flex justify-content-between"><span>ETF Flow</span><span style="color:#00ffcc">+12</span></div>
                            <div class="progress bg-dark mb-1" style="height: 3px;"><div class="progress-bar" style="width: 50%; background: #00ffcc;"></div></div>
                            
                            <hr style="border-color: #334455; margin: 0.4rem 0;">
                            <div class="d-flex justify-content-between fw-bold" style="font-size: 0.75rem;">
                                <span>FLOW SCORE</span><span style="color:#00ffcc">88/100</span>
                            </div>
                            <div class="d-flex justify-content-between fw-bold" style="font-size: 0.75rem;">
                                <span>FLOW CONFIDENCE</span><span style="color:#00ffcc">91%</span>
                            </div>
                            <div class="d-flex justify-content-between" style="color: #ff9900; font-size: 0.65rem;">
                                <span>DIVERGENCE RISK</span><span>18%</span>
                            </div>
                            <div class="text-center mt-2 p-1 fw-bold rounded" style="background: rgba(0, 255, 204, 0.1); color: #00ffcc; border: 1px solid #00ffcc;">
                                ACCUMULATION PHASE
                            </div>
                        </div>
                    </div>

                    <!-- PANEL 4: FLOW DYNAMICS (Col 1-2, Row 3) -->
                    <div style="grid-column: 1 / 3; grid-row: 3 / 4; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem;">
                        <div style="color: #00ffcc; font-size: 0.55rem; letter-spacing: 1px; margin-bottom: 0.4rem;">4. FLOW DYNAMICS</div>
                        <div class="d-flex justify-content-around text-center h-75 align-items-center">
                            <!-- SVG Gauges -->
                            <div>
                                <svg viewBox="0 0 100 50" width="60" height="30">
                                    <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#223" stroke-width="10"/>
                                    <path d="M 10 50 A 40 40 0 0 1 80 20" fill="none" stroke="#00ffcc" stroke-width="10"/>
                                </svg>
                                <div style="font-size:0.55rem;">Strength: <span style="color:#00ffcc">88</span></div>
                            </div>
                            <div>
                                <svg viewBox="0 0 100 50" width="60" height="30">
                                    <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#223" stroke-width="10"/>
                                    <path d="M 10 50 A 40 40 0 0 1 85 25" fill="none" stroke="#00ffcc" stroke-width="10"/>
                                </svg>
                                <div style="font-size:0.55rem;">Velocity: <span style="color:#00ffcc">94</span></div>
                            </div>
                            <div>
                                <svg viewBox="0 0 100 50" width="60" height="30">
                                    <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#223" stroke-width="10"/>
                                    <path d="M 10 50 A 40 40 0 0 1 60 15" fill="none" stroke="#ff9900" stroke-width="10"/>
                                </svg>
                                <div style="font-size:0.55rem;">Persist: <span style="color:#ff9900">72</span></div>
                            </div>
                            <div>
                                <svg viewBox="0 0 100 50" width="60" height="30">
                                    <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#223" stroke-width="10"/>
                                    <path d="M 10 50 A 40 40 0 0 1 70 15" fill="none" stroke="#00ffcc" stroke-width="10"/>
                                </svg>
                                <div style="font-size:0.55rem;">Align: <span style="color:#00ffcc">85</span></div>
                            </div>
                        </div>
                    </div>

                    <!-- PANEL 5: TRANSMISSION LAG (Col 3, Row 3) -->
                    <div style="grid-column: 3 / 4; grid-row: 3 / 4; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem;">
                        <div style="color: #00ffcc; font-size: 0.55rem; letter-spacing: 1px; margin-bottom: 0.4rem;">5. TRANSMISSION LAG</div>
                        <table style="width: 100%; font-size: 0.55rem; line-height: 1.5;">
                            <tr><td>Event → Exp</td><td>10m</td><td style="color:#00ffcc">4m</td></tr>
                            <tr><td>Yield → DXY</td><td>20m</td><td style="color:#00ffcc">9m</td></tr>
                            <tr><td>Flow → Price</td><td>30m</td><td style="color:#ff9900">21m</td></tr>
                            <tr><td>Price → Close</td><td>60m</td><td style="color:#00ffcc">45m</td></tr>
                        </table>
                    </div>

                    <!-- PANEL 6: FLOW STRUCTURE (Col 4, Row 3) -->
                    <div style="grid-column: 4 / 5; grid-row: 3 / 4; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem;">
                        <div style="color: #00ffcc; font-size: 0.55rem; letter-spacing: 1px; margin-bottom: 0.4rem;">6. FLOW STRUCTURE</div>
                        <div class="d-flex flex-column justify-content-around h-75" style="font-size: 0.55rem;">
                            <div class="d-flex justify-content-between"><span style="color:#00ffcc">FAST (HFT)</span><span>Score 85</span></div>
                            <div class="d-flex justify-content-between"><span style="color:#ffcc00">MED (Swing)</span><span>Score 82</span></div>
                            <div class="d-flex justify-content-between"><span style="color:#ff3366">SLOW (Inst)</span><span>Score 75</span></div>
                        </div>
                    </div>

                    <!-- BOTTOM ROW (Row 4): Panels 7 to 13 -->
                    <!-- PANEL 7: PRICE RESPONSE -->
                    <div style="grid-column: 1 / 2; grid-row: 4 / 5; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem;">
                        <div style="color: #00ffcc; font-size: 0.55rem; letter-spacing: 1px; margin-bottom: 0.4rem;">7. PRICE RESPONSE</div>
                        <div class="d-flex flex-column gap-1" style="font-size: 0.5rem; text-align: center;">
                            <div style="background: #112211; color: #00ffcc; border: 1px solid #00ffcc; border-radius: 2px;">Trend: UP</div>
                            <div style="background: #112211; color: #00ffcc; border: 1px solid #00ffcc; border-radius: 2px;">Mom: STRONG</div>
                            <div style="background: #221100; color: #ff9900; border: 1px solid #ff9900; border-radius: 2px;">Vol: ELEVATED</div>
                        </div>
                    </div>
                    
                    <!-- PANEL 8: CONSENSUS -->
                    <div style="grid-column: 2 / 3; grid-row: 4 / 5; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem;">
                        <div style="color: #00ffcc; font-size: 0.55rem; letter-spacing: 1px; margin-bottom: 0.4rem;">8. CONSENSUS MATRIX</div>
                        <div class="d-flex justify-content-between" style="font-size: 0.55rem;"><span>Flow</span><span>88 (30%)</span></div>
                        <div class="d-flex justify-content-between" style="font-size: 0.55rem;"><span>Macro</span><span>84 (25%)</span></div>
                        <div class="d-flex justify-content-between" style="font-size: 0.55rem;"><span>Tech</span><span>81 (20%)</span></div>
                    </div>

                    <!-- PANEL 9: PROBABILITY & 10: RISK -->
                    <div style="grid-column: 3 / 4; grid-row: 4 / 5; display: flex; gap: 0.25rem;">
                        <div style="flex: 1; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem; text-align: center;">
                            <div style="color: #00ffcc; font-size: 0.5rem; margin-bottom: 0.4rem;">9. PROB</div>
                            <div style="color: #00ffcc; font-size: 1.2rem; font-weight: bold;">78%</div>
                        </div>
                        <div style="flex: 1; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem;">
                            <div style="color: #00ffcc; font-size: 0.5rem; margin-bottom: 0.4rem;">10. RISK</div>
                            <div style="font-size: 0.5rem; color:#00ffcc;">Cont: LOW</div>
                            <div style="font-size: 0.5rem; color:#ff9900;">Event: MOD</div>
                        </div>
                    </div>

                    <!-- PANEL 11, 12, 13 -->
                    <div style="grid-column: 4 / 5; grid-row: 4 / 5; display: flex; gap: 0.25rem;">
                        <div style="flex: 1; border: 1px solid #1a2b3c; background: #08101a; padding: 0.4rem;">
                            <div style="color: #00ffcc; font-size: 0.5rem; margin-bottom: 0.4rem;">11/12. LOGIC</div>
                            <div style="font-size: 0.45rem; color: #ff3366;">Inv: DXY>106</div>
                            <div style="font-size: 0.45rem; color: #00ffcc;">OOS: PASS</div>
                        </div>
                        <div style="flex: 1.2; border: 1px solid #00ffcc; background: rgba(0,255,204,0.05); padding: 0.4rem; text-align: center; box-shadow: 0 0 10px rgba(0,255,204,0.2);">
                            <div style="color: #00ffcc; font-size: 0.55rem; font-weight: bold; margin-bottom: 0.2rem;">13. GATE</div>
                            <div style="color: #00ffcc; font-size: 0.65rem; font-weight: bold;">TRADE<br>ALLOWED</div>
                            <div style="font-size: 0.5rem;">UP | RR 1:2.4</div>
                        </div>
                    </div>

                </div>
            </div>
"""

start_idx = content.find('<!-- V39 EXACT REPLICA DASHBOARD (TAB-MONEYFLOW) -->')
if start_idx == -1:
    start_idx = content.find('<div id="tab-moneyflow"')

if start_idx != -1:
    end_idx = content.find('<div id="tab-', start_idx + 20)
    content = content[:start_idx] + exact_html + content[end_idx:]

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Exact PNG Replica injected.")
