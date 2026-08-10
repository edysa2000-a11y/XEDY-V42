import re

notif_path = "backend/telegram/notifier.py"
with open(notif_path, "r", encoding="utf-8") as f:
    content = f.read()

v39_notify = """
    async def notify_v39_consensus(self, v39_data: dict, price: float, action: str):
        \"\"\"
        Special Telegram Notifier for V39 Causal Engine (17-Step Process).
        Broadcasts the internal state of the causal pipeline.
        \"\"\"
        event = v39_data.get("event", {})
        macro = v39_data.get("macro", {})
        flow = v39_data.get("flow", {})
        div = v39_data.get("div", {})
        gate = v39_data.get("gate", {})
        
        # Color coding
        gate_status = "🟢 TRADE ALLOWED" if gate.get("trade_allowed") else "🔴 TRADE BLOCKED"
        div_icon = "🟢" if div.get("divergence_risk", 0) < 30 else "🔴"
        flow_icon = "🟢" if flow.get("flow_regime") == "ACCUMULATION" else ("🔴" if flow.get("flow_regime") == "DISTRIBUTION" else "⚪")
        
        msg = (
            f"🚀 <b>XEDY V39 CAUSAL ENGINE ALERT</b>\n\n"
            f"💰 <b>Harga XAUUSD Saat Ini: ${price:.2f}</b>\n"
            f"🎯 <b>Rekomendasi Arah: {action}</b>\n\n"
            
            f"⚡ <b>① EVENT SHOCK</b>\n"
            f"• <i>{event.get('event_type', 'Normal')} Score: {event.get('shock_score', 0):.1f}/100</i>\n"
            f"• <i>Regime: {event.get('regime', 'Normal')}</i>\n\n"
            
            f"🏦 <b>② MACRO & YIELD</b>\n"
            f"• <i>Δ Yield: {macro.get('real_yield_change', 0):.2f}%</i>\n"
            f"• <i>DXY Strength: {macro.get('dxy_strength', 50):.1f}/100</i>\n"
            f"• <i>Bias: {macro.get('expected_direction', 'Neutral')}</i>\n\n"
            
            f"💸 <b>③ INSTITUTIONAL FLOW (PROXY)</b>\n"
            f"• <i>Flow Score: {flow.get('flow_score', 50):.1f}/100</i>\n"
            f"• <i>Regime: {flow_icon} {flow.get('flow_regime', 'NEUTRAL')}</i>\n\n"
            
            f"⚠️ <b>④ DIVERGENCE ENGINE</b>\n"
            f"• <i>Risk Penalty: {div_icon} {div.get('divergence_risk', 0):.1f}%</i>\n"
            f"• <i>Status: {div.get('status', 'ALIGNED')}</i>\n\n"
            
            f"🧠 <b>⑤ CONSENSUS GATE</b>\n"
            f"• <i>Raw Probability: {gate.get('raw_prob', 50):.1f}%</i>\n"
            f"• <i>Calibrated Prob: {gate.get('calibrated_prob', 50):.1f}%</i>\n"
            f"• <i>Expected Value: {gate.get('edge', 0):.2f}R</i>\n\n"
            
            f"🛡️ <b>FINAL DECISION:</b>\n"
            f"<b>{gate_status}</b>"
        )
        await self._send_safe(msg)
"""

if "def notify_v39_consensus" not in content:
    content = content.replace("    async def notify_risk_alert", v39_notify + "\n    async def notify_risk_alert")
    with open(notif_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("V39 Telegram Notifier injected.")
else:
    print("V39 Telegram Notifier already exists.")
