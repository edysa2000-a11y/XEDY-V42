import os
import io
import math
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

WIB = timezone(timedelta(hours=7))

def get_font(size, bold=True):
    font_names = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahomabd.ttf" if bold else "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            continue
    return ImageFont.load_default()

def draw_sphere(draw, cx, cy, r, color):
    for i in range(r, 0, -1):
        ratio = i / r
        cr = int(color[0] * (0.3 + 0.7 * (1.0 - ratio)))
        cg = int(color[1] * (0.3 + 0.7 * (1.0 - ratio)))
        cb = int(color[2] * (0.3 + 0.7 * (1.0 - ratio)))
        draw.ellipse([(cx - i, cy - i), (cx + i, cy + i)], fill=(cr, cg, cb))
    h_r = max(2, r // 3)
    draw.ellipse([(cx - h_r, cy - h_r), (cx, cy)], fill=(255, 255, 255, 220))

def draw_circular_gauge_semi(draw, cx, cy, radius, value, min_val=-100, max_val=100, label=""):
    """Half circular gauge matching top card in attachment (-100 to +100)."""
    bbox = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    draw.arc(bbox, start=140, end=400, fill=(15, 25, 45), width=8)
    
    # Calculate sweep
    pct = (value - min_val) / (max_val - min_val)
    pct = max(0.0, min(1.0, pct))
    sweep = int(pct * 260)
    col = (0, 230, 120) if value > 10 else ((240, 50, 60) if value < -10 else (220, 200, 40))
    if sweep > 0:
        draw.arc(bbox, start=140, end=140 + sweep, fill=col, width=8)
    
    # Inner Score
    f_score = get_font(26, bold=True)
    f_sub = get_font(11, bold=True)
    sign = "+" if value > 0 else ""
    draw.text((cx, cy - 2), f"{sign}{value}", fill=(255, 255, 255), font=f_score, anchor="mm")
    
    tag = "STRONG BUY" if value >= 60 else ("BUY" if value >= 20 else ("STRONG SELL" if value <= -60 else ("SELL" if value <= -20 else "NEUTRAL")))
    tag_col = (0, 255, 136) if "BUY" in tag else ((255, 75, 75) if "SELL" in tag else (220, 200, 40))
    draw.text((cx, cy + 22), tag, fill=tag_col, font=f_sub, anchor="mm")

def draw_flow_meter(draw, cx, cy, radius, pct, col=(0, 230, 120)):
    bbox = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    draw.arc(bbox, start=180, end=360, fill=(15, 25, 45), width=6)
    sweep = int((pct / 100.0) * 180)
    if sweep > 0:
        draw.arc(bbox, start=180, end=180 + sweep, fill=col, width=6)
    f_num = get_font(11, bold=True)
    draw.text((cx, cy - 6), f"{pct}%", fill=(255, 255, 255), font=f_num, anchor="mm")

def generate_money_flow_radar_card(radar_data: dict, now_wib: datetime = None) -> bytes:
    """
    Renders 1600x1000 High-Resolution Institutional XEDY V31 MONEY FLOW RADAR.
    Exact match to jillywosy.com and institutional trading desk attachment.
    """
    if now_wib is None:
        now_wib = datetime.now(WIB)
        
    W, H = 1600, 1000
    img = Image.new("RGB", (W, H), (4, 9, 18))
    draw = ImageDraw.Draw(img)
    
    # Background subtle grid lines
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill=(7, 16, 32), width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=(7, 16, 32), width=1)
        
    # Outer frame
    draw.rounded_rectangle([(8, 8), (W - 8, H - 8)], radius=8, outline=(0, 100, 220), width=2)
    
    # Fonts
    f_title = get_font(26, bold=True)
    f_sub = get_font(12, bold=True)
    f_micro = get_font(10, bold=False)
    f_clock = get_font(22, bold=True)
    f_badge = get_font(11, bold=True)
    f_card_title = get_font(15, bold=True)
    f_card_sub = get_font(11, bold=False)
    f_price = get_font(18, bold=True)
    f_chg = get_font(12, bold=True)
    f_tf = get_font(11, bold=True)
    f_bar_num = get_font(10, bold=True)
    f_hdr_box = get_font(12, bold=True)
    f_cell = get_font(11, bold=False)
    f_cell_bold = get_font(11, bold=True)
    
    # =========================================================================
    # 1. HEADER (Y: 14 to 88)
    # =========================================================================
    # Brand
    draw.text((24, 20), "XEDY V31", fill=(0, 185, 255), font=f_title)
    draw.text((24, 52), "MONEY FLOW RADAR", fill=(255, 255, 255), font=get_font(16, bold=True))
    draw.text((24, 72), "GLOBAL CAPITAL FLOW • FX • COMMODITY • INDEX • BOND • ETF • SECTOR", fill=(110, 160, 215), font=f_micro)
    
    # Clock & Live Badge
    draw.rounded_rectangle([(300, 18), (440, 80)], radius=6, fill=(3, 16, 38), outline=(15, 45, 95), width=1)
    draw.text((310, 24), now_wib.strftime("%a, %d %b %Y"), fill=(130, 175, 225), font=get_font(10, bold=False))
    draw.text((310, 38), now_wib.strftime("%H:%M:%S"), fill=(255, 255, 255), font=f_clock)
    
    # Active Session Calculation
    hour = now_wib.hour
    is_asia = 1 <= hour < 8
    is_europe = 8 <= hour < 15
    is_us = 14 <= hour or hour < 2
    session_label = "London Session" if is_europe else ("New York Session" if is_us else "Asian Session")
    draw.text((310, 64), session_label, fill=(0, 255, 136), font=get_font(11, bold=True))
    
    # Live Pill
    draw.rounded_rectangle([(390, 44), (432, 64)], radius=10, fill=(0, 60, 30), outline=(0, 220, 110), width=1)
    draw.text((411, 54), "LIVE", fill=(0, 255, 136), font=get_font(10, bold=True), anchor="mm")
    
    # Market Sessions Box
    draw.rounded_rectangle([(460, 18), (760, 80)], radius=6, fill=(3, 16, 38), outline=(15, 45, 95), width=1)
    draw.text((472, 24), "MARKET SESSION (LOCAL TIME)", fill=(160, 195, 235), font=get_font(10, bold=True))
    
    # Sessions slots: Asia (01:00-08:00), Europe (08:00-14:00), US (14:40-22:00)
    sessions = [
        ("ASIA", "01:00 - 08:00", "ACTIVE" if is_asia else "COMPLETED", (0, 220, 110) if is_asia else (100, 130, 160)),
        ("EUROPE", "08:00 - 15:00", "ACTIVE" if is_europe else ("UPCOMING" if hour < 8 else "COMPLETED"), (255, 214, 0) if is_europe else (100, 130, 160)),
        ("US", "14:40 - 22:00", "ACTIVE" if is_us else "UPCOMING", (0, 200, 255) if is_us else (100, 130, 160)),
    ]
    for idx, (s_name, s_time, s_st, s_col) in enumerate(sessions):
        bx = 472 + idx * 94
        bg_col = (10, 45, 30) if "ACTIVE" in s_st and s_name=="ASIA" else ((45, 38, 10) if "ACTIVE" in s_st and s_name=="EUROPE" else ((10, 35, 55) if "ACTIVE" in s_st else (4, 18, 38)))
        draw.rounded_rectangle([(bx, 40), (bx + 86, 74)], radius=4, fill=bg_col, outline=s_col, width=1)
        draw.text((bx + 43, 46), s_name, fill=(255, 255, 255), font=get_font(10, bold=True), anchor="mm")
        draw.text((bx + 43, 64), s_st, fill=s_col, font=get_font(9, bold=True), anchor="mm")
        
    # Global Flow Sentiment Bar (Right)
    draw.rounded_rectangle([(780, 18), (1576, 80)], radius=6, fill=(3, 16, 38), outline=(15, 45, 95), width=1)
    draw.text((795, 24), "GLOBAL FLOW SENTIMENT (TRADINGVIEW & JILLYWOSY INDEX)", fill=(160, 195, 235), font=get_font(10, bold=True))
    
    # Scale bar (-100 to +100)
    bar_x1, bar_x2 = 795, 1560
    bar_w = bar_x2 - bar_x1
    by1, by2 = 52, 60
    # Gradient red to green
    for x in range(bar_x1, bar_x2):
        t = (x - bar_x1) / bar_w
        if t < 0.4:
            c = (int(240 - 100 * (t/0.4)), int(50 + 50 * (t/0.4)), 50)
        elif t < 0.6:
            c = (200, 190, 40)
        else:
            c = (int(40 + 180 * ((t-0.6)/0.4)), int(180 + 75 * ((t-0.6)/0.4)), 80)
        draw.line([(x, by1), (x, by2)], fill=c, width=1)
    
    # Labels above bar
    draw.text((bar_x1, 38), "STRONG SELL", fill=(240, 60, 60), font=get_font(9, bold=True))
    draw.text((bar_x1 + int(bar_w*0.25), 38), "SELL", fill=(240, 100, 60), font=get_font(9, bold=True))
    draw.text((bar_x1 + int(bar_w*0.50), 38), "NEUTRAL", fill=(220, 200, 40), font=get_font(9, bold=True), anchor="ma")
    draw.text((bar_x1 + int(bar_w*0.75), 38), "BUY", fill=(0, 220, 110), font=get_font(9, bold=True), anchor="ma")
    draw.text((bar_x2, 38), "STRONG BUY", fill=(0, 255, 136), font=get_font(9, bold=True), anchor="ra")
    
    # Ticks (-100, -60, -30, -10, 0, +10, +30, +60, +100)
    ticks = [(-100, 0.0), (-60, 0.20), (-30, 0.35), (0, 0.50), (+30, 0.65), (+60, 0.80), (+100, 1.0)]
    for val, rel in ticks:
        tx = bar_x1 + int(bar_w * rel)
        draw.line([(tx, by2), (tx, by2 + 4)], fill=(120, 160, 210), width=1)
        draw.text((tx, by2 + 6), f"{val:+d}" if val!=0 else "0", fill=(140, 180, 230), font=get_font(8, bold=False), anchor="ma")
        
    # Marker on Global sentiment
    glob_score = radar_data.get("global_sentiment", -28)
    g_pos = (glob_score - (-100)) / 200.0
    g_pos = max(0.0, min(1.0, g_pos))
    m_x = bar_x1 + int(bar_w * g_pos)
    draw.polygon([(m_x - 5, by1 - 6), (m_x + 5, by1 - 6), (m_x, by1 - 1)], fill=(255, 255, 255))
    draw.ellipse([(m_x - 4, (by1+by2)//2 - 4), (m_x + 4, (by1+by2)//2 + 4)], fill=(0, 255, 255), outline=(255, 255, 255))
    
    # Header Divider Line
    draw.line([(14, 94), (W - 14, 94)], fill=(15, 45, 95), width=2)
    
    # =========================================================================
    # 2. TOP 5 INSTRUMENT RADAR CARDS (Y: 100 to 480)
    # =========================================================================
    instruments = [
        {"key": "XAUUSD", "title": "XAUUSD", "sub": "GOLD SPOT", "icon": "gold"},
        {"key": "USDJPY", "title": "USDJPY", "sub": "USD / JPY", "icon": "jpy"},
        {"key": "EURUSD", "title": "EURUSD", "sub": "EUR / USD", "icon": "eur"},
        {"key": "GBPUSD", "title": "GBPUSD", "sub": "GBP / USD", "icon": "gbp"},
        {"key": "OIL", "title": "OIL", "sub": "WTI CRUDE", "icon": "oil"},
    ]
    
    card_w = 306
    card_gap = 10
    card_top = 100
    card_h = 380
    
    for i, inst in enumerate(instruments):
        cx1 = 16 + i * (card_w + card_gap)
        cx2 = cx1 + card_w
        cy1 = card_top
        cy2 = cy1 + card_h
        
        d = radar_data.get(inst["key"], {})
        score_val = d.get("score", 0)
        price_val = d.get("price", 0.0)
        chg_val = d.get("change_val", 0.0)
        chg_pct = d.get("change_pct", 0.0)
        digits = 2 if inst["key"] in ["XAUUSD", "USDJPY", "OIL"] else 4
        
        # Outer Card Box
        draw.rounded_rectangle([(cx1, cy1), (cx2, cy2)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
        
        # Header inside card
        draw_sphere(draw, cx1 + 22, cy1 + 22, 12, (255, 214, 0) if inst["key"]=="XAUUSD" else ((0, 180, 255) if "USD" in inst["key"] else (180, 180, 190)))
        draw.text((cx1 + 42, cy1 + 12), inst["title"], fill=(255, 255, 255), font=f_card_title)
        draw.text((cx1 + 42, cy1 + 28), inst["sub"], fill=(130, 175, 230), font=f_card_sub)
        
        # Price right-aligned
        chg_sgn = "+" if chg_val >= 0 else ""
        chg_col = (0, 255, 136) if chg_val >= 0 else (255, 75, 75)
        draw.text((cx2 - 12, cy1 + 12), f"{price_val:,.{digits}f}", fill=(255, 255, 255), font=f_price, anchor="ra")
        draw.text((cx2 - 12, cy1 + 30), f"{chg_sgn}{chg_val:.{digits}f} ({chg_sgn}{chg_pct:.2f}%)", fill=chg_col, font=f_chg, anchor="ra")
        
        # Gauge Box: Left = Gauge Score, Right = Multi-Timeframe Trend
        draw.text((cx1 + 45, cy1 + 48), "MONEY FLOW SCORE", fill=(140, 180, 230), font=get_font(9, bold=True), anchor="ma")
        draw.text((cx1 + 230, cy1 + 48), "FLOW TREND", fill=(140, 180, 230), font=get_font(9, bold=True), anchor="ma")
        
        # Half circular gauge
        draw_circular_gauge_semi(draw, cx1 + 65, cy1 + 105, radius=42, value=score_val)
        
        # Multi-timeframe trend (M5, M15, H1, H4, D1)
        tf_list = [
            ("M5", d.get("tf_m5", -12)),
            ("M15", d.get("tf_m15", -24)),
            ("H1", d.get("tf_h1", -45)),
            ("H4", d.get("tf_h4", -55)),
            ("D1", d.get("tf_d1", -62)),
        ]
        for t_idx, (tf_k, tf_v) in enumerate(tf_list):
            ty = cy1 + 66 + t_idx * 16
            draw.text((cx1 + 165, ty), tf_k, fill=(160, 195, 235), font=f_tf)
            v_col = (0, 255, 136) if tf_v > 0 else (255, 75, 75)
            draw.text((cx1 + 205, ty), f"{tf_v:+d}", fill=v_col, font=f_tf, anchor="ra")
            # Mini Arrow
            arr_x = cx1 + 225
            if tf_v > 0:
                draw.line([(arr_x, ty + 10), (arr_x + 8, ty + 2)], fill=v_col, width=2)
                draw.line([(arr_x + 3, ty + 2), (arr_x + 8, ty + 2), (arr_x + 8, ty + 7)], fill=v_col, width=2)
            else:
                draw.line([(arr_x, ty + 2), (arr_x + 8, ty + 10)], fill=v_col, width=2)
                draw.line([(arr_x + 3, ty + 10), (arr_x + 8, ty + 10), (arr_x + 8, ty + 5)], fill=v_col, width=2)
                
        # Card Middle Divider
        draw.line([(cx1 + 10, cy1 + 155), (cx2 - 10, cy1 + 155)], fill=(12, 35, 75), width=1)
        
        # Daily Low - High Horizontal Range Slider
        d_low = d.get("low", price_val * 0.99)
        d_high = d.get("high", price_val * 1.01)
        
        # Tags above bar
        draw.rounded_rectangle([(cx1 + 12, cy1 + 162), (cx1 + 72, cy1 + 178)], radius=3, fill=(10, 45, 30))
        draw.text((cx1 + 42, cy1 + 170), "Daily Low", fill=(0, 255, 136), font=get_font(9, bold=True), anchor="mm")
        
        draw.rounded_rectangle([(cx2 - 72, cy1 + 162), (cx2 - 12, cy1 + 178)], radius=3, fill=(50, 15, 20))
        draw.text((cx2 - 42, cy1 + 170), "Daily High", fill=(255, 80, 80), font=get_font(9, bold=True), anchor="mm")
        
        draw.text((cx1 + 12, cy1 + 185), f"{d_low:,.{digits}f}", fill=(0, 255, 136), font=f_bar_num)
        draw.text((cx2 - 12, cy1 + 185), f"{d_high:,.{digits}f}", fill=(255, 80, 80), font=f_bar_num, anchor="ra")
        
        # Slider Track
        sx1, sx2 = cx1 + 14, cx2 - 14
        sw = sx2 - sx1
        sy1, sy2 = cy1 + 218, cy1 + 226
        
        # Draw gradient track 0% (green) to 100% (red)
        for x in range(sx1, sx2):
            t = (x - sx1) / sw
            if t < 0.25:
                col = (0, 225, 115)
            elif t < 0.50:
                col = (int(0 + 200 * ((t-0.25)/0.25)), int(225 - 25 * ((t-0.25)/0.25)), 40)
            elif t < 0.75:
                col = (210, 200, 0)
            else:
                col = (int(210 + 35 * ((t-0.75)/0.25)), int(200 - 130 * ((t-0.75)/0.25)), int(0 + 50 * ((t-0.75)/0.25)))
            draw.line([(x, sy1), (x, sy2)], fill=col, width=1)
            
        # Range % position
        pct_range = (price_val - d_low) / (d_high - d_low) * 100.0 if d_high > d_low else 50.0
        pct_clamp = max(0.0, min(100.0, pct_range))
        pin_x = sx1 + int(sw * (pct_clamp / 100.0))
        
        # Tooltip badge on slider
        draw.rounded_rectangle([(pin_x - 22, sy1 - 22), (pin_x + 22, sy1 - 4)], radius=4, fill=(255, 214, 0))
        draw.text((pin_x, sy1 - 13), f"{pct_range:.1f}%", fill=(0, 0, 0), font=get_font(9, bold=True), anchor="mm")
        draw.line([(pin_x, sy1 - 4), (pin_x, sy2)], fill=(255, 214, 0), width=2)
        draw.ellipse([(pin_x - 5, (sy1+sy2)//2 - 5), (pin_x + 5, (sy1+sy2)//2 + 5)], fill=(0, 180, 255), outline=(255, 255, 255))
        
        # Ticks below bar: 0%, 25%, 50%, 75%, 100%
        draw.text((sx1, sy2 + 4), "0%", fill=(120, 160, 215), font=get_font(8, bold=False))
        draw.text((sx1 + int(sw*0.25), sy2 + 4), "25%", fill=(120, 160, 215), font=get_font(8, bold=False), anchor="ma")
        draw.text((sx1 + int(sw*0.50), sy2 + 4), "50%", fill=(120, 160, 215), font=get_font(8, bold=False), anchor="ma")
        draw.text((sx1 + int(sw*0.75), sy2 + 4), "75%", fill=(120, 160, 215), font=get_font(8, bold=False), anchor="ma")
        draw.text((sx2, sy2 + 4), "100%", fill=(120, 160, 215), font=get_font(8, bold=False), anchor="ra")
        
        draw.text(((sx1+sx2)//2, sy2 + 20), f"Live Price: {price_val:,.{digits}f} ({pct_range:.1f}% dari Low)", fill=(160, 205, 255), font=get_font(10, bold=False), anchor="mm")
        
        # Card Bottom Divider
        draw.line([(cx1 + 10, cy1 + 258), (cx2 - 10, cy1 + 258)], fill=(12, 35, 75), width=1)
        
        # Inflow / Outflow / Net / Flow Intensity
        in_b = d.get("inflow", 320)
        out_b = d.get("outflow", 280)
        net_b = in_b - out_b
        net_sgn = "+" if net_b >= 0 else ""
        net_col = (0, 255, 136) if net_b >= 0 else (255, 75, 75)
        
        draw.text((cx1 + 35, cy1 + 266), "INFLOW", fill=(130, 175, 230), font=get_font(9, bold=True), anchor="mm")
        draw.text((cx1 + 105, cy1 + 266), "OUTFLOW", fill=(130, 175, 230), font=get_font(9, bold=True), anchor="mm")
        draw.text((cx1 + 175, cy1 + 266), "NET", fill=(130, 175, 230), font=get_font(9, bold=True), anchor="mm")
        draw.text((cx1 + 255, cy1 + 266), "FLOW INTENSITY", fill=(130, 175, 230), font=get_font(9, bold=True), anchor="mm")
        
        draw.text((cx1 + 35, cy1 + 295), f"{in_b}B", fill=(0, 255, 136), font=get_font(15, bold=True), anchor="mm")
        draw.text((cx1 + 105, cy1 + 295), f"{out_b}B", fill=(255, 75, 75), font=get_font(15, bold=True), anchor="mm")
        draw.text((cx1 + 175, cy1 + 295), f"{net_sgn}{net_b}B", fill=net_col, font=get_font(15, bold=True), anchor="mm")
        
        # Half meter for flow intensity
        intensity = d.get("intensity", 75)
        draw_flow_meter(draw, cx1 + 255, cy1 + 300, radius=24, pct=intensity, col=(0, 230, 120) if intensity > 60 else (220, 200, 40))
        
        # Bottom Badge (Status Verdict)
        verdict = d.get("verdict", "INSTITUTIONAL ACCUMULATION" if net_b > 0 else "INSTITUTIONAL DISTRIBUTION")
        v_bg = (4, 45, 25) if net_b > 0 else (45, 15, 20)
        v_col = (0, 255, 136) if net_b > 0 else (255, 80, 80)
        draw.rounded_rectangle([(cx1 + 12, cy1 + 338), (cx2 - 12, cy1 + 368)], radius=4, fill=v_bg, outline=v_col, width=1)
        draw.text(((cx1+cx2)//2, cy1 + 353), verdict, fill=v_col, font=get_font(11, bold=True), anchor="mm")

    # =========================================================================
    # 3. BOTTOM 8 INSTITUTIONAL MATRIX PANELS (Y: 490 to 980)
    # =========================================================================
    # Grid 1: Major FX Money Flow (X: 16 to 340)
    draw.rounded_rectangle([(16, 490), (340, 730)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((26, 498), "MAJOR FX MONEY FLOW (JILLYWOSY INDEX)", fill=(255, 214, 0), font=get_font(11, bold=True))
    draw.text((26, 514), "CURRENCY    SCORE   FLOW BAR    1D   1W   TREND", fill=(120, 160, 210), font=get_font(9, bold=True))
    draw.line([(22, 526), (334, 526)], fill=(12, 35, 75), width=1)
    
    fx_list = radar_data.get("fx_major", [
        ("USD", +78, "INFLOW", "+0.45%", "+1.2%", "UP"),
        ("EUR", -21, "OUTFLOW", "-0.22%", "-0.8%", "DOWN"),
        ("GBP", -34, "OUTFLOW", "-0.31%", "-0.4%", "DOWN"),
        ("JPY", +43, "INFLOW", "+0.18%", "+0.9%", "UP"),
        ("CHF", +19, "NEUTRAL", "+0.05%", "-0.2%", "SIDE"),
        ("AUD", -17, "OUTFLOW", "-0.15%", "-0.6%", "DOWN"),
        ("CAD", +9, "NEUTRAL", "+0.08%", "+0.3%", "SIDE"),
        ("NZD", -14, "OUTFLOW", "-0.28%", "-0.7%", "DOWN"),
    ])
    for r_i, (f_curr, f_sc, f_tag, f_1d, f_1w, f_tr) in enumerate(fx_list):
        ry = 532 + r_i * 24
        draw.text((26, ry), f_curr, fill=(255, 255, 255), font=f_cell_bold)
        sc_col = (0, 255, 136) if f_sc > 0 else (255, 75, 75)
        draw.text((75, ry), f"{f_sc:+d}", fill=sc_col, font=f_cell_bold)
        
        # Flow bar
        draw.rounded_rectangle([(105, ry + 2), (175, ry + 12)], radius=2, fill=(10, 20, 40))
        b_w = int(abs(f_sc) / 100.0 * 35)
        if f_sc > 0:
            draw.rounded_rectangle([(140, ry + 2), (140 + b_w, ry + 12)], radius=2, fill=(0, 230, 120))
        else:
            draw.rounded_rectangle([(140 - b_w, ry + 2), (140, ry + 12)], radius=2, fill=(240, 50, 60))
            
        draw.text((188, ry), f_1d, fill=sc_col, font=f_cell)
        draw.text((238, ry), f_1w, fill=(180, 210, 245), font=f_cell)
        
        # Trend Icon
        t_col = (0, 255, 136) if f_tr == "UP" else ((255, 75, 75) if f_tr == "DOWN" else (220, 200, 40))
        t_sym = "▲" if f_tr == "UP" else ("▼" if f_tr == "DOWN" else "▶")
        draw.text((295, ry), t_sym, fill=t_col, font=f_cell_bold)
        
    # Grid 2: Global Capital Flow Map (X: 350 to 950, Y: 490 to 730)
    draw.rounded_rectangle([(350, 490), (950, 730)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((362, 498), "GLOBAL CAPITAL FLOW MAP (REGIONAL MACRO DYNAMICS)", fill=(0, 229, 255), font=get_font(11, bold=True))
    draw.line([(356, 516), (944, 516)], fill=(12, 35, 75), width=1)
    
    # World map schematic boxes
    regions = [
        ("N. AMERICA", "+42", "Capital Inflow", "USD ↑ Equities ↑", 380, 530, (0, 230, 120)),
        ("EUROPE", "-28", "Capital Outflow", "EUR ↓ Bonds ↑", 610, 530, (240, 50, 60)),
        ("ASIA PACIFIC", "+18", "Moderate Inflow", "JPY ↑ Commodities ↑", 790, 530, (0, 210, 140)),
        ("LATAM", "-12", "Risk Off", "Commodity Outflow", 420, 630, (240, 70, 70)),
        ("MIDDLE EAST", "+24", "Petrodollar Inflow", "Oil ↑ USD Reserves", 650, 630, (0, 230, 120)),
    ]
    for r_name, r_sc, r_fl, r_desc, rx, ry, r_col in regions:
        draw.rounded_rectangle([(rx, ry), (rx + 140, ry + 75)], radius=5, fill=(4, 20, 42), outline=r_col, width=1)
        draw.text((rx + 70, ry + 12), r_name, fill=(255, 255, 255), font=get_font(10, bold=True), anchor="mm")
        draw.text((rx + 70, ry + 32), r_sc, fill=r_col, font=get_font(18, bold=True), anchor="mm")
        draw.text((rx + 70, ry + 48), r_fl, fill=r_col, font=get_font(9, bold=True), anchor="mm")
        draw.text((rx + 70, ry + 62), r_desc, fill=(140, 180, 220), font=get_font(8, bold=False), anchor="mm")
        
    # Flow Vector Arrows between regions
    # N. America -> Europe
    draw.line([(520, 565), (610, 565)], fill=(0, 255, 200), width=2)
    # Europe -> Middle East
    draw.line([(680, 605), (710, 630)], fill=(240, 80, 80), width=2)
    # Asia -> Middle East
    draw.line([(790, 605), (760, 630)], fill=(0, 255, 136), width=2)
    
    # Legend below map
    draw.text((400, 715), "■ Capital Inflow (Hijau)", fill=(0, 255, 136), font=get_font(9, bold=True))
    draw.text((560, 715), "■ Capital Outflow (Merah)", fill=(255, 80, 80), font=get_font(9, bold=True))
    draw.text((720, 715), "● High Flow Intensity", fill=(0, 229, 255), font=get_font(9, bold=True))
    
    # Grid 3: Commodity Money Flow (X: 960 to 1270, Y: 490 to 730)
    draw.rounded_rectangle([(960, 490), (1270, 730)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((970, 498), "COMMODITY MONEY FLOW", fill=(255, 214, 0), font=get_font(11, bold=True))
    draw.text((970, 514), "ASSET      SCORE  FLOW   1D     1W   TREND", fill=(120, 160, 210), font=get_font(9, bold=True))
    draw.line([(966, 526), (1264, 526)], fill=(12, 35, 75), width=1)
    
    comms = radar_data.get("commodities", [
        ("GOLD", -62, "OUT", "-0.60%", "-1.1%", "DOWN"),
        ("SILVER", +32, "IN", "+0.45%", "+2.3%", "UP"),
        ("WTI OIL", +56, "IN", "+0.86%", "+1.4%", "UP"),
        ("BRENT", +48, "IN", "+0.72%", "+1.1%", "UP"),
        ("NAT GAS", -18, "OUT", "-0.85%", "-2.8%", "DOWN"),
        ("COPPER", +26, "IN", "+0.32%", "+0.8%", "UP"),
        ("PLATINUM", +12, "NEUT", "+0.15%", "+0.4%", "SIDE"),
        ("SOYBEAN", -11, "OUT", "-0.22%", "-0.9%", "DOWN"),
    ])
    for c_i, (c_name, c_sc, c_fl, c_1d, c_1w, c_tr) in enumerate(comms):
        cy = 532 + c_i * 24
        draw.text((970, cy), c_name, fill=(255, 255, 255), font=f_cell_bold)
        sc_col = (0, 255, 136) if c_sc > 0 else (255, 75, 75)
        draw.text((1035, cy), f"{c_sc:+d}", fill=sc_col, font=f_cell_bold)
        
        # Mini bar
        draw.rounded_rectangle([(1065, cy + 2), (1110, cy + 12)], radius=2, fill=(10, 20, 40))
        b_w = int(abs(c_sc) / 100.0 * 22)
        if c_sc > 0:
            draw.rounded_rectangle([(1087, cy + 2), (1087 + b_w, cy + 12)], radius=2, fill=(0, 230, 120))
        else:
            draw.rounded_rectangle([(1087 - b_w, cy + 2), (1087, cy + 12)], radius=2, fill=(240, 50, 60))
            
        draw.text((1125, cy), c_1d, fill=sc_col, font=f_cell)
        draw.text((1180, cy), c_1w, fill=(180, 210, 245), font=f_cell)
        t_col = (0, 255, 136) if c_tr == "UP" else ((255, 75, 75) if c_tr == "DOWN" else (220, 200, 40))
        draw.text((1235, cy), "▲" if c_tr == "UP" else ("▼" if c_tr == "DOWN" else "▶"), fill=t_col, font=f_cell_bold)
        
    # Grid 4: Index Money Flow (X: 1280 to 1584, Y: 490 to 730)
    draw.rounded_rectangle([(1280, 490), (1584, 730)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((1290, 498), "GLOBAL INDEX MONEY FLOW", fill=(255, 214, 0), font=get_font(11, bold=True))
    draw.text((1290, 514), "INDEX      SCORE  FLOW   1D     1W   TREND", fill=(120, 160, 210), font=get_font(9, bold=True))
    draw.line([(1286, 526), (1578, 526)], fill=(12, 35, 75), width=1)
    
    indices = radar_data.get("indices", [
        ("DXY", +78, "IN", "+0.21%", "+0.6%", "UP"),
        ("US500", -32, "OUT", "-0.18%", "+0.4%", "DOWN"),
        ("US100", -41, "OUT", "-0.24%", "+0.2%", "DOWN"),
        ("US30", -28, "OUT", "-0.12%", "+0.5%", "DOWN"),
        ("NIKKEI", +36, "IN", "+0.45%", "+1.2%", "UP"),
        ("DAX", -24, "OUT", "-0.32%", "-0.6%", "DOWN"),
        ("FTSE", -19, "OUT", "-0.15%", "-0.4%", "DOWN"),
        ("VIX", +22, "IN", "+3.40%", "+5.2%", "UP"),
    ])
    for idx_i, (id_name, id_sc, id_fl, id_1d, id_1w, id_tr) in enumerate(indices):
        iy = 532 + idx_i * 24
        draw.text((1290, iy), id_name, fill=(255, 255, 255), font=f_cell_bold)
        sc_col = (0, 255, 136) if id_sc > 0 else (255, 75, 75)
        draw.text((1355, iy), f"{id_sc:+d}", fill=sc_col, font=f_cell_bold)
        
        # Mini bar
        draw.rounded_rectangle([(1385, iy + 2), (1430, iy + 12)], radius=2, fill=(10, 20, 40))
        b_w = int(abs(id_sc) / 100.0 * 22)
        if id_sc > 0:
            draw.rounded_rectangle([(1407, iy + 2), (1407 + b_w, iy + 12)], radius=2, fill=(0, 230, 120))
        else:
            draw.rounded_rectangle([(1407 - b_w, iy + 2), (1407, iy + 12)], radius=2, fill=(240, 50, 60))
            
        draw.text((1445, iy), id_1d, fill=sc_col, font=f_cell)
        draw.text((1500, iy), id_1w, fill=(180, 210, 245), font=f_cell)
        t_col = (0, 255, 136) if id_tr == "UP" else ((255, 75, 75) if id_tr == "DOWN" else (220, 200, 40))
        draw.text((1555, iy), "▲" if id_tr == "UP" else ("▼" if id_tr == "DOWN" else "▶"), fill=t_col, font=f_cell_bold)
        
    # Lower 4 Grid Panels (Y: 740 to 980)
    # Grid 5: Bond & Yield Flow (X: 16 to 260)
    draw.rounded_rectangle([(16, 740), (260, 980)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((26, 748), "BOND & YIELD FLOW", fill=(0, 229, 255), font=get_font(11, bold=True))
    draw.text((26, 764), "TENOR   YIELD   Δ(bps)  FLOW", fill=(120, 160, 210), font=get_font(9, bold=True))
    draw.line([(22, 776), (254, 776)], fill=(12, 35, 75), width=1)
    
    yields = [
        ("US 2Y", "3.72%", "+3.1", "UP"),
        ("US 5Y", "3.81%", "+3.8", "UP"),
        ("US 10Y", "4.05%", "+2.5", "UP"),
        ("US 30Y", "4.40%", "+1.9", "UP"),
        ("GER 10Y", "2.65%", "-1.2", "DOWN"),
        ("JPY 10Y", "0.92%", "+0.5", "UP"),
        ("UK 10Y", "4.21%", "+0.8", "UP"),
    ]
    for y_i, (y_t, y_v, y_d, y_tr) in enumerate(yields):
        yy = 782 + y_i * 26
        draw.text((26, yy), y_t, fill=(255, 255, 255), font=f_cell_bold)
        draw.text((90, yy), y_v, fill=(200, 230, 255), font=f_cell)
        d_col = (0, 255, 136) if "+" in y_d else (255, 75, 75)
        draw.text((150, yy), y_d, fill=d_col, font=f_cell_bold)
        draw.text((215, yy), "▲" if y_tr == "UP" else "▼", fill=d_col, font=f_cell_bold)
        
    # Grid 6: Sector Money Flow (S&P 500) (X: 270 to 570)
    draw.rounded_rectangle([(270, 740), (570, 980)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((280, 748), "SECTOR MONEY FLOW (S&P 500)", fill=(0, 229, 255), font=get_font(11, bold=True))
    draw.text((280, 764), "SECTOR          SCORE   FLOW BAR     TREND", fill=(120, 160, 210), font=get_font(9, bold=True))
    draw.line([(276, 776), (564, 776)], fill=(12, 35, 75), width=1)
    
    sectors = [
        ("Technology", -34, "DOWN"),
        ("Financials", +18, "UP"),
        ("Energy", +42, "UP"),
        ("Consumer Disc.", -26, "DOWN"),
        ("Consumer Staples", +12, "UP"),
        ("Healthcare", -18, "DOWN"),
        ("Utilities", +14, "UP"),
    ]
    for s_i, (sec_n, sec_sc, sec_tr) in enumerate(sectors):
        sy = 782 + s_i * 26
        draw.text((280, sy), sec_n, fill=(255, 255, 255), font=f_cell_bold)
        sc_col = (0, 255, 136) if sec_sc > 0 else (255, 75, 75)
        draw.text((395, sy), f"{sec_sc:+d}", fill=sc_col, font=f_cell_bold)
        
        # Bar
        draw.rounded_rectangle([(430, sy + 2), (490, sy + 12)], radius=2, fill=(10, 20, 40))
        b_w = int(abs(sec_sc) / 100.0 * 30)
        if sec_sc > 0:
            draw.rounded_rectangle([(460, sy + 2), (460 + b_w, sy + 12)], radius=2, fill=(0, 230, 120))
        else:
            draw.rounded_rectangle([(460 - b_w, sy + 2), (460, sy + 12)], radius=2, fill=(240, 50, 60))
        draw.text((525, sy), "▲" if sec_tr == "UP" else "▼", fill=sc_col, font=f_cell_bold)
        
    # Grid 7: Top Flow Movers (X: 580 to 950)
    draw.rounded_rectangle([(580, 740), (950, 980)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((590, 748), "TOP FLOW MOVERS (REAL TIME)", fill=(0, 229, 255), font=get_font(11, bold=True))
    
    # Left = Top Inflow, Right = Top Outflow
    draw.rounded_rectangle([(590, 768), (755, 786)], radius=3, fill=(10, 45, 25))
    draw.text((672, 777), "TOP INFLOW", fill=(0, 255, 136), font=get_font(9, bold=True), anchor="mm")
    
    draw.rounded_rectangle([(765, 768), (940, 786)], radius=3, fill=(50, 15, 20))
    draw.text((852, 777), "TOP OUTFLOW", fill=(255, 80, 80), font=get_font(9, bold=True), anchor="mm")
    
    inflows = [("USD", "+78"), ("OIL", "+56"), ("JPY", "+45"), ("ENERGY", "+42"), ("SILVER", "+32"), ("COPPER", "+26")]
    outflows = [("GOLD", "-62"), ("EUR", "-21"), ("GBP", "-34"), ("TECH", "-34"), ("US100", "-41"), ("NZD", "-14")]
    
    for m_i in range(6):
        my = 794 + m_i * 28
        in_a, in_s = inflows[m_i]
        out_a, out_s = outflows[m_i]
        
        # Inflow row
        draw.text((595, my), in_a, fill=(255, 255, 255), font=f_cell_bold)
        draw.text((740, my), in_s, fill=(0, 255, 136), font=f_cell_bold, anchor="ra")
        
        # Outflow row
        draw.text((770, my), out_a, fill=(255, 255, 255), font=f_cell_bold)
        draw.text((930, my), out_s, fill=(255, 75, 75), font=f_cell_bold, anchor="ra")
        
    # Grid 8: Multi-Asset Flow Alignment Heatmap (X: 960 to 1584, Y: 740 to 980)
    draw.rounded_rectangle([(960, 740), (1584, 980)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((970, 748), "FLOW ALIGNMENT HEATMAP (MULTI-ASSET & TIMEFRAME)", fill=(0, 229, 255), font=get_font(11, bold=True))
    draw.line([(966, 766), (1578, 766)], fill=(12, 35, 75), width=1)
    
    # Table Header
    cols_hm = ["ASSET", "M5", "M15", "H1", "H4", "D1", "1W", "AGGREGATE STATUS"]
    col_xs = [975, 1070, 1130, 1190, 1250, 1310, 1370, 1450]
    for c_idx, c_title in enumerate(cols_hm):
        draw.text((col_xs[c_idx], 774), c_title, fill=(120, 160, 210), font=get_font(9, bold=True))
        
    hm_rows = [
        ("XAUUSD", [-1, -2, -2, -2, -2, -1], "STRONG DISTRIBUTION"),
        ("USDJPY", [+1, +2, +2, +2, +2, +1], "STRONG ACCUMULATION"),
        ("EURUSD", [-1, -1, -2, -2, -2, -1], "INSTITUTIONAL OUTFLOW"),
        ("GBPUSD", [-1, -1, -1, -2, -1, 0], "MODERATE OUTFLOW"),
        ("OIL", [+2, +2, +2, +1, +1, +1], "STRONG ACCUMULATION"),
        ("DXY", [+1, +1, +2, +2, +2, +2], "DOLLAR DOMINANCE"),
        ("SP500", [-1, -1, -2, -1, 0, +1], "ROTATION / REBALANCING"),
    ]
    
    for h_i, (h_ast, h_vals, h_verdict) in enumerate(hm_rows):
        hy = 794 + h_i * 24
        draw.text((col_xs[0], hy + 2), h_ast, fill=(255, 255, 255), font=f_cell_bold)
        
        # Heatmap boxes
        for v_i, val in enumerate(h_vals):
            bx = col_xs[1 + v_i]
            # Color encoding: +2 Dark Green, +1 Light Green, 0 Yellow, -1 Orange, -2 Red
            if val == 2: b_c = (0, 180, 80)
            elif val == 1: b_c = (0, 230, 120)
            elif val == 0: b_c = (210, 190, 40)
            elif val == -1: b_c = (230, 90, 60)
            else: b_c = (190, 30, 40)
            
            draw.rounded_rectangle([(bx, hy), (bx + 42, hy + 18)], radius=3, fill=b_c)
            v_str = "BUY" if val > 0 else ("SELL" if val < 0 else "NEUT")
            draw.text((bx + 21, hy + 9), v_str, fill=(0, 0, 0) if val==0 else (255, 255, 255), font=get_font(8, bold=True), anchor="mm")
            
        # Aggregate status
        stat_col = (0, 255, 136) if "ACCUMULATION" in h_verdict or "DOMINANCE" in h_verdict else ((255, 75, 75) if "DISTRIBUTION" in h_verdict or "OUTFLOW" in h_verdict else (220, 200, 40))
        draw.text((col_xs[7], hy + 2), h_verdict, fill=stat_col, font=get_font(10, bold=True))
        
    # Upgrade to 1920x1080 Full HD (16:9) with High-Fidelity Lanczos Resampling
    if img.size != (1920, 1080):
        img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
        
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
