import re

html_path = "frontend/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Define the massive 13-panel grid
v39_grid = """
            <!-- V39 13-PANEL MEGA DASHBOARD (FULLSCREEN NO-SCROLL) -->
            <div id="tab-v39-overview" class="spa-tab d-none h-100 w-100" style="overflow: hidden; padding: 0.5rem; background: #0b0e14;">
                
                <!-- HEADER (Minimal) -->
                <div class="d-flex justify-content-between align-items-center mb-1" style="height: 3%;">
                    <h6 class="mb-0 text-warning" style="font-size: 0.8rem; letter-spacing: 1px;"><i class="bi bi-robot"></i> XEDY AI • XAUUSD • MONEY FLOW ENGINE V39</h6>
                    <div class="text-muted" style="font-size: 0.65rem;">LIVE MODE <span class="text-success ms-2">ADAPTIVE ON</span></div>
                </div>

                <!-- MAIN GRID CONTAINER -->
                <div style="display: grid; grid-template-columns: 2fr 1fr; grid-template-rows: 25% 45% 25%; gap: 0.5rem; height: 95%;">
                    
                    <!-- TOP LEFT: PANELS 1 & 2 -->
                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <!-- Panel 1: Causal Chain -->
                        <div class="bg-dark-panel rounded border border-secondary p-2" style="flex: 1; display: flex; flex-direction: column;">
                            <div class="text-muted mb-1" style="font-size: 0.6rem; letter-spacing:1px;">1. CAUSAL TRANSMISSION CHAIN (EVENT -> EXPECTATION -> YIELD -> LIQUIDITY -> FLOW -> PRICE)</div>
                            <div class="d-flex justify-content-between h-100 text-center" style="font-size: 0.65rem;">
                                <div class="border border-secondary rounded p-1 mx-1 flex-fill">EVENT<br><span class="text-danger">CPI/PCE</span></div>
                                <div class="align-self-center">→</div>
                                <div class="border border-secondary rounded p-1 mx-1 flex-fill">EXPECTATION<br><span class="text-bullish">Bullish</span></div>
                                <div class="align-self-center">→</div>
                                <div class="border border-success rounded p-1 mx-1 flex-fill text-success">REAL YIELD<br>2.18%</div>
                                <div class="align-self-center">→</div>
                                <div class="border border-secondary rounded p-1 mx-1 flex-fill">USD LIQUIDITY<br><span class="text-bullish">Bullish</span></div>
                                <div class="align-self-center">→</div>
                                <div class="border border-warning rounded p-1 mx-1 flex-fill text-warning">ASSET ALLOC<br>Risk Off</div>
                                <div class="align-self-center">→</div>
                                <div class="border border-success rounded p-1 mx-1 flex-fill text-success">FLOW CHANNELS<br>Accumulation</div>
                                <div class="align-self-center">→</div>
                                <div class="border border-danger rounded p-1 mx-1 flex-fill text-danger">PRICE RESPONSE<br>Confirmed</div>
                            </div>
                        </div>
                        
                        <!-- Panel 2: Money Flow Channels -->
                        <div class="bg-dark-panel rounded border border-secondary p-2" style="flex: 1; display: flex; flex-direction: column;">
                            <div class="text-muted mb-1" style="font-size: 0.6rem; letter-spacing:1px;">2. MONEY FLOW CHANNELS (PARALLEL CONFIRMATION)</div>
                            <div class="d-flex justify-content-between h-100 text-center gap-1" style="font-size: 0.6rem;">
                                <div class="border border-secondary rounded p-1 flex-fill">ETF FLOW<br><span class="text-success">+3.25 Ton</span></div>
                                <div class="border border-secondary rounded p-1 flex-fill">FUTURES<br><span class="text-success">+124,853</span></div>
                                <div class="border border-secondary rounded p-1 flex-fill">OPTIONS<br><span class="text-success">Skew +0.21</span></div>
                                <div class="border border-secondary rounded p-1 flex-fill">EQUITY<br><span class="text-danger">Risk Off</span></div>
                                <div class="border border-secondary rounded p-1 flex-fill">CENTRAL BANK<br><span class="text-success">+18.7 Ton</span></div>
                                <div class="border border-secondary rounded p-1 flex-fill">PHYSICAL<br><span class="text-success">High Demand</span></div>
                                <div class="border border-secondary rounded p-1 flex-fill">LIQUIDITY<br><span class="text-success">Expanding</span></div>
                            </div>
                        </div>
                    </div>

                    <!-- TOP RIGHT: PANEL 3 (Scorecard) -->
                    <div class="bg-dark-panel rounded border border-secondary p-2" style="grid-row: 1 / 3;">
                        <div class="text-muted mb-2" style="font-size: 0.6rem; letter-spacing:1px;">3. FLOW SCORECARD</div>
                        <div style="font-size: 0.65rem;" class="d-flex flex-column h-100 justify-content-around">
                            <div class="d-flex justify-content-between"><span>Real Yield</span><span class="text-success">+24</span></div>
                            <div class="progress mb-1" style="height: 4px;"><div class="progress-bar bg-success" style="width: 90%;"></div></div>
                            <div class="d-flex justify-content-between"><span>DXY</span><span class="text-success">+18</span></div>
                            <div class="progress mb-1" style="height: 4px;"><div class="progress-bar bg-success" style="width: 70%;"></div></div>
                            <div class="d-flex justify-content-between"><span>Futures</span><span class="text-success">+10</span></div>
                            <div class="progress mb-1" style="height: 4px;"><div class="progress-bar bg-success" style="width: 40%;"></div></div>
                            <div class="d-flex justify-content-between"><span>ETF Flow</span><span class="text-success">+12</span></div>
                            <div class="progress mb-2" style="height: 4px;"><div class="progress-bar bg-success" style="width: 50%;"></div></div>
                            
                            <hr class="border-secondary my-1">
                            <div class="d-flex justify-content-between fs-6 fw-bold"><span>FLOW SCORE</span><span class="text-success">88/100</span></div>
                            <div class="d-flex justify-content-between fs-6 fw-bold"><span>FLOW CONFIDENCE</span><span class="text-success">91%</span></div>
                            <div class="d-flex justify-content-between text-warning"><span>DIVERGENCE RISK</span><span>18%</span></div>
                            <div class="d-flex justify-content-between text-success"><span>CAUSAL CONFIDENCE</span><span>89%</span></div>
                            <div class="text-center mt-2 p-1 bg-success text-black fw-bold rounded">ACCUMULATION</div>
                        </div>
                    </div>

                    <!-- MIDDLE LEFT: PANELS 4, 5, 6, 7 -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 0.5rem;">
                        
                        <!-- Panel 4: Flow Dynamics -->
                        <div class="bg-dark-panel rounded border border-secondary p-2 d-flex flex-column">
                            <div class="text-muted mb-1" style="font-size: 0.6rem; letter-spacing:1px;">4. FLOW DYNAMICS</div>
                            <div class="d-flex justify-content-around text-center mt-2" style="font-size: 0.65rem;">
                                <div><div class="fw-bold text-success" style="font-size: 1.2rem;">88</div>Strength</div>
                                <div><div class="fw-bold text-success" style="font-size: 1.2rem;">94</div>Velocity</div>
                                <div><div class="fw-bold text-warning" style="font-size: 1.2rem;">72</div>Persist.</div>
                            </div>
                        </div>

                        <!-- Panel 5: Transmission Lag -->
                        <div class="bg-dark-panel rounded border border-secondary p-2 d-flex flex-column">
                            <div class="text-muted mb-1" style="font-size: 0.6rem; letter-spacing:1px;">5. TRANSMISSION LAG</div>
                            <table class="table table-sm table-borderless text-white m-0" style="font-size: 0.55rem;">
                                <tr><td>Event -> Expect</td><td>10m</td><td class="text-success">4m</td></tr>
                                <tr><td>Yield -> DXY</td><td>20m</td><td class="text-success">9m</td></tr>
                                <tr><td>Flow -> Price</td><td>30m</td><td class="text-warning">21m</td></tr>
                            </table>
                        </div>

                        <!-- Panel 6: Flow Structure -->
                        <div class="bg-dark-panel rounded border border-secondary p-2 d-flex flex-column">
                            <div class="text-muted mb-1" style="font-size: 0.6rem; letter-spacing:1px;">6. FLOW STRUCTURE</div>
                            <div class="d-flex justify-content-between" style="font-size: 0.6rem;">
                                <div><span class="text-info">FAST</span><br>Score 85</div>
                                <div><span class="text-warning">MED</span><br>Score 82</div>
                                <div><span class="text-danger">SLOW</span><br>Score 75</div>
                            </div>
                        </div>

                        <!-- Panel 7: Price Response -->
                        <div class="bg-dark-panel rounded border border-secondary p-2 d-flex flex-column text-center">
                            <div class="text-muted mb-1" style="font-size: 0.6rem; letter-spacing:1px;">7. PRICE RESPONSE</div>
                            <div class="d-flex flex-wrap justify-content-center gap-1" style="font-size: 0.55rem;">
                                <div class="badge bg-success">Trend: UP</div>
                                <div class="badge bg-success">Mom: STRONG</div>
                                <div class="badge bg-success">Struct: BULLISH</div>
                                <div class="badge bg-warning text-dark">Vol: ELEVATED</div>
                            </div>
                        </div>
                    </div>

                    <!-- BOTTOM ROW: PANELS 8 to 13 -->
                    <div style="grid-column: 1 / 3; display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.5rem;">
                        
                        <!-- Panel 8: Consensus -->
                        <div class="bg-dark-panel rounded border border-secondary p-2 d-flex flex-column">
                            <div class="text-muted mb-1" style="font-size: 0.55rem; letter-spacing:1px;">8. CONSENSUS MATRIX</div>
                            <div class="d-flex justify-content-between" style="font-size: 0.55rem;"><span>Flow</span><span>88 (30%)</span></div>
                            <div class="d-flex justify-content-between" style="font-size: 0.55rem;"><span>Macro</span><span>84 (25%)</span></div>
                            <div class="d-flex justify-content-between" style="font-size: 0.55rem;"><span>Tech</span><span>81 (20%)</span></div>
                            <div class="fw-bold mt-auto" style="font-size: 0.65rem;">TOTAL: <span class="text-success">85.7</span></div>
                        </div>

                        <!-- Panel 9: Trade Prob -->
                        <div class="bg-dark-panel rounded border border-secondary p-2 d-flex flex-column text-center">
                            <div class="text-muted mb-1" style="font-size: 0.55rem; letter-spacing:1px;">9. PROBABILITY</div>
                            <div class="text-success fw-bold" style="font-size: 1.5rem;">78%</div>
                            <div style="font-size: 0.55rem;">UP PROBABILITY</div>
                        </div>

                        <!-- Panel 10: Risk Check -->
                        <div class="bg-dark-panel rounded border border-secondary p-2 d-flex flex-column">
                            <div class="text-muted mb-1" style="font-size: 0.55rem; letter-spacing:1px;">10. RISK CHECK</div>
                            <div class="d-flex justify-content-between text-success" style="font-size: 0.55rem;"><span>Contrarian</span><span>LOW</span></div>
                            <div class="d-flex justify-content-between text-success" style="font-size: 0.55rem;"><span>Position</span><span>LOW</span></div>
                            <div class="d-flex justify-content-between text-warning" style="font-size: 0.55rem;"><span>Event</span><span>MOD</span></div>
                        </div>

                        <!-- Panel 11: Invalidation -->
                        <div class="bg-dark-panel rounded border border-secondary p-2 d-flex flex-column">
                            <div class="text-muted mb-1" style="font-size: 0.55rem; letter-spacing:1px;">11. INVALIDATION</div>
                            <ul class="text-danger m-0 ps-3" style="font-size: 0.5rem;">
                                <li>Real Yield > +0.15%</li>
                                <li>DXY > 106.50</li>
                                <li>Break < 4310</li>
                            </ul>
                        </div>

                        <!-- Panel 12: Self-Learning -->
                        <div class="bg-dark-panel rounded border border-secondary p-2 d-flex flex-column text-center">
                            <div class="text-muted mb-1" style="font-size: 0.55rem; letter-spacing:1px;">12. ADAPTATION</div>
                            <div class="text-info mt-1" style="font-size: 0.6rem;">OOS Validation: PASS</div>
                            <div class="text-success fw-bold mt-auto" style="font-size: 0.65rem;">EDGE +2.3%</div>
                        </div>

                        <!-- Panel 13: Final Gate -->
                        <div class="bg-dark-panel rounded border border-success p-2 d-flex flex-column text-center" style="box-shadow: 0 0 10px rgba(0,255,0,0.2);">
                            <div class="text-success fw-bold mb-1" style="font-size: 0.7rem;"><i class="bi bi-check-circle"></i> TRADE ALLOWED</div>
                            <div class="d-flex justify-content-between" style="font-size: 0.55rem;"><span>Dir:</span><span class="text-success">UP</span></div>
                            <div class="d-flex justify-content-between" style="font-size: 0.55rem;"><span>Conf:</span><span>83%</span></div>
                            <div class="d-flex justify-content-between" style="font-size: 0.55rem;"><span>RR:</span><span>1:2.4</span></div>
                        </div>

                    </div>
                </div>
            </div>
"""

# Extract the old tab-v39-overview
start_idx = content.find('<div id="tab-v39-overview"')
if start_idx != -1:
    end_idx = content.find('<div id="tab-logs"', start_idx)
    content = content[:start_idx] + v39_grid + content[end_idx:]

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("V39 13-Panel Grid injected.")
