import re

html_path = "frontend/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Inject Navigation Link into sidebar nav right below Money Flow V39
nav_target = '<li class="nav-item"><a class="nav-link" data-target="tab-moneyflow" href="#" style="color: #00ffaa;">💸 Money Flow V39</a></li>'
nav_replacement = nav_target + '\n                <li class="nav-item"><a class="nav-link" data-target="tab-scalping" href="#" style="color: #ffcc00; font-weight: bold;">⚡ Scalping Engine</a></li>'

if 'data-target="tab-scalping"' not in content:
    content = content.replace(nav_target, nav_replacement)
    print("Injected sidebar nav link for tab-scalping.")

# 2. Inject Tab HTML Container right before tab-tick
tab_scalping_html = """
            <!-- TAB SCALPING ENGINE (TICK VELOCITY & LIVE STRUCTURE) -->
            <div id="tab-scalping" class="spa-tab d-none h-100 w-100" style="padding: 1.25rem; background: #050b14; overflow-y: auto;">
                <!-- HEADER -->
                <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary">
                    <div>
                        <h4 class="text-white m-0 fw-bold"><i class="fas fa-bolt text-warning me-2"></i>⚡ Scalping Engine V42</h4>
                        <span class="text-muted small">Real-Time Tick Velocity, Market Structure (HH/HL/LH/LL) & Instant Gate</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge bg-dark text-info border border-info px-3 py-2" style="font-size: 0.8rem;">
                            <i class="fas fa-sync-alt fa-spin me-1"></i> TICK STREAM ACTIVE
                        </span>
                        <span class="badge bg-success px-3 py-2" id="scalp-eng-status-badge">SCALPER READY</span>
                    </div>
                </div>

                <!-- MAIN GRID CONTAINER -->
                <div class="row g-3">
                    <!-- TOP KPI ROW: REALTIME TICK & SPREAD SUMMARY -->
                    <div class="col-12">
                        <div class="card bg-dark-panel border-secondary">
                            <div class="card-body p-3 d-flex justify-content-between align-items-center text-center flex-wrap">
                                <div class="px-3 border-end border-secondary flex-fill mb-2 mb-md-0">
                                    <div class="text-muted small fw-bold text-uppercase">XAUUSD BID</div>
                                    <div class="h3 m-0 text-danger fw-bold" id="scalp-eng-bid">0.00</div>
                                </div>
                                <div class="px-3 border-end border-secondary flex-fill mb-2 mb-md-0">
                                    <div class="text-muted small fw-bold text-uppercase">XAUUSD ASK</div>
                                    <div class="h3 m-0 text-success fw-bold" id="scalp-eng-ask">0.00</div>
                                </div>
                                <div class="px-3 border-end border-secondary flex-fill mb-2 mb-md-0">
                                    <div class="text-muted small fw-bold text-uppercase">SPREAD (LIVE)</div>
                                    <div class="h3 m-0 text-warning fw-bold" id="scalp-eng-spread-live">0 pts <span class="fs-6 text-muted" id="scalp-eng-spread-pips">(0.0 pips)</span></div>
                                </div>
                                <div class="px-3 border-end border-secondary flex-fill mb-2 mb-md-0">
                                    <div class="text-muted small fw-bold text-uppercase">MIN / MAX SPREAD (5m)</div>
                                    <div class="h5 m-0 text-info fw-bold" id="scalp-eng-spread-range">0 / 0 pts</div>
                                </div>
                                <div class="px-3 flex-fill">
                                    <div class="text-muted small fw-bold text-uppercase">TICK SPEED (60s)</div>
                                    <div class="h3 m-0 text-primary fw-bold" id="scalp-eng-total-ticks-min">0 <span class="fs-6 text-muted">ticks/min</span></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- ROW 2: TREND & TICK VELOCITY (60s ROLLING) -->
                    <div class="col-md-6">
                        <div class="card bg-dark-panel border-secondary h-100">
                            <div class="card-header border-secondary bg-transparent d-flex justify-content-between align-items-center">
                                <span class="text-white fw-bold"><i class="fas fa-tachometer-alt text-warning me-2"></i>Scalping Trend & Momentum</span>
                                <span class="badge bg-primary" id="scalp-eng-trend-badge">ANALYZING</span>
                            </div>
                            <div class="card-body d-flex flex-column justify-content-between p-3">
                                <div class="text-center my-2">
                                    <div class="text-muted small text-uppercase mb-1">SCALPER BIAS & DIRECTION</div>
                                    <h2 class="fw-bold m-0" id="scalp-eng-trend-title" style="color: #00ffcc;">BULLISH SCALP</h2>
                                    <span class="text-muted small" id="scalp-eng-trend-sub">Strong Buyer Pressure (Momentum: 50%)</span>
                                </div>

                                <!-- TICK BUY / SELL PER MINUTE BARS -->
                                <div class="my-3 p-3 rounded" style="background: rgba(0,0,0,0.3); border: 1px solid #1a2b3c;">
                                    <div class="d-flex justify-content-between align-items-center mb-2" style="font-size: 0.85rem;">
                                        <span class="text-success fw-bold"><i class="fas fa-arrow-up me-1"></i>TICK BUY / MIN: <span id="scalp-eng-buy-min">0</span></span>
                                        <span class="text-danger fw-bold">TICK SELL / MIN: <span id="scalp-eng-sell-min">0</span> <i class="fas fa-arrow-down ms-1"></i></span>
                                    </div>
                                    <div class="progress" style="height: 22px; background: #330000; border-radius: 4px;">
                                        <div id="scalp-eng-buy-bar" class="progress-bar bg-success" role="progressbar" style="width: 50%; transition: width 0.3s;">50%</div>
                                        <div id="scalp-eng-sell-bar" class="progress-bar bg-danger" role="progressbar" style="width: 50%; transition: width 0.3s;">50%</div>
                                    </div>
                                    <div class="d-flex justify-content-between mt-2" style="font-size: 0.75rem;">
                                        <span class="text-muted">Net Tick Delta: <span id="scalp-eng-net-delta" class="fw-bold text-white">+0</span></span>
                                        <span class="text-muted">Buy Dominance: <span id="scalp-eng-buy-pct" class="fw-bold text-success">50%</span></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- ROW 2 RIGHT: MARKET STRUCTURE TRACKING (HH, LL, HL, LH) -->
                    <div class="col-md-6">
                        <div class="card bg-dark-panel border-secondary h-100">
                            <div class="card-header border-secondary bg-transparent d-flex justify-content-between align-items-center">
                                <span class="text-white fw-bold"><i class="fas fa-layer-group text-info me-2"></i>Market Structure (HH, HL, LH, LL)</span>
                                <span class="badge bg-secondary" id="scalp-eng-struct-state">STRUCTURE OK</span>
                            </div>
                            <div class="card-body p-3">
                                <div class="row g-2 text-center mb-3">
                                    <!-- HH -->
                                    <div class="col-6">
                                        <div class="p-2 rounded border" style="background: rgba(0,255,204,0.05); border-color: rgba(0,255,204,0.3) !important;">
                                            <div class="text-muted small fw-bold">HH (Higher High)</div>
                                            <div class="h4 m-0 fw-bold" style="color: #00ffcc;" id="scalp-eng-hh">0.00</div>
                                            <div class="text-muted" style="font-size: 0.65rem;" id="scalp-eng-hh-time">--:--:--</div>
                                        </div>
                                    </div>
                                    <!-- LH -->
                                    <div class="col-6">
                                        <div class="p-2 rounded border" style="background: rgba(255,153,0,0.05); border-color: rgba(255,153,0,0.3) !important;">
                                            <div class="text-muted small fw-bold">LH (Lower High)</div>
                                            <div class="h4 m-0 fw-bold" style="color: #ff9900;" id="scalp-eng-lh">0.00</div>
                                            <div class="text-muted" style="font-size: 0.65rem;" id="scalp-eng-lh-time">--:--:--</div>
                                        </div>
                                    </div>
                                    <!-- HL -->
                                    <div class="col-6">
                                        <div class="p-2 rounded border" style="background: rgba(0,204,255,0.05); border-color: rgba(0,204,255,0.3) !important;">
                                            <div class="text-muted small fw-bold">HL (Higher Low)</div>
                                            <div class="h4 m-0 fw-bold" style="color: #00ccff;" id="scalp-eng-hl">0.00</div>
                                            <div class="text-muted" style="font-size: 0.65rem;" id="scalp-eng-hl-time">--:--:--</div>
                                        </div>
                                    </div>
                                    <!-- LL -->
                                    <div class="col-6">
                                        <div class="p-2 rounded border" style="background: rgba(255,51,102,0.05); border-color: rgba(255,51,102,0.3) !important;">
                                            <div class="text-muted small fw-bold">LL (Lower Low)</div>
                                            <div class="h4 m-0 fw-bold" style="color: #ff3366;" id="scalp-eng-ll">0.00</div>
                                            <div class="text-muted" style="font-size: 0.65rem;" id="scalp-eng-ll-time">--:--:--</div>
                                        </div>
                                    </div>
                                </div>
                                <!-- STRUCTURE STATUS FOOTER -->
                                <div class="p-2 text-center rounded border border-secondary" style="background: #08101a;">
                                    <span class="text-muted small me-2">Structure Condition:</span>
                                    <span class="fw-bold" id="scalp-eng-struct-desc" style="color: #00ffcc;">🟢 HIGHER HIGH & HIGHER LOW (BULLISH)</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- ROW 3: FAST ACTION & SCALPING EXECUTION GATE -->
                    <div class="col-12">
                        <div class="card bg-dark-panel border-secondary">
                            <div class="card-header border-secondary bg-transparent d-flex justify-content-between align-items-center">
                                <span class="text-white fw-bold"><i class="fas fa-crosshairs text-danger me-2"></i>Instant Scalp Action & AI Gate</span>
                                <span class="badge bg-dark border border-warning text-warning" id="scalp-eng-gate-badge">SCALPER GATE: READY</span>
                            </div>
                            <div class="card-body p-3">
                                <div class="row align-items-center g-3">
                                    <div class="col-md-3">
                                        <label class="text-muted small fw-bold text-uppercase mb-1">Lot Size</label>
                                        <input type="number" id="scalp-eng-lot-input" class="form-control form-control-lg bg-dark text-white border-secondary text-center fw-bold" value="0.01" step="0.01" min="0.01">
                                    </div>
                                    <div class="col-md-3">
                                        <button class="btn btn-lg btn-danger w-100 fw-bold py-3" onclick="if(typeof window.executeScalping==='function') window.executeScalping('SELL');">
                                            <i class="fas fa-arrow-down me-2"></i>INSTANT SELL
                                        </button>
                                    </div>
                                    <div class="col-md-3">
                                        <button class="btn btn-lg btn-success w-100 fw-bold py-3" onclick="if(typeof window.executeScalping==='function') window.executeScalping('BUY');">
                                            <i class="fas fa-arrow-up me-2"></i>INSTANT BUY
                                        </button>
                                    </div>
                                    <div class="col-md-3 text-center">
                                        <div class="form-check form-switch d-inline-block text-start">
                                            <input class="form-check-input" type="checkbox" id="scalp-eng-auto-toggle" style="transform: scale(1.3); cursor: pointer;" onchange="if(typeof window.toggleAutoScalp==='function') window.toggleAutoScalp(this);">
                                            <label class="form-check-label text-white fw-bold ms-2" for="scalp-eng-auto-toggle">Auto Scalper AI</label>
                                        </div>
                                        <div class="text-muted small mt-1" id="scalp-eng-auto-status">AI Trigger: 60s Momentum & HH/LL Breakout</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                </div>
            </div>
"""

tab_tick_marker = '<!-- TICK (LEGACY) SUB-TAB -> SCALPER\'S TERMINAL -->'
if 'id="tab-scalping"' not in content:
    content = content.replace(tab_tick_marker, tab_scalping_html + '\n            ' + tab_tick_marker)
    print("Injected tab-scalping HTML container.")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("index.html update complete.")
