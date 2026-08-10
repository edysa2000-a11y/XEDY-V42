import re

app_path = "frontend/js/app.js"
with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """                const ascGate = document.getElementById('v39_asc_gate');
                if (ascGate) ascGate.innerText = v39.gate.trade_allowed ? "🟢 TRADE ALLOWED" : "🔴 TRADE BLOCKED";"""

new_logic = """                const ascGate = document.getElementById('v39_asc_gate');
                if (ascGate) ascGate.innerText = v39.gate.trade_allowed ? "🟢 TRADE ALLOWED" : "🔴 TRADE BLOCKED";
                
                // Add missing template wirings for V39 Engine Console Tab
                const elAscShock = document.getElementById('v39_asc_shock');
                if (elAscShock) elAscShock.innerText = v39.event.shock_score.toFixed(1);
                
                const elAscRyDir = document.getElementById('v39_asc_ry_dir');
                if (elAscRyDir) elAscRyDir.innerText = v39.macro.expected_direction.split(" ")[0];
                
                const elAscFlowVel = document.getElementById('v39_asc_flow_vel');
                if (elAscFlowVel) elAscFlowVel.innerText = Math.round(v39.flow.flow_velocity) + "/100";
                
                const elAscConf = document.getElementById('v39_asc_conf');
                if (elAscConf) elAscConf.innerText = Math.round(v39.gate.calibrated_prob) + "%";
                
                const elAscRegime = document.getElementById('v39_asc_regime');
                if (elAscRegime) elAscRegime.innerText = (v39.flow.flow_regime === "ACCUMULATION" ? "🟢 " : "🔴 ") + v39.flow.flow_regime;
                
                const elAscStatus = document.getElementById('v39_asc_status');
                if (elAscStatus) elAscStatus.innerText = (v39.div.divergence_risk < 30 ? "🟢 " : "🔴 ") + v39.div.status;
                
                const elAscConsensus = document.getElementById('v39_asc_consensus');
                if (elAscConsensus) elAscConsensus.innerText = (v39.gate.trade_allowed ? "🟢 " : "🔴 ") + v39.gate.raw_prob.toFixed(1) + "/100";
                
                // Missing fields in main tab
                const elFlowConf = document.getElementById('v39_flow_conf');
                if (elFlowConf) elFlowConf.innerText = Math.round(v39.flow.flow_score) + "%"; // Mocking flow confidence with flow score
"""

if "v39_asc_shock" not in content:
    content = content.replace(target, new_logic)
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("app.js patched to link all remaining V39 template IDs.")
else:
    print("Already patched.")
