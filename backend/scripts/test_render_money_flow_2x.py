import os
import sys
import io
import math
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.telegram.money_flow_generator import get_font, draw_sphere

WIB = timezone(timedelta(hours=7))

def draw_circular_gauge_semi_2x(draw, cx, cy, radius, value, min_val=-100, max_val=100):
    bbox = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    draw.arc(bbox, start=140, end=400, fill=(15, 25, 45), width=10)
    
    pct = (value - min_val) / (max_val - min_val)
    pct = max(0.0, min(1.0, pct))
    sweep = int(pct * 260)
    col = (0, 230, 120) if value > 10 else ((240, 50, 60) if value < -10 else (220, 200, 40))
    if sweep > 0:
        draw.arc(bbox, start=140, end=140 + sweep, fill=col, width=10)
    
    f_score = get_font(34, bold=True)
    f_sub = get_font(15, bold=True)
    sign = "+" if value > 0 else ""
    draw.text((cx, cy - 4), f"{sign}{value}", fill=(255, 255, 255), font=f_score, anchor="mm")
    
    tag = "STRONG BUY" if value >= 60 else ("BUY" if value >= 20 else ("STRONG SELL" if value <= -60 else ("SELL" if value <= -20 else "NEUTRAL")))
    tag_col = (0, 255, 136) if "BUY" in tag else ((255, 75, 75) if "SELL" in tag else (220, 200, 40))
    draw.text((cx, cy + 26), tag, fill=tag_col, font=f_sub, anchor="mm")

def draw_flow_meter_2x(draw, cx, cy, radius, pct, col=(0, 230, 120)):
    bbox = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    draw.arc(bbox, start=180, end=360, fill=(15, 25, 45), width=8)
    sweep = int((pct / 100.0) * 180)
    if sweep > 0:
        draw.arc(bbox, start=180, end=180 + sweep, fill=col, width=8)
    f_num = get_font(15, bold=True)
    draw.text((cx, cy - 8), f"{pct}%", fill=(255, 255, 255), font=f_num, anchor="mm")

def render_money_flow_radar_2x(radar_data: dict, now_wib: datetime = None, output_path: str = None) -> bytes:
    if now_wib is None:
        now_wib = datetime.now(WIB)
        
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (4, 9, 18))
    draw = ImageDraw.Draw(img)
    
    # Background subtle grid lines
    for x in range(0, W, 48):
        draw.line([(x, 0), (x, H)], fill=(7, 16, 32), width=1)
    for y in range(0, H, 48):
        draw.line([(0, y), (W, y)], fill=(7, 16, 32), width=1)
        
    # Outer frame
    draw.rounded_rectangle([(8, 8), (W - 8, H - 8)], radius=10, outline=(0, 110, 230), width=2)
    
    # Fonts (Scaled ~2X)
    f_title = get_font(38, bold=True)
    f_sub = get_font(24, bold=True)
    f_micro = get_font(14, bold=False)
    f_clock = get_font(30, bold=True)
    f_card_title = get_font(24, bold=True)
    f_card_sub = get_font(14, bold=False)
    f_price = get_font(26, bold=True)
    f_chg = get_font(15, bold=True)
    f_tf = get_font(14, bold=True)
    f_bar_num = get_font(15, bold=True)
    f_hdr_box = get_font(15, bold=True)
    f_sub_hdr = get_font(12, bold=True)
    f_cell = get_font(14, bold=False)
    f_cell_bold = get_font(14, bold=True)
    
    # =========================================================================
    # 1. HEADER (Y: 14 to 92)
    # =========================================================================
    # Brand
    draw.text((24, 16), "XEDY V31", fill=(0, 185, 255), font=f_title)
    draw.text((24, 54), "MONEY FLOW RADAR", fill=(255, 255, 255), font=f_sub)
    draw.text((24, 80), "GLOBAL CAPITAL FLOW • FX • COMMODITY • INDEX • BOND • ETF • SECTOR", fill=(110, 160, 215), font=f_micro)
    
    # Clock & Live Badge (Wider box, LIVE pill at top-right)
    draw.rounded_rectangle([(275, 16), (510, 88)], radius=6, fill=(3, 16, 38), outline=(15, 45, 95), width=1)
    draw.text((288, 20), now_wib.strftime("%a, %d %b %Y"), fill=(130, 175, 225), font=get_font(13, bold=False))
    draw.rounded_rectangle([(445, 18), (498, 40)], radius=11, fill=(0, 60, 30), outline=(0, 220, 110), width=1)
    draw.text((471, 29), "LIVE", fill=(0, 255, 136), font=get_font(11, bold=True), anchor="mm")
    
    draw.text((288, 38), now_wib.strftime("%H:%M:%S"), fill=(255, 255, 255), font=f_clock)
    
    # Active Session Calculation
    hour = now_wib.hour
    is_asia = 1 <= hour < 8
    is_europe = 8 <= hour < 15
    is_us = 14 <= hour or hour < 2
    session_label = "London Session" if is_europe else ("New York Session" if is_us else "Asian Session")
    draw.text((288, 68), session_label, fill=(0, 255, 136), font=get_font(13, bold=True))
    
    # Market Sessions Box
    draw.rounded_rectangle([(522, 16), (900, 88)], radius=6, fill=(3, 16, 38), outline=(15, 45, 95), width=1)
    draw.text((534, 22), "MARKET SESSION (LOCAL TIME)", fill=(160, 195, 235), font=get_font(13, bold=True))
    
    sessions = [
        ("ASIA", "01:00 - 08:00", "ACTIVE" if is_asia else "COMPLETED", (0, 220, 110) if is_asia else (100, 130, 160)),
        ("EUROPE", "08:00 - 15:00", "ACTIVE" if is_europe else ("UPCOMING" if hour < 8 else "COMPLETED"), (255, 214, 0) if is_europe else (100, 130, 160)),
        ("US", "14:40 - 22:00", "ACTIVE" if is_us else "UPCOMING", (0, 200, 255) if is_us else (100, 130, 160)),
    ]
    for idx, (s_name, s_time, s_st, s_col) in enumerate(sessions):
        bx = 534 + idx * 120
        bg_col = (10, 45, 30) if "ACTIVE" in s_st and s_name=="ASIA" else ((45, 38, 10) if "ACTIVE" in s_st and s_name=="EUROPE" else ((10, 35, 55) if "ACTIVE" in s_st else (4, 18, 38)))
        draw.rounded_rectangle([(bx, 42), (bx + 110, 80)], radius=4, fill=bg_col, outline=s_col, width=1)
        draw.text((bx + 55, 50), s_name, fill=(255, 255, 255), font=get_font(13, bold=True), anchor="mm")
        draw.text((bx + 55, 69), s_st, fill=s_col, font=get_font(12, bold=True), anchor="mm")
        
    # Global Flow Sentiment Bar (Right)
    draw.rounded_rectangle([(912, 16), (1902, 88)], radius=6, fill=(3, 16, 38), outline=(15, 45, 95), width=1)
    draw.text((928, 22), "GLOBAL FLOW SENTIMENT (TRADINGVIEW & JILLYWOSY INDEX)", fill=(160, 195, 235), font=get_font(13, bold=True))
    
    # Scale bar (-100 to +100)
    bar_x1, bar_x2 = 928, 1886
    bar_w = bar_x2 - bar_x1
    by1, by2 = 56, 66
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
    f_bar_lbl = get_font(13, bold=True)
    draw.text((bar_x1, 38), "STRONG SELL", fill=(240, 60, 60), font=f_bar_lbl)
    draw.text((bar_x1 + int(bar_w*0.25), 38), "SELL", fill=(240, 100, 60), font=f_bar_lbl)
    draw.text((bar_x1 + int(bar_w*0.50), 38), "NEUTRAL", fill=(220, 200, 40), font=f_bar_lbl, anchor="ma")
    draw.text((bar_x1 + int(bar_w*0.75), 38), "BUY", fill=(0, 220, 110), font=f_bar_lbl, anchor="ma")
    draw.text((bar_x2, 38), "STRONG BUY", fill=(0, 255, 136), font=f_bar_lbl, anchor="ra")
    
    # Ticks (-100, -60, -30, 0, +30, +60, +100)
    ticks = [(-100, 0.0), (-60, 0.20), (-30, 0.35), (0, 0.50), (+30, 0.65), (+60, 0.80), (+100, 1.0)]
    for val, rel in ticks:
        tx = bar_x1 + int(bar_w * rel)
        draw.line([(tx, by2), (tx, by2 + 5)], fill=(120, 160, 210), width=1)
        draw.text((tx, by2 + 6), f"{val:+d}" if val!=0 else "0", fill=(140, 180, 230), font=get_font(11, bold=False), anchor="ma")
        
    glob_score = radar_data.get("global_sentiment", -28)
    g_pos = (glob_score - (-100)) / 200.0
    g_pos = max(0.0, min(1.0, g_pos))
    m_x = bar_x1 + int(bar_w * g_pos)
    draw.polygon([(m_x - 6, by1 - 8), (m_x + 6, by1 - 8), (m_x, by1 - 1)], fill=(255, 255, 255))
    draw.ellipse([(m_x - 5, (by1+by2)//2 - 5), (m_x + 5, (by1+by2)//2 + 5)], fill=(0, 255, 255), outline=(255, 255, 255))
    
    # Header Divider Line
    draw.line([(14, 98), (W - 14, 98)], fill=(15, 45, 95), width=2)
    
    # =========================================================================
    # 2. TOP 5 INSTRUMENT RADAR CARDS (Y: 106 to 506) - Height 400px
    # =========================================================================
    instruments = [
        {"key": "XAUUSD", "title": "XAUUSD", "sub": "GOLD SPOT", "icon": "gold"},
        {"key": "USDJPY", "title": "USDJPY", "sub": "USD / JPY", "icon": "jpy"},
        {"key": "EURUSD", "title": "EURUSD", "sub": "EUR / USD", "icon": "eur"},
        {"key": "GBPUSD", "title": "GBPUSD", "sub": "GBP / USD", "icon": "gbp"},
        {"key": "OIL", "title": "OIL", "sub": "WTI CRUDE", "icon": "oil"},
    ]
    
    card_w = 368
    card_gap = 12
    card_top = 106
    card_h = 400
    
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
        draw.rounded_rectangle([(cx1, cy1), (cx2, cy2)], radius=8, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
        
        # Header inside card
        draw_sphere(draw, cx1 + 26, cy1 + 28, 14, (255, 214, 0) if inst["key"]=="XAUUSD" else ((0, 180, 255) if "USD" in inst["key"] else (180, 180, 190)))
        draw.text((cx1 + 48, cy1 + 14), inst["title"], fill=(255, 255, 255), font=f_card_title)
        draw.text((cx1 + 48, cy1 + 40), inst["sub"], fill=(130, 175, 230), font=f_card_sub)
        
        # Price right-aligned
        chg_sgn = "+" if chg_val >= 0 else ""
        chg_col = (0, 255, 136) if chg_val >= 0 else (255, 75, 75)
        draw.text((cx2 - 14, cy1 + 14), f"{price_val:,.{digits}f}", fill=(255, 255, 255), font=f_price, anchor="ra")
        draw.text((cx2 - 14, cy1 + 40), f"{chg_sgn}{chg_val:.{digits}f} ({chg_sgn}{chg_pct:.2f}%)", fill=chg_col, font=f_chg, anchor="ra")
        
        # Gauge Box: Left = Gauge Score, Right = Multi-Timeframe Trend
        draw.text((cx1 + 80, cy1 + 60), "MONEY FLOW SCORE", fill=(140, 180, 230), font=get_font(12, bold=True), anchor="ma")
        draw.text((cx1 + 285, cy1 + 60), "FLOW TREND", fill=(140, 180, 230), font=get_font(12, bold=True), anchor="ma")
        
        # Half circular gauge
        draw_circular_gauge_semi_2x(draw, cx1 + 80, cy1 + 120, radius=46, value=score_val)
        
        # Multi-timeframe trend (M5, M15, H1, H4, D1)
        tf_list = [
            ("M5", d.get("tf_m5", -12)),
            ("M15", d.get("tf_m15", -24)),
            ("H1", d.get("tf_h1", -45)),
            ("H4", d.get("tf_h4", -55)),
            ("D1", d.get("tf_d1", -62)),
        ]
        for t_idx, (tf_k, tf_v) in enumerate(tf_list):
            ty = cy1 + 80 + t_idx * 18
            draw.text((cx1 + 215, ty), tf_k, fill=(160, 195, 235), font=f_tf)
            v_col = (0, 255, 136) if tf_v > 0 else (255, 75, 75)
            draw.text((cx1 + 275, ty), f"{tf_v:+d}", fill=v_col, font=f_tf, anchor="ra")
            # Mini Arrow
            arr_x = cx1 + 300
            if tf_v > 0:
                draw.line([(arr_x, ty + 12), (arr_x + 9, ty + 3)], fill=v_col, width=2)
                draw.line([(arr_x + 4, ty + 3), (arr_x + 9, ty + 3), (arr_x + 9, ty + 8)], fill=v_col, width=2)
            else:
                draw.line([(arr_x, ty + 3), (arr_x + 9, ty + 12)], fill=v_col, width=2)
                draw.line([(arr_x + 4, ty + 12), (arr_x + 9, ty + 12), (arr_x + 9, ty + 7)], fill=v_col, width=2)
                
        # Card Middle Divider
        draw.line([(cx1 + 12, cy1 + 176), (cx2 - 12, cy1 + 176)], fill=(12, 35, 75), width=1)
        
        # Support & Resistance Horizontal Range Slider (Weekly SNR)
        d_supp = d.get("support", d.get("low", price_val * 0.99))
        d_res = d.get("resistance", d.get("high", price_val * 1.01))
        
        # Combined Tags above bar
        draw.rounded_rectangle([(cx1 + 14, cy1 + 184), (cx1 + 130, cy1 + 210)], radius=4, fill=(10, 45, 30), outline=(0, 220, 110), width=1)
        draw.text((cx1 + 72, cy1 + 197), f"S: {d_supp:,.{digits}f}", fill=(0, 255, 136), font=f_bar_num, anchor="mm")
        
        draw.rounded_rectangle([(cx2 - 130, cy1 + 184), (cx2 - 14, cy1 + 210)], radius=4, fill=(50, 15, 20), outline=(240, 60, 60), width=1)
        draw.text((cx2 - 72, cy1 + 197), f"R: {d_res:,.{digits}f}", fill=(255, 80, 80), font=f_bar_num, anchor="mm")
        
        # Slider Track
        sx1, sx2 = cx1 + 16, cx2 - 16
        sw = sx2 - sx1
        sy1, sy2 = cy1 + 242, cy1 + 252
        
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
            
        pct_range = (price_val - d_supp) / (d_res - d_supp) * 100.0 if d_res > d_supp else 50.0
        pct_clamp = max(0.0, min(100.0, pct_range))
        pin_x = sx1 + int(sw * (pct_clamp / 100.0))
        
        # Tooltip badge on slider
        draw.rounded_rectangle([(pin_x - 30, sy1 - 24), (pin_x + 30, sy1 - 4)], radius=4, fill=(255, 214, 0))
        draw.text((pin_x, sy1 - 14), f"{pct_range:.1f}%", fill=(0, 0, 0), font=get_font(12, bold=True), anchor="mm")
        draw.line([(pin_x, sy1 - 4), (pin_x, sy2)], fill=(255, 214, 0), width=2)
        draw.ellipse([(pin_x - 5, (sy1+sy2)//2 - 5), (pin_x + 5, (sy1+sy2)//2 + 5)], fill=(0, 180, 255), outline=(255, 255, 255))
        
        # Ticks below bar: 0%, 25%, 50%, 75%, 100%
        f_tks = get_font(11, bold=False)
        draw.text((sx1, sy2 + 4), "0%", fill=(120, 160, 215), font=f_tks)
        draw.text((sx1 + int(sw*0.25), sy2 + 4), "25%", fill=(120, 160, 215), font=f_tks, anchor="ma")
        draw.text((sx1 + int(sw*0.50), sy2 + 4), "50%", fill=(120, 160, 215), font=f_tks, anchor="ma")
        draw.text((sx1 + int(sw*0.75), sy2 + 4), "75%", fill=(120, 160, 215), font=f_tks, anchor="ma")
        draw.text((sx2, sy2 + 4), "100%", fill=(120, 160, 215), font=f_tks, anchor="ra")
        
        draw.text(((sx1+sx2)//2, sy2 + 22), f"Live: {price_val:,.{digits}f} (%SNR: {pct_range:.1f}%)", fill=(160, 205, 255), font=get_font(13, bold=False), anchor="mm")
        
        # Card Bottom Divider
        draw.line([(cx1 + 12, cy1 + 288), (cx2 - 12, cy1 + 288)], fill=(12, 35, 75), width=1)
        
        # Inflow / Outflow / Net / Flow Intensity
        in_b = d.get("inflow", 320)
        out_b = d.get("outflow", 280)
        net_b = in_b - out_b
        net_sgn = "+" if net_b >= 0 else ""
        net_col = (0, 255, 136) if net_b >= 0 else (255, 75, 75)
        
        f_io_lbl = get_font(12, bold=True)
        draw.text((cx1 + 42, cy1 + 296), "INFLOW", fill=(130, 175, 230), font=f_io_lbl, anchor="mm")
        draw.text((cx1 + 126, cy1 + 296), "OUTFLOW", fill=(130, 175, 230), font=f_io_lbl, anchor="mm")
        draw.text((cx1 + 210, cy1 + 296), "NET", fill=(130, 175, 230), font=f_io_lbl, anchor="mm")
        draw.text((cx1 + 305, cy1 + 296), "INTENSITY", fill=(130, 175, 230), font=f_io_lbl, anchor="mm")
        
        draw.text((cx1 + 42, cy1 + 326), f"{in_b}B", fill=(0, 255, 136), font=get_font(18, bold=True), anchor="mm")
        draw.text((cx1 + 126, cy1 + 326), f"{out_b}B", fill=(255, 75, 75), font=get_font(18, bold=True), anchor="mm")
        draw.text((cx1 + 210, cy1 + 326), f"{net_sgn}{net_b}B", fill=net_col, font=get_font(18, bold=True), anchor="mm")
        
        intensity = d.get("intensity", 75)
        draw_flow_meter_2x(draw, cx1 + 305, cy1 + 332, radius=26, pct=intensity, col=(0, 230, 120) if intensity > 60 else (220, 200, 40))
        
        # Bottom Badge (Status Verdict)
        verdict = d.get("verdict", "INSTITUTIONAL ACCUMULATION" if net_b > 0 else "INSTITUTIONAL DISTRIBUTION")
        v_bg = (4, 45, 25) if net_b > 0 else (45, 15, 20)
        v_col = (0, 255, 136) if net_b > 0 else (255, 80, 80)
        draw.rounded_rectangle([(cx1 + 14, cy1 + 358), (cx2 - 14, cy1 + 392)], radius=5, fill=v_bg, outline=v_col, width=1)
        draw.text(((cx1+cx2)//2, cy1 + 375), verdict, fill=v_col, font=get_font(14, bold=True), anchor="mm")

    # =========================================================================
    # 3. BOTTOM 8 INSTITUTIONAL MATRIX PANELS (Y: 516 to 1066)
    # =========================================================================
    # Row 1 (Y: 516 to 784) - Height 268px
    # Grid 1: Major FX Money Flow (X: 16 to 430)
    draw.rounded_rectangle([(16, 516), (430, 784)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((28, 524), "MAJOR FX MONEY FLOW (JILLYWOSY INDEX)", fill=(255, 214, 0), font=f_hdr_box)
    draw.text((28, 546), "CURRENCY    SCORE   FLOW BAR       1D       1W     TREND", fill=(120, 160, 210), font=f_sub_hdr)
    draw.line([(24, 562), (422, 562)], fill=(12, 35, 75), width=1)
    
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
        ry = 568 + r_i * 26
        draw.text((28, ry), f_curr, fill=(255, 255, 255), font=f_cell_bold)
        sc_col = (0, 255, 136) if f_sc > 0 else (255, 75, 75)
        draw.text((95, ry), f"{f_sc:+d}", fill=sc_col, font=f_cell_bold)
        
        # Flow bar
        draw.rounded_rectangle([(140, ry + 2), (230, ry + 14)], radius=2, fill=(10, 20, 40))
        b_w = int(abs(f_sc) / 100.0 * 45)
        if f_sc > 0:
            draw.rounded_rectangle([(185, ry + 2), (185 + b_w, ry + 14)], radius=2, fill=(0, 230, 120))
        else:
            draw.rounded_rectangle([(185 - b_w, ry + 2), (185, ry + 14)], radius=2, fill=(240, 50, 60))
            
        draw.text((250, ry), f_1d, fill=sc_col, font=f_cell)
        draw.text((315, ry), f_1w, fill=(180, 210, 245), font=f_cell)
        
        t_col = (0, 255, 136) if f_tr == "UP" else ((255, 75, 75) if f_tr == "DOWN" else (220, 200, 40))
        t_sym = "▲" if f_tr == "UP" else ("▼" if f_tr == "DOWN" else "▶")
        draw.text((385, ry), t_sym, fill=t_col, font=f_cell_bold)
        
    # Grid 2: Global Capital Flow Map (X: 442 to 1180, Y: 516 to 784) [width 738px]
    draw.rounded_rectangle([(442, 516), (1180, 784)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((456, 524), "GLOBAL CAPITAL FLOW MAP (REGIONAL MACRO DYNAMICS)", fill=(0, 229, 255), font=f_hdr_box)
    draw.line([(450, 546), (1172, 546)], fill=(12, 35, 75), width=1)
    
    regions = [
        ("N. AMERICA", "+42", "Capital Inflow", "USD ↑ Equities ↑", 475, 560, (0, 230, 120)),
        ("EUROPE", "-28", "Capital Outflow", "EUR ↓ Bonds ↑", 735, 560, (240, 50, 60)),
        ("ASIA PACIFIC", "+18", "Moderate Inflow", "JPY ↑ Commodities ↑", 965, 560, (0, 210, 140)),
        ("LATAM", "-12", "Risk Off", "Commodity Outflow", 535, 670, (240, 70, 70)),
        ("MIDDLE EAST", "+24", "Petrodollar Inflow", "Oil ↑ USD Reserves", 845, 670, (0, 230, 120)),
    ]
    for r_name, r_sc, r_fl, r_desc, rx, ry, r_col in regions:
        draw.rounded_rectangle([(rx, ry), (rx + 165, ry + 82)], radius=5, fill=(4, 20, 42), outline=r_col, width=1)
        draw.text((rx + 82, ry + 14), r_name, fill=(255, 255, 255), font=get_font(13, bold=True), anchor="mm")
        draw.text((rx + 82, ry + 36), r_sc, fill=r_col, font=get_font(22, bold=True), anchor="mm")
        draw.text((rx + 82, ry + 54), r_fl, fill=r_col, font=get_font(12, bold=True), anchor="mm")
        draw.text((rx + 82, ry + 70), r_desc, fill=(140, 180, 220), font=get_font(11, bold=False), anchor="mm")
        
    # Flow Vector Arrows
    draw.line([(640, 601), (735, 601)], fill=(0, 255, 200), width=3)
    draw.line([(820, 642), (860, 670)], fill=(240, 80, 80), width=3)
    draw.line([(965, 642), (935, 670)], fill=(0, 255, 136), width=3)
    
    # Legend below map
    draw.text((495, 762), "■ Capital Inflow (Hijau)", fill=(0, 255, 136), font=get_font(12, bold=True))
    draw.text((695, 762), "■ Capital Outflow (Merah)", fill=(255, 80, 80), font=get_font(12, bold=True))
    draw.text((895, 762), "● High Flow Intensity", fill=(0, 229, 255), font=get_font(12, bold=True))
    
    # Grid 3: Commodity Money Flow (X: 1192 to 1550, Y: 516 to 784) [width 358px]
    draw.rounded_rectangle([(1192, 516), (1550, 784)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((1204, 524), "COMMODITY MONEY FLOW", fill=(255, 214, 0), font=f_hdr_box)
    draw.text((1204, 546), "ASSET      SCORE  FLOW    1D     1W   TREND", fill=(120, 160, 210), font=f_sub_hdr)
    draw.line([(1200, 562), (1542, 562)], fill=(12, 35, 75), width=1)
    
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
        cy = 568 + c_i * 26
        draw.text((1204, cy), c_name, fill=(255, 255, 255), font=f_cell_bold)
        sc_col = (0, 255, 136) if c_sc > 0 else (255, 75, 75)
        draw.text((1280, cy), f"{c_sc:+d}", fill=sc_col, font=f_cell_bold)
        
        draw.rounded_rectangle([(1320, cy + 2), (1375, cy + 14)], radius=2, fill=(10, 20, 40))
        b_w = int(abs(c_sc) / 100.0 * 27)
        if c_sc > 0:
            draw.rounded_rectangle([(1347, cy + 2), (1347 + b_w, cy + 14)], radius=2, fill=(0, 230, 120))
        else:
            draw.rounded_rectangle([(1347 - b_w, cy + 2), (1347, cy + 14)], radius=2, fill=(240, 50, 60))
            
        draw.text((1395, cy), c_1d, fill=sc_col, font=f_cell)
        draw.text((1460, cy), c_1w, fill=(180, 210, 245), font=f_cell)
        t_col = (0, 255, 136) if c_tr == "UP" else ((255, 75, 75) if c_tr == "DOWN" else (220, 200, 40))
        draw.text((1525, cy), "▲" if c_tr == "UP" else ("▼" if c_tr == "DOWN" else "▶"), fill=t_col, font=f_cell_bold)
        
    # Grid 4: Index Money Flow (X: 1562 to 1904, Y: 516 to 784) [width 342px]
    draw.rounded_rectangle([(1562, 516), (1904, 784)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((1574, 524), "GLOBAL INDEX MONEY FLOW", fill=(255, 214, 0), font=f_hdr_box)
    draw.text((1574, 546), "INDEX      SCORE  FLOW    1D     1W   TREND", fill=(120, 160, 210), font=f_sub_hdr)
    draw.line([(1570, 562), (1896, 562)], fill=(12, 35, 75), width=1)
    
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
        iy = 568 + idx_i * 26
        draw.text((1574, iy), id_name, fill=(255, 255, 255), font=f_cell_bold)
        sc_col = (0, 255, 136) if id_sc > 0 else (255, 75, 75)
        draw.text((1645, iy), f"{id_sc:+d}", fill=sc_col, font=f_cell_bold)
        
        draw.rounded_rectangle([(1685, iy + 2), (1740, iy + 14)], radius=2, fill=(10, 20, 40))
        b_w = int(abs(id_sc) / 100.0 * 27)
        if id_sc > 0:
            draw.rounded_rectangle([(1712, iy + 2), (1712 + b_w, iy + 14)], radius=2, fill=(0, 230, 120))
        else:
            draw.rounded_rectangle([(1712 - b_w, iy + 2), (1712, iy + 14)], radius=2, fill=(240, 50, 60))
            
        draw.text((1760, iy), id_1d, fill=sc_col, font=f_cell)
        draw.text((1825, iy), id_1w, fill=(180, 210, 245), font=f_cell)
        t_col = (0, 255, 136) if id_tr == "UP" else ((255, 75, 75) if id_tr == "DOWN" else (220, 200, 40))
        draw.text((1885, iy), "▲" if id_tr == "UP" else ("▼" if id_tr == "DOWN" else "▶"), fill=t_col, font=f_cell_bold)
        
    # Row 2 (Y: 794 to 1066) - Height 272px
    # Grid 5: Bond & Yield Flow (X: 16 to 340) [width 324px]
    draw.rounded_rectangle([(16, 794), (340, 1066)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((28, 802), "BOND & YIELD FLOW", fill=(0, 229, 255), font=f_hdr_box)
    draw.text((28, 824), "TENOR       YIELD      Δ(bps)     FLOW", fill=(120, 160, 210), font=f_sub_hdr)
    draw.line([(24, 840), (332, 840)], fill=(12, 35, 75), width=1)
    
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
        yy = 848 + y_i * 29
        draw.text((28, yy), y_t, fill=(255, 255, 255), font=f_cell_bold)
        draw.text((112, yy), y_v, fill=(200, 230, 255), font=f_cell)
        d_col = (0, 255, 136) if "+" in y_d else (255, 75, 75)
        draw.text((195, yy), y_d, fill=d_col, font=f_cell_bold)
        draw.text((285, yy), "▲" if y_tr == "UP" else "▼", fill=d_col, font=f_cell_bold)
        
    # Grid 6: Sector Money Flow (S&P 500) (X: 352 to 720) [width 368px]
    draw.rounded_rectangle([(352, 794), (720, 1066)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((364, 802), "SECTOR MONEY FLOW (S&P 500)", fill=(0, 229, 255), font=f_hdr_box)
    draw.text((364, 824), "SECTOR            SCORE    FLOW BAR       TREND", fill=(120, 160, 210), font=f_sub_hdr)
    draw.line([(360, 840), (712, 840)], fill=(12, 35, 75), width=1)
    
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
        sy = 848 + s_i * 29
        draw.text((364, sy), sec_n, fill=(255, 255, 255), font=f_cell_bold)
        sc_col = (0, 255, 136) if sec_sc > 0 else (255, 75, 75)
        draw.text((505, sy), f"{sec_sc:+d}", fill=sc_col, font=f_cell_bold)
        
        draw.rounded_rectangle([(550, sy + 2), (630, sy + 14)], radius=2, fill=(10, 20, 40))
        b_w = int(abs(sec_sc) / 100.0 * 40)
        if sec_sc > 0:
            draw.rounded_rectangle([(590, sy + 2), (590 + b_w, sy + 14)], radius=2, fill=(0, 230, 120))
        else:
            draw.rounded_rectangle([(590 - b_w, sy + 2), (590, sy + 14)], radius=2, fill=(240, 50, 60))
        draw.text((675, sy), "▲" if sec_tr == "UP" else "▼", fill=sc_col, font=f_cell_bold)
        
    # Grid 7: Top Flow Movers (X: 732 to 1180) [width 448px]
    draw.rounded_rectangle([(732, 794), (1180, 1066)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((744, 802), "TOP FLOW MOVERS (REAL TIME)", fill=(0, 229, 255), font=f_hdr_box)
    
    draw.rounded_rectangle([(744, 826), (945, 848)], radius=4, fill=(10, 45, 25))
    draw.text((844, 837), "TOP INFLOW", fill=(0, 255, 136), font=get_font(12, bold=True), anchor="mm")
    
    draw.rounded_rectangle([(965, 826), (1168, 848)], radius=4, fill=(50, 15, 20))
    draw.text((1066, 837), "TOP OUTFLOW", fill=(255, 80, 80), font=get_font(12, bold=True), anchor="mm")
    
    inflows = [("USD", "+78"), ("OIL", "+56"), ("JPY", "+45"), ("ENERGY", "+42"), ("SILVER", "+32"), ("COPPER", "+26")]
    outflows = [("GOLD", "-62"), ("EUR", "-21"), ("GBP", "-34"), ("TECH", "-34"), ("US100", "-41"), ("NZD", "-14")]
    
    for m_i in range(6):
        my = 858 + m_i * 32
        in_a, in_s = inflows[m_i]
        out_a, out_s = outflows[m_i]
        
        draw.text((752, my), in_a, fill=(255, 255, 255), font=f_cell_bold)
        draw.text((935, my), in_s, fill=(0, 255, 136), font=f_cell_bold, anchor="ra")
        
        draw.text((975, my), out_a, fill=(255, 255, 255), font=f_cell_bold)
        draw.text((1158, my), out_s, fill=(255, 75, 75), font=f_cell_bold, anchor="ra")
        
    # Grid 8: Multi-Asset Flow Alignment Heatmap (X: 1192 to 1904, Y: 794 to 1066) [width 712px]
    draw.rounded_rectangle([(1192, 794), (1904, 1066)], radius=6, fill=(3, 14, 32), outline=(12, 40, 85), width=1)
    draw.text((1204, 802), "FLOW ALIGNMENT HEATMAP (MULTI-ASSET & TIMEFRAME)", fill=(0, 229, 255), font=f_hdr_box)
    draw.line([(1200, 822), (1896, 822)], fill=(12, 35, 75), width=1)
    
    cols_hm = ["ASSET", "M5", "M15", "H1", "H4", "D1", "1W", "AGGREGATE STATUS"]
    col_xs = [1206, 1290, 1354, 1418, 1482, 1546, 1610, 1690]
    for c_idx, c_title in enumerate(cols_hm):
        draw.text((col_xs[c_idx], 830), c_title, fill=(120, 160, 210), font=f_sub_hdr)
        
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
        hy = 852 + h_i * 28
        draw.text((col_xs[0], hy + 4), h_ast, fill=(255, 255, 255), font=f_cell_bold)
        
        for v_i, val in enumerate(h_vals):
            bx = col_xs[1 + v_i]
            if val == 2: b_c = (0, 180, 80)
            elif val == 1: b_c = (0, 230, 120)
            elif val == 0: b_c = (210, 190, 40)
            elif val == -1: b_c = (230, 90, 60)
            else: b_c = (190, 30, 40)
            
            draw.rounded_rectangle([(bx, hy), (bx + 52, hy + 22)], radius=3, fill=b_c)
            v_str = "BUY" if val > 0 else ("SELL" if val < 0 else "NEUT")
            draw.text((bx + 26, hy + 11), v_str, fill=(0, 0, 0) if val==0 else (255, 255, 255), font=get_font(11, bold=True), anchor="mm")
            
        stat_col = (0, 255, 136) if "ACCUMULATION" in h_verdict or "DOMINANCE" in h_verdict else ((255, 75, 75) if "DISTRIBUTION" in h_verdict or "OUTFLOW" in h_verdict else (220, 200, 40))
        draw.text((col_xs[7], hy + 4), h_verdict, fill=stat_col, font=get_font(13, bold=True))
        
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path, "PNG", optimize=True)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

if __name__ == "__main__":
    from backend.telegram.money_flow_engine import MoneyFlowRadarEngine
    eng = MoneyFlowRadarEngine()
    data = eng.fetch_live_market_data()
    out = r"C:\Users\ACER\.gemini\antigravity\brain\558a85bc-66f2-430d-b5c2-57d9b5fa3ae7\test_money_flow_2x.png"
    render_money_flow_radar_2x(data, output_path=out)
    print("Rendered Money Flow 2X successfully to", out)
