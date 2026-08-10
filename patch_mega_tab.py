import re

html_path = "frontend/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

v39_tab = """            <!-- V39 ULTIMATE OVERVIEW TAB -->
            <div id="tab-v39-overview" class="spa-tab d-none">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h5 class="mb-0 text-white" style="text-transform: uppercase; letter-spacing: 2px;">🌟 V39 Ultimate Overview</h5>
                    <span class="badge bg-success" style="font-size: 0.8rem; padding: 0.5rem 1rem;">STATUS: LIVE TRADING</span>
                </div>

                <!-- ROW 1: INTELLIGENCE CORE -->
                <h6 class="text-muted mb-3" style="font-size: 0.85rem;">INTELLIGENCE CORE (CAUSAL ENGINE)</h6>
                <div class="row g-3 mb-4">
                    <div class="col-md-4">
                        <div class="bg-dark-panel p-4 rounded h-100 border border-secondary text-center" style="box-shadow: 0 0 20px rgba(0, 255, 170, 0.1);">
                            <div class="text-muted mb-2" style="font-size: 0.75rem; letter-spacing: 1px;">CAUSAL CONFIDENCE</div>
                            <div class="text-white fw-bold mb-1" style="font-size: 2.5rem; text-shadow: 0 0 10px rgba(0,255,170,0.5);" id="v39-confidence">--%</div>
                            <div class="badge bg-dark border border-success text-success" id="v39-signal-status">WAITING CONFIRMATION</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="bg-dark-panel p-4 rounded h-100 border border-secondary text-center" style="box-shadow: 0 0 20px rgba(255, 87, 34, 0.1);">
                            <div class="text-muted mb-2" style="font-size: 0.75rem; letter-spacing: 1px;">DIVERGENCE PENALTY</div>
                            <div class="text-warning-v42 fw-bold mb-1" style="font-size: 2.5rem; text-shadow: 0 0 10px rgba(255, 87, 34, 0.5);" id="v39-divergence">0%</div>
                            <div class="badge bg-dark border border-warning text-warning" id="v39-divergence-status">ALIGNED</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="bg-dark-panel p-4 rounded h-100 border border-secondary text-center" style="box-shadow: 0 0 20px rgba(255, 193, 7, 0.1);">
                            <div class="text-muted mb-2" style="font-size: 0.75rem; letter-spacing: 1px;">SIDEWAYS FILTER</div>
                            <div class="text-white fw-bold mb-1" style="font-size: 2.5rem;" id="v39-sideways-atr">--</div>
                            <div class="badge bg-dark border border-secondary text-secondary" id="v39-sideways-status">DETECTING...</div>
                        </div>
                    </div>
                </div>

                <!-- ROW 2: HOLY GRAIL MATRIX -->
                <h6 class="text-muted mb-3" style="font-size: 0.85rem;">HOLY GRAIL MATRIX (MULTI-TIMEFRAME)</h6>
                <div class="row g-3 mb-4">
                    <div class="col-12">
                        <div class="bg-dark-panel p-4 rounded border border-secondary">
                            <div class="d-flex justify-content-between text-center">
                                <div class="flex-fill">
                                    <div class="text-muted mb-1" style="font-size: 0.75rem;">M15 (MICRO)</div>
                                    <div class="badge bg-secondary p-2 w-75" id="v39-m15-trend">WAIT</div>
                                </div>
                                <div class="flex-fill border-start border-secondary">
                                    <div class="text-muted mb-1" style="font-size: 0.75rem;">H1 (INTRADAY)</div>
                                    <div class="badge bg-secondary p-2 w-75" id="v39-h1-trend">WAIT</div>
                                </div>
                                <div class="flex-fill border-start border-secondary">
                                    <div class="text-muted mb-1" style="font-size: 0.75rem;">H4 (SWING)</div>
                                    <div class="badge bg-secondary p-2 w-75" id="v39-h4-trend">WAIT</div>
                                </div>
                                <div class="flex-fill border-start border-secondary">
                                    <div class="text-muted mb-1" style="font-size: 0.75rem;">D1 (MACRO)</div>
                                    <div class="badge bg-secondary p-2 w-75" id="v39-d1-trend">WAIT</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ROW 3: LIVE PERFORMANCE -->
                <h6 class="text-muted mb-3" style="font-size: 0.85rem;">LIVE EXECUTION & PERFORMANCE (TARGET: 3% PROFIT/DAY)</h6>
                <div class="row g-3">
                    <div class="col-md-3">
                        <div class="bg-dark-panel p-3 rounded h-100 border border-secondary text-center">
                            <div class="text-muted mb-2" style="font-size: 0.75rem;">DAILY PROFIT</div>
                            <div class="text-success fw-bold" style="font-size: 1.8rem;" id="v39-daily-profit">$0.00</div>
                            <div class="progress mt-2" style="height: 5px;">
                                <div class="progress-bar bg-success" role="progressbar" style="width: 0%;" id="v39-profit-bar"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="bg-dark-panel p-3 rounded h-100 border border-secondary text-center">
                            <div class="text-muted mb-2" style="font-size: 0.75rem;">CURRENT DRAWDOWN</div>
                            <div class="text-warning fw-bold" style="font-size: 1.8rem;" id="v39-current-dd">0.00%</div>
                            <div class="text-muted mt-1" style="font-size: 0.7rem;">Limit: 10.0%</div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="bg-dark-panel p-3 rounded h-100 border border-secondary">
                            <div class="text-muted mb-2" style="font-size: 0.75rem;">LIVE TRADE LOG (SL 1.5 ATR | TP 1.2 ATR)</div>
                            <div class="bg-black p-2 rounded" style="height: 80px; overflow-y: auto;">
                                <table class="table table-sm table-dark table-borderless m-0" style="font-size: 0.75rem;">
                                    <tbody id="v39-trade-logs">
                                        <tr><td class="text-muted text-center py-3">Tidak ada transaksi hari ini</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
"""

content = content.replace('            <div id="tab-logs" class="spa-tab d-none">', v39_tab + '\n            <div id="tab-logs" class="spa-tab d-none">')

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("V39 Ultimate Overview tab injected.")
