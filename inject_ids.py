import re

html_path = "frontend/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Inject IDs into tab-moneyflow (The 13 Panel Grid)
# We will do targeted string replacements on the specific lines I added in enlarge_font.py

replacements_moneyflow = {
    # Panel 1: Causal Chain
    '<span style="color:#ff3366; font-weight:bold;">CPI/PCE</span>': '<span id="v39_event_type" style="color:#ff3366; font-weight:bold;">CPI/PCE</span>',
    '<span style="color:#667788; font-size:0.65rem">Impact High</span>': '<span id="v39_event_impact" style="color:#667788; font-size:0.65rem">Impact High</span>',
    
    '<span style="color:#00ffcc; font-weight:bold;">Bullish</span><br><span style="color:#667788; font-size:0.65rem">Rate Cut Prob</span>': '<span id="v39_exp_dir" style="color:#00ffcc; font-weight:bold;">Bullish</span><br><span id="v39_exp_desc" style="color:#667788; font-size:0.65rem">Rate Cut Prob</span>',
    
    '<span style="color:#00ffcc; font-weight:bold;">Bullish</span><br><span style="color:#667788; font-size:0.65rem">US 10Y Down</span>': '<span id="v39_yield_dir" style="color:#00ffcc; font-weight:bold;">Bullish</span><br><span id="v39_yield_desc" style="color:#667788; font-size:0.65rem">US 10Y Down</span>',
    
    '<span style="color:#00ffcc; font-weight:bold;">Bullish</span><br><span style="color:#667788; font-size:0.65rem">DXY Melemah</span>': '<span id="v39_dxy_dir" style="color:#00ffcc; font-weight:bold;">Bullish</span><br><span id="v39_dxy_desc" style="color:#667788; font-size:0.65rem">DXY Melemah</span>',
    
    '<span style="color:#ffcc00; font-weight:bold;">Bullish</span><br><span style="color:#667788; font-size:0.65rem">Risk Off</span>': '<span id="v39_alloc_dir" style="color:#ffcc00; font-weight:bold;">Bullish</span><br><span id="v39_alloc_desc" style="color:#667788; font-size:0.65rem">Risk Off</span>',
    
    # Panel 3: Scorecard
    '<span>FLOW SCORE</span><span style="color:#00ffcc">88/100</span>': '<span>FLOW SCORE</span><span id="v39_flow_score_txt" style="color:#00ffcc">88/100</span>',
    '<span>FLOW CONFIDENCE</span><span style="color:#00ffcc">91%</span>': '<span>FLOW CONFIDENCE</span><span id="v39_flow_conf" style="color:#00ffcc">91%</span>',
    '<span>DIVERGENCE RISK</span><span>18%</span>': '<span>DIVERGENCE RISK</span><span id="v39_div_risk">18%</span>',
    'ACCUMULATION PHASE': '<span id="v39_flow_regime_txt">ACCUMULATION PHASE</span>',
    
    # Panel 4: Gauges
    'Strength: <span style="color:#00ffcc; font-weight:bold;">88</span>': 'Strength: <span id="v39_g_str" style="color:#00ffcc; font-weight:bold;">88</span>',
    'Velocity: <span style="color:#00ffcc; font-weight:bold;">94</span>': 'Velocity: <span id="v39_g_vel" style="color:#00ffcc; font-weight:bold;">94</span>',
    'Persist: <span style="color:#ff9900; font-weight:bold;">72</span>': 'Persist: <span id="v39_g_per" style="color:#ff9900; font-weight:bold;">72</span>',
    'Align: <span style="color:#00ffcc; font-weight:bold;">85</span>': 'Align: <span id="v39_g_ali" style="color:#00ffcc; font-weight:bold;">85</span>',
    
    # Panel 7, 9, 10, 11, 13
    '<div style="color: #00ffcc; font-size: 1.5rem; font-weight: bold;">78%</div>': '<div id="v39_prob_txt" style="color: #00ffcc; font-size: 1.5rem; font-weight: bold;">78%</div>',
    '<div style="color: #00ffcc; font-size: 0.9rem; font-weight: bold; margin-bottom: 0.3rem;">TRADE<br>ALLOWED</div>': '<div id="v39_gate_txt" style="color: #00ffcc; font-size: 0.9rem; font-weight: bold; margin-bottom: 0.3rem;">TRADE<br>ALLOWED</div>',
    '<div style="font-size: 0.7rem; font-weight:bold;">UP | RR 1:2.4</div>': '<div id="v39_gate_rr" style="font-size: 0.7rem; font-weight:bold;">UP | RR 1:2.4</div>',
    
    # SVG progress bars
    '<div class="progress-bar" style="width: 80%; background: #00ffcc;"></div>': '<div id="v39_bar_1" class="progress-bar" style="width: 80%; background: #00ffcc; transition: width 0.5s;"></div>',
    '<div class="progress-bar" style="width: 70%; background: #00ffcc;"></div>': '<div id="v39_bar_2" class="progress-bar" style="width: 70%; background: #00ffcc; transition: width 0.5s;"></div>',
    '<div class="progress-bar" style="width: 40%; background: #00ffcc;"></div>': '<div id="v39_bar_3" class="progress-bar" style="width: 40%; background: #00ffcc; transition: width 0.5s;"></div>',
    '<div class="progress-bar" style="width: 50%; background: #00ffcc;"></div>': '<div id="v39_bar_4" class="progress-bar" style="width: 50%; background: #00ffcc; transition: width 0.5s;"></div>',
    
    # SVGs for Gauges (Adding IDs to paths)
    '<path d="M 10 50 A 40 40 0 0 1 80 20" fill="none" stroke="#00ffcc" stroke-width="12"/>': '<path id="v39_svg_str" d="M 10 50 A 40 40 0 0 1 80 20" fill="none" stroke="#00ffcc" stroke-width="12" style="transition: all 0.5s;"/>',
    '<path d="M 10 50 A 40 40 0 0 1 85 25" fill="none" stroke="#00ffcc" stroke-width="12"/>': '<path id="v39_svg_vel" d="M 10 50 A 40 40 0 0 1 85 25" fill="none" stroke="#00ffcc" stroke-width="12" style="transition: all 0.5s;"/>',
    '<path d="M 10 50 A 40 40 0 0 1 60 15" fill="none" stroke="#ff9900" stroke-width="12"/>': '<path id="v39_svg_per" d="M 10 50 A 40 40 0 0 1 60 15" fill="none" stroke="#ff9900" stroke-width="12" style="transition: all 0.5s;"/>',
    '<path d="M 10 50 A 40 40 0 0 1 70 15" fill="none" stroke="#00ffcc" stroke-width="12"/>': '<path id="v39_svg_ali" d="M 10 50 A 40 40 0 0 1 70 15" fill="none" stroke="#00ffcc" stroke-width="12" style="transition: all 0.5s;"/>',
}

for k, v in replacements_moneyflow.items():
    content = content.replace(k, v)
    
# 2. Inject IDs into tab-moneyflow-engine (The ASCII block)
# We will wrap the numbers in <span id="..."> without breaking the ASCII alignment.
ascii_replacements = {
    'EVENT SHOCK SCORE                                            ║': 'EVENT SHOCK SCORE                    <span id="v39_asc_shock">30.0</span>                    ║',
    'Real Yield Direction │ Velocity │ Acceleration │ Gold Sensitivity            ║': 'Real Yield Direction │ Velocity │ Acceleration │ Gold Sensitivity            ║\n║        <span id="v39_asc_ry_dir">Bullish</span>     │  <span id="v39_asc_ry_vel">Low</span>     │    <span id="v39_asc_ry_acc">Low</span>       │       <span id="v39_asc_ry_gs">High</span>                  ║',
    'FLOW STRENGTH       ██████████████████░░  88/100                             ║': 'FLOW STRENGTH       ██████████████████░░  <span id="v39_asc_flow_str">88/100</span>                             ║',
    'FLOW VELOCITY       ███████████████████░  94/100                             ║': 'FLOW VELOCITY       ███████████████████░  <span id="v39_asc_flow_vel">94/100</span>                             ║',
    'CAUSAL CONFIDENCE   ██████████████████░░  89%                                ║': 'CAUSAL CONFIDENCE   ██████████████████░░  <span id="v39_asc_conf">89%</span>                                ║',
    'FLOW REGIME         🟢 ACCUMULATION                                          ║': 'FLOW REGIME         <span id="v39_asc_regime">🟢 ACCUMULATION</span>                                          ║',
    'DIVERGENCE RISK                         🟢 18%                               ║': 'DIVERGENCE RISK                         <span id="v39_asc_div_risk">🟢 18%</span>                               ║',
    'FLOW / PRICE STATUS                     🟢 ALIGNED                           ║': 'FLOW / PRICE STATUS                     <span id="v39_asc_status">🟢 ALIGNED</span>                           ║',
    'Current Regime: 🟢 BULL TREND                                                ║': 'Current Regime: <span id="v39_asc_macro_regime">🟢 BULL TREND</span>                                                ║',
    'CONSENSUS SCORE                         🟢 85.7/100                          ║': 'CONSENSUS SCORE                         <span id="v39_asc_consensus">🟢 85.7/100</span>                          ║',
    'CALIBRATED PROBABILITY                🟢 76%                                 ║': 'CALIBRATED PROBABILITY                <span id="v39_asc_cal_prob">🟢 76%</span>                                 ║',
    'Expected Value                         🟢 +0.82R                             ║': 'Expected Value                         <span id="v39_asc_ev">🟢 +0.82R</span>                             ║',
    '                       🟢 TRADE ALLOWED                                       ║': '                       <span id="v39_asc_gate">🟢 TRADE ALLOWED</span>                                       ║',
}

for k, v in ascii_replacements.items():
    content = content.replace(k, v)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("IDs injected into HTML.")
