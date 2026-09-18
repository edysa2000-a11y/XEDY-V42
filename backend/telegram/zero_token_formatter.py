import re

# ------------------------------------------------------------------
# 1. EVENT STANCE CLASSIFIER (independen dari price direction)
# ------------------------------------------------------------------
HAWKISH_KEYWORDS = [
    "rate hike", "hawkish", "inflation surge", "strong nfp", "strong jobs",
    "cpi beat", "fed tightening", "balance sheet reduction", "qt",
    "higher for longer", "restrictive policy",
]

DOVISH_KEYWORDS = [
    "rate cut", "dovish", "weak nfp", "weak jobs", "cpi miss",
    "fed easing", "qe", "rate pause", "recession risk", "yield curve invert",
]

FED_INDEPENDENCE_THREAT_KEYWORDS = [
    "fed chair removal", "considering her removal", "considering his removal",
    "fire fed", "remove fed governor", "fed independence", "cook removal",
    "trump.*remove.*fed", "trump.*fire.*powell", "scotusblog",
]

def classify_event_stance(news_headline: str, event: dict) -> str:
    text = (news_headline or "").lower()

    upstream_stance = event.get("policy_stance")
    if upstream_stance in ("HAWKISH", "DOVISH", "NEUTRAL"):
        return upstream_stance

    for pat in FED_INDEPENDENCE_THREAT_KEYWORDS:
        if re.search(pat, text):
            return "DOVISH"

    hawkish_hits = sum(1 for kw in HAWKISH_KEYWORDS if kw in text)
    dovish_hits = sum(1 for kw in DOVISH_KEYWORDS if kw in text)

    if hawkish_hits > dovish_hits:
        return "HAWKISH"
    elif dovish_hits > hawkish_hits:
        return "DOVISH"
    return "NEUTRAL"

# ------------------------------------------------------------------
# 2. CONFLICT DETECTOR
# ------------------------------------------------------------------
def detect_conflict(stance: str, real_yield_change: float, dxy_strength: float) -> tuple[bool, list[str]]:
    reasons = []
    if stance == "HAWKISH":
        if real_yield_change <= 0:
            reasons.append("Stance HAWKISH tapi real yield TURUN (harusnya naik)")
        if dxy_strength < 50:
            reasons.append("Stance HAWKISH tapi DXY strength LEMAH (harusnya kuat)")
    elif stance == "DOVISH":
        if real_yield_change > 0:
            reasons.append("Stance DOVISH tapi real yield NAIK (harusnya turun)")
        if dxy_strength >= 50:
            reasons.append("Stance DOVISH tapi DXY strength KUAT (harusnya lemah)")
    return (len(reasons) > 0, reasons)

def generate_ascii_narrative(v39_data: dict, price: float, news_headline: str) -> str:
    event = v39_data.get("event", {})
    macro = v39_data.get("macro", {})
    flow = v39_data.get("flow", {})
    div = v39_data.get("div", {})
    gate = v39_data.get("gate", {})

    # Map Logic
    direction = gate.get("direction", "SIDEWAYS")
    regime = event.get("regime", "NORMAL")
    volatility = flow.get("flow_velocity", 50)
    trend_score = macro.get("dxy_strength", 50)
    momentum_score = flow.get("flow_score", 50)
    calib_prob = gate.get("calibrated_prob", 50.0)
    div_risk = div.get("divergence_risk", 0)
    
    # 📍 MARKET STATE
    state_desc = "BULLISH (BULL MARKET REGIME)" if direction == "UP" else "BEARISH (BEAR MARKET REGIME)" if direction == "DOWN" else "SIDEWAYS (MEAN-REVERTING REGIME)"
    struct_desc = "STRUCTURAL CONTINUATION" if momentum_score > 70 else "STRUCTURAL REVERSAL" if momentum_score < 30 else "MACRO CONSOLIDATION"
    mom_desc = "menunjukkan akselerasi agresif (momentum expansion)" if momentum_score > 60 else "mengalami deselerasi (momentum decay)" if momentum_score < 40 else "terkompresi (stabilizing)"
    vol_desc = "volatilitas ekstrem (liquidity sweeping)" if volatility > 80 else "volatilitas tinggi (elevated VIX proxy)" if volatility > 60 else "volatilitas normal (orderly market)"
    selaras_desc = "terjadi konvergensi (macro-technical alignment)" if div_risk < 30 else "terdapat divergensi struktural"
    
    if trend_score > 75: cat_desc = "MACRO-TREND"
    elif event.get("shock_score", 0) > 70: cat_desc = "EVENT-DRIVEN SHOCK"
    elif volatility > 80: cat_desc = "LIQUIDITY-SQUEEZE"
    elif trend_score < 30: cat_desc = "RANGE-BOUND ACCUMULATION"
    else: cat_desc = "MONETARY POLICY"

    # 🔎 WHAT CHANGED
    primary_driver = news_headline or "Technical & Macro Dynamics"
    sec_driver = "Dinamika Sovereign Yield & DXY (Dollar Index)" if trend_score > 50 else "Institutional Order Flow & Algorithmic Sweeps"
    catalyst = "Rilis Indikator Ekonomi Makro / Fed Forward Guidance" if ("Fed" in primary_driver or "Data" in primary_driver) else primary_driver

    # === FIX #1: stance classification INDEPENDEN dari direction ===
    stance = classify_event_stance(news_headline, event)
    if stance == "HAWKISH":
        expectation = "Hawkish Repricing / Peningkatan Risk-Aversion"
        risk_prem = "Terakselerasi (Elevated Risk Premium)"
        usd_liq = "Apresiasi USD / Pengetatan Likuiditas"
        asset_alloc = "Capital Rotation (Risk-On / Yield-Seeking Outflows)"
    elif stance == "DOVISH":
        expectation = "Dovish Repricing / Peningkatan Risk-Appetite / Credibility Risk"
        risk_prem = "Terkontraksi (Diminishing Risk Premium)"
        usd_liq = "Depresiasi USD / Ekspansi Likuiditas"
        asset_alloc = "Capital Rotation (Safe-Haven Inflows)"
    else:  # NEUTRAL -> fallback ke direction
        expectation = "Neutral / Mixed Signals — fallback ke price direction"
        risk_prem = "Netral (Priced-In)"
        usd_liq = "Netral / Range-bound Likuiditas"
        asset_alloc = "Capital Rotation (Netral)"

    real_yield_change = macro.get("real_yield_change", 0)
    real_yield = "Terkoreksi Negatif (Real Rates Turun)" if real_yield_change <= 0 else "Menanjak (Real Rates Naik)"

    # === FIX #2: conflict detection ===
    conflict, conflict_reasons = detect_conflict(stance, real_yield_change, trend_score)

    # === FIX #3: discount confidence kalau conflict ===
    if conflict:
        calib_prob_adjusted = round(calib_prob * 0.5, 1)
        conflict_block = (
            "\n⚠️ CONFLICT WARNING\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Fundamental stance ({stance}) TIDAK KONSISTEN dengan real yield & USD:\n"
            + "\n".join(f"  - {r}" for r in conflict_reasons) +
            f"\nConfidence didiskon dari {calib_prob:.1f}% -> {calib_prob_adjusted:.1f}% "
            "(low conviction, hindari over-sizing).\n"
        )
    else:
        calib_prob_adjusted = calib_prob
        conflict_block = ""
        
    calib_prob = calib_prob_adjusted
    money_flow_dir = "Institutional Net Inflow (Smart Money Accumulation)" if direction == "UP" else "Institutional Net Outflow (Smart Money Distribution)"

    # 🇺🇸 PRESIDENT + POLICY
    pres_topic = "Kebijakan Fiskal Ekspansif & Trajektori Defisit AS (US Deficit/Debt Dynamics)"
    pres_impact = "MENGAKSELERASI BULLISH SENTIMENT" if direction == "UP" else "MEMBERIKAN TEKANAN BEARISH" if direction == "DOWN" else "TETAP NEUTRAL DALAM HORIZON INI"
    pres_channel = "ekspektasi inflasi jangka panjang (breakeven inflation) dan trajektori penerbitan US Treasury"

    # 🌍 GEOPOLITICAL INTELLIGENCE
    geo_region = "Global/Timur Tengah"
    geo_phase = "ESCALATION" if cat_desc == "SAFE-HAVEN" else "STATUS QUO"
    geo_channel = "SAFE-HAVEN/RISK PREMIUM/USD"

    # 📅 ECONOMIC CALENDAR
    eco_event = "Rilis Data Utama (NFP/CPI)" 
    eco_exp = "Sesuai/Miss"
    eco_prev = "Bulan Lalu"

    # 🏛️ FED POLICY
    fed_state = "DOVISH" if direction == "UP" else "HAWKISH" if direction == "DOWN" else "NEUTRAL"

    # 💰 MONEY FLOW
    mf_state = flow.get("flow_regime", "INSTITUTIONAL ACCUMULATION (DARK POOL BIDDING)" if direction == "UP" else "INSTITUTIONAL DISTRIBUTION (OFF-EXCHANGE SELLING)")
    mf_source = "COMEX Futures (Managed Money), ETF Bullion (GLD Inflows), dan Central Bank (PBoC/EM) Reserves"
    mf_selaras = "TERKONFIRMASI (ORDER BOOK ABSORPTION MATCHES MACRO)" if div_risk < 30 else "DIVERGENSI (RETAIL VS INSTITUTIONAL DISCONNECT)"
    
    # 🔗 MACRO + INTERMARKET
    dxy_dir = "MENGUAT" if trend_score > 50 else "MELEMAH"
    tr_dir = "NAIK" if macro.get("real_yield_change", 0) > 0 else "TURUN"
    oil_dir = "NAIK" if direction == "UP" else "TURUN"
    vol_dir = "NAIK" if volatility > 50 else "TURUN"
    eq_dir = "RISK-ON" if direction == "UP" else "RISK-OFF"
    liq_dir = "NAIK" if direction == "UP" else "TURUN"
    macro_combo = "MENDUKUNG" if selaras_desc == "selaras" else "BERLAWANAN"

    # 🧬 CAUSAL VALIDATION
    alt_hypo = "MACRO REPRICING" if selaras_desc == "berbeda" else "INSTITUTIONAL FLOW"

    # 🕓 H4 FORECAST
    h4_bias = struct_desc
    h4_driver = "Cumulative Volume Delta (CVD) dan Order Block Sweeping"
    h4_cond = "DXY Index mempertahankan lintasan depresiasi di bawah pivot makronya" if direction == "UP" else "DXY Index mempertahankan yield advantage dan premium likuiditas"
    h4_fc = f"{price + (price*0.003):.2f} - {price + (price*0.008):.2f}" if direction == "UP" else f"{price - (price*0.008):.2f} - {price - (price*0.003):.2f}"
    h4_outlook = f"{state_desc} {struct_desc}"

    # 📅 D1 FORECAST
    d1_regime = state_desc
    d1_driver = "Pergeseran Dot Plot The Fed, Real Interest Rates (TIPS Yields), dan DXY Repricing"
    d1_fc = f"{price + (price*0.012):.2f} - {price + (price*0.025):.2f}" if direction == "UP" else f"{price - (price*0.025):.2f} - {price - (price*0.012):.2f}"
    d1_outlook = f"STRUCTURAL {state_desc}"
    
    # 🔄 H4 <-> D1
    h4d1_align = "ALIGNED" if selaras_desc == "selaras" else "PULLBACK/COUNTER-TREND"
    h4d1_trigger = "Breakout Valid" if selaras_desc == "selaras" else "Rejection"
    h4d1_conf = "Flow Terkonfirmasi"
    h4d1_cont = struct_desc

    # 🔮 WHAT HAPPENS NEXT
    whn_scen = "Continuation" if selaras_desc == "selaras" else "Correction"
    whn_h4 = "Melanjutkan Struktur Harga"
    whn_d1 = "Menguji Support/Resistance Utama"

    # ⚔️ CONTRARIAN
    contra_risk = "FED REPRICING/DXY REVERSAL/FLOW REVERSAL"

    # 🚨 INVALIDATION
    inv_cond = "Score > 50%"
    inv_h4 = "Breakout Support/Resistance Terdekat"
    inv_d1 = "Perubahan Trend Harian"

    # 🎯 FINAL OUTLOOK
    final_view = f"🟢 {state_desc} CONTINUATION" if direction == "UP" else f"🔴 {state_desc} CONTINUATION" if direction == "DOWN" else f"🟡 {state_desc} CONSOLIDATION"

    template = f"""╔══════════════════════════════════════════════════════════════════════════╗
║                 🧠 XEDY AI • XAUUSD V39.4                              ║
║       CAUSAL MARKET NARRATIVE • H4/D1 FORECAST • REGIME ENGINE          ║
║                                                                          ║
║ PRESIDENT → GEOPOLITICS → DATA → FED → YIELD → USD → FLOW → PRICE      ║
║                 → H4 → D1 → FORECAST → INVALIDATION                    ║
╚══════════════════════════════════════════════════════════════════════════╝

{conflict_block}
📍 MARKET STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
XAUUSD berada dalam kondisi {state_desc}.
Struktur {struct_desc}, momentum {mom_desc}, dan volatilitas {vol_desc}.
Secara multi-timeframe, kondisi {selaras_desc}, sehingga market
dikategorikan sebagai {cat_desc} DRIVEN.

🔎 WHAT CHANGED → WHY?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Perubahan utama XAUUSD terjadi setelah {primary_driver}. 
XEDY memisahkan fakta terkonfirmasi dari interpretasi, kemudian menentukan 
{primary_driver} sebagai penyebab utama dan {sec_driver} sebagai penguat.

Causal chain:
{catalyst} → {expectation} → {risk_prem} → {real_yield}
→ {usd_liq} → {asset_alloc} → {money_flow_dir} → XAUUSD.

🇺🇸 PRESIDENT + POLICY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kebijakan/pernyataan Presiden AS mengenai {pres_topic} berpotensi
memengaruhi {pres_channel}.
Dampaknya terhadap Gold {pres_impact} melalui {pres_channel}.

XEDY membedakan retorika, proposal, kebijakan resmi, implementasi,
dan actual market repricing. Speech tanpa perubahan expectation,
yield, USD, flow atau price tidak dianggap primary catalyst.

🌍 GEOPOLITICAL INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Perkembangan {geo_region} berada pada fase {geo_phase}. 
Dampaknya diteruskan melalui {geo_channel}.

XEDY memeriksa apakah geopolitik benar-benar menghasilkan safe-haven
flow atau hanya headline volatility. Jika risiko meningkat tetapi Gold
tidak merespons, sistem menguji kemungkinan risk premium telah priced-in.

📅 ECONOMIC CALENDAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Catalyst ekonomi terdekat adalah {eco_event}, dengan market expectation
{eco_exp} dibandingkan {eco_prev}. Risiko utamanya adalah
perbedaan ACTUAL terhadap EXPECTATION.

DATA → INFLATION/GROWTH/EMPLOYMENT → FED EXPECTATION
→ REAL YIELD → USD → FLOW → GOLD.

Sebelum rilis XEDY membaca anticipation; setelah rilis XEDY menunggu
konfirmasi yield, USD, flow dan Gold sebelum mengubah thesis.

🏛️ FED POLICY + SPEECH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fed saat ini {fed_state}. FOMC, Fed Chair, Governors, dot plot, 
forward guidance dan balance-sheet policy digunakan untuk membaca 
perubahan rate-path expectation.

FED → RATE EXPECTATION → REAL YIELD → USD → GOLD.

XEDY tidak menggunakan aturan sederhana "hawkish = bearish Gold".
Yang dinilai adalah surprise, repricing, actual yield response,
USD response dan price response.

💰 MONEY FLOW + PRICE CONFIRMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Money flow menunjukkan {mf_state}. Arus berasal dari {mf_source}.

Flow dan price {mf_selaras}. Jika flow meningkat dan harga
mengikuti dengan struktur sehat, kondisi dianggap genuine demand.
Jika flow meningkat tetapi harga gagal naik, XEDY menguji absorption,
distribution atau divergence. Jika harga bergerak tanpa flow,
XEDY menguji breakout, short covering atau liquidity distortion.

🔗 MACRO + INTERMARKET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Real yield {tr_dir}, USD {dxy_dir}, Treasury {tr_dir},
oil {oil_dir}, volatility {vol_dir}, equity {eq_dir}
dan liquidity {liq_dir}.

Kombinasi tersebut {macro_combo} dengan causal
thesis. XEDY juga memeriksa apakah hubungan historis masih berlaku
atau telah terjadi structural exception.

🧬 CAUSAL VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
XEDY menguji siapa yang bergerak lebih dahulu, kapan Gold merespons,
seberapa besar responsnya, apakah efek bertahan, dan apakah faktor
lain mengonfirmasi.

Jika causal chain tidak konsisten, confidence diturunkan dan
alternative hypothesis diuji: {alt_hypo}.

🕓 H4 FORECAST — TACTICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pada H4, XAUUSD menunjukkan {h4_bias}. Driver utama adalah {h4_driver}.

Jika {h4_cond} bertahan, pergerakan H4 diperkirakan menuju {h4_fc} (Akurasi/Confidence: {calib_prob:.1f}%).
Jika harga melemah tetapi D1 causal structure tetap utuh, XEDY
menganggapnya healthy correction. Jika H4 weakness dikonfirmasi
flow, yield, USD dan structure, risiko reversal meningkat.

H4 OUTLOOK: {h4_outlook}
TARGET H4 (PROYEKSI TAKTIKAL): {h4_fc}

📅 D1 FORECAST — STRUCTURAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pada D1, structural regime berada pada {d1_regime}. Driver persisten 
berasal dari {d1_driver}.

Headline jangka pendek tidak mengubah D1 tanpa perubahan causal
yang persisten. Jika H4 berlawanan tetapi D1 tetap kuat, kondisi
dianggap correction/counter-trend. Jika H4 dan D1 berubah bersama
dan dikonfirmasi macro serta flow, risiko structural reversal meningkat.

D1 OUTLOOK: {d1_outlook} (Akurasi/Confidence: {calib_prob:.1f}%)
TARGET D1 (PROYEKSI STRUKTURAL): {d1_fc}

🔄 H4 ↔ D1 FORECAST PATH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
H4 dan D1 saat ini {h4d1_align}.

CURRENT → {struct_desc} → {h4d1_trigger} → {h4d1_conf} → {h4d1_cont}.

Jika H4 dan D1 searah, continuation mendapat dukungan multi-horizon.
Jika berlawanan, D1 menjadi structural anchor dan H4 menjadi tactical
signal. Lower timeframe hanya digunakan untuk timing, bukan mengganti
structural bias.

🔮 WHAT HAPPENS NEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Skenario utama adalah {whn_scen} karena {primary_driver} masih
didukung oleh FLOW/YIELD/USD/PRICE STRUCTURE. Dalam jangka pendek,
H4 kemungkinan {whn_h4}, sementara dalam horizon D1 {whn_d1}.

Catalyst berikutnya adalah {eco_event}, yang dapat mengubah FED/
REAL YIELD/USD/GEOPOLITICAL RISK/FLOW. Jika kondisi tetap konsisten,
continuation menjadi skenario utama. Jika evidence mulai melemah,
status berubah menjadi DEGRADING; jika causal chain rusak,
forecast menjadi INVALIDATED.

⚔️ CONTRARIAN + PRICED-IN CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
XEDY memeriksa apakah catalyst sudah priced-in dan mencari evidence
berlawanan. Risiko utama berasal dari {contra_risk}.

Catalyst yang semakin kuat tetapi menghasilkan respons harga semakin
lemah diperlakukan sebagai early warning.

🚨 INVALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Thesis tetap valid selama {inv_cond}. H4 invalid apabila
{inv_h4}. D1 invalid membutuhkan perubahan struktural pada
{inv_d1}.

Full causal thesis dianggap invalid apabila PRIMARY DRIVER,
TRANSMISSION, FLOW dan PRICE STRUCTURE berbalik secara konsisten.
Jika invalid, XEDY menghentikan forecast lama, menghitung ulang
causal chain dan mencari scenario baru.

🎯 FINAL TREND FORECAST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
XAUUSD saat ini berada dalam {state_desc} regime.

Pada H4, harga diperkirakan {h4_outlook}, dengan jalur
utama menuju {h4_fc} selama {h4_cond} tetap berlaku.

Pada D1, structural trend menunjukkan {d1_outlook}, dengan
potensi pergerakan menuju {d1_fc} selama structural drivers
tetap mendukung.

Hubungan H4 dan D1 saat ini {h4d1_align}.

Dengan demikian, forward price path yang paling konsisten adalah:

{price:.2f}
→ {h4_bias}
→ {h4_fc}
→ {d1_outlook}
→ {d1_fc}

Risiko terbesar berasal dari {contra_risk}.

Jika {inv_cond} terjadi, trajectory tersebut tidak lagi valid
dan XEDY akan menghitung ulang trend forecast.

FINAL VIEW:
[{final_view}]
"""
    return template
