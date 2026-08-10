import re

js_path = "frontend/js/app.js"
with open(js_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove mock
mock_start = content.find("// --- V39 ULTIMATE OVERVIEW MOCK DATA (Aesthetics) ---")
if mock_start != -1:
    content = content[:mock_start]

# 2. Add v39_data listener
v39_handler = """
            if (data.type === 'v39_data') {
                const v39 = data.data;
                // Panel 1: Causal Chain
                const elEvent = document.getElementById('v39_event_type');
                if (elEvent) elEvent.innerText = v39.event.event_type;
                const elImpact = document.getElementById('v39_event_impact');
                if (elImpact) elImpact.innerText = v39.event.regime;
                
                const elDxyDir = document.getElementById('v39_dxy_dir');
                if (elDxyDir) {
                    elDxyDir.innerText = v39.macro.expected_direction.split(" ")[0];
                    elDxyDir.style.color = v39.macro.expected_direction.includes("Bullish") ? "#00ffcc" : "#ff3366";
                }
                
                // Panel 3: Scorecard
                const elFlowScore = document.getElementById('v39_flow_score_txt');
                if (elFlowScore) elFlowScore.innerText = Math.round(v39.flow.flow_score) + "/100";
                const elDivRisk = document.getElementById('v39_div_risk');
                if (elDivRisk) elDivRisk.innerText = Math.round(v39.div.divergence_risk) + "%";
                const elRegime = document.getElementById('v39_flow_regime_txt');
                if (elRegime) elRegime.innerText = v39.flow.flow_regime + " PHASE";
                
                // Panel 4: Gauges
                const elStr = document.getElementById('v39_g_str');
                if (elStr) elStr.innerText = Math.round(v39.flow.flow_strength);
                const elVel = document.getElementById('v39_g_vel');
                if (elVel) elVel.innerText = Math.round(v39.flow.flow_velocity);
                const elAli = document.getElementById('v39_g_ali');
                if (elAli) elAli.innerText = Math.round(100 - v39.div.divergence_risk);
                
                const svgStr = document.getElementById('v39_svg_str');
                if (svgStr) {
                    // map 0-100 to 10-90 x coordinates roughly
                    let endX = 10 + (v39.flow.flow_strength * 0.8);
                    svgStr.setAttribute("d", `M 10 50 A 40 40 0 0 1 ${endX} 20`);
                }
                const svgVel = document.getElementById('v39_svg_vel');
                if (svgVel) {
                    let endX = 10 + (v39.flow.flow_velocity * 0.8);
                    svgVel.setAttribute("d", `M 10 50 A 40 40 0 0 1 ${endX} 25`);
                }
                
                // Gate & Prob
                const elProb = document.getElementById('v39_prob_txt');
                if (elProb) elProb.innerText = Math.round(v39.gate.calibrated_prob) + "%";
                
                const elGate = document.getElementById('v39_gate_txt');
                if (elGate) {
                    elGate.innerHTML = v39.gate.trade_allowed ? "TRADE<br>ALLOWED" : "TRADE<br>BLOCKED";
                    elGate.style.color = v39.gate.trade_allowed ? "#00ffcc" : "#ff3366";
                }
                
                // Console ASCII Sync
                const ascFlowStr = document.getElementById('v39_asc_flow_str');
                if (ascFlowStr) ascFlowStr.innerText = Math.round(v39.flow.flow_score) + "/100";
                
                const ascDivRisk = document.getElementById('v39_asc_div_risk');
                if (ascDivRisk) ascDivRisk.innerText = "🟢 " + Math.round(v39.div.divergence_risk) + "%";
                
                const ascGate = document.getElementById('v39_asc_gate');
                if (ascGate) ascGate.innerText = v39.gate.trade_allowed ? "🟢 TRADE ALLOWED" : "🔴 TRADE BLOCKED";
            }
"""

ws_target = "if (data.type === 'tick' && (data.symbol === 'XAUUSD' || !data.symbol)) {"
content = content.replace(ws_target, v39_handler + "\n            " + ws_target)

with open(js_path, "w", encoding="utf-8") as f:
    f.write(content)

print("V39 UI Listener wired.")
