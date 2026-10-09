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

def draw_flag_icon(draw, cx, cy, r, p_type):
    if p_type == "gold":
        # 3D Gold bars
        draw.polygon([(cx - 14, cy + 2), (cx + 2, cy + 2), (cx + 8, cy - 7), (cx - 8, cy - 7)], fill=(255, 215, 0), outline=(218, 165, 32))
        draw.polygon([(cx - 8, cy + 9), (cx + 8, cy + 9), (cx + 14, cy), (cx - 2, cy)], fill=(255, 195, 0), outline=(184, 134, 11))
    elif p_type == "oil":
        # 3D Oil droplet
        draw_sphere(draw, cx, cy + 3, r - 3, (120, 130, 145))
        draw.polygon([(cx, cy - 11), (cx - 6, cy + 3), (cx + 6, cy + 3)], fill=(20, 25, 35))
    elif p_type == "eur":
        # EU blue circle with circle of stars
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(0, 51, 153), outline=(40, 90, 200), width=1)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            sx = int(cx + (r - 4) * math.cos(rad))
            sy = int(cy + (r - 4) * math.sin(rad))
            draw.ellipse([(sx - 1, sy - 1), (sx + 1, sy + 1)], fill=(255, 204, 0))
    elif p_type == "jpy":
        # Japan flag circle
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(255, 255, 255), outline=(180, 180, 180), width=1)
        draw.ellipse([(cx - r//2, cy - r//2), (cx + r//2, cy + r//2)], fill=(188, 0, 45))
    else:
        draw_sphere(draw, cx, cy, r, (0, 170, 255))

def draw_gradient_bar(draw, x1, y1, x2, y2):
    total_w = x2 - x1
    for x in range(x1, x2):
        pos = (x - x1) / total_w
        if pos < 0.20:
            col = (0, 225, 115)
        elif pos < 0.40:
            t = (pos - 0.20) / 0.20
            col = (int(0 + 200 * t), int(225 - 25 * t), 40)
        elif pos < 0.60:
            col = (210, 200, 0)
        elif pos < 0.80:
            t = (pos - 0.60) / 0.20
            col = (int(210 + 35 * t), int(200 - 130 * t), int(0 + 50 * t))
        else:
            col = (245, 55, 65)
        draw.line([(x, y1), (x, y2)], fill=col, width=1)

def draw_circular_gauge(draw, cx, cy, radius, value, max_val, active_color, bg_color=(15, 30, 55), text=None, text_color=(255, 255, 255), font=None):
    bbox = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    draw.arc(bbox, start=-90, end=270, fill=bg_color, width=5)
    pct = max(0.0, min(1.0, value / max_val))
    sweep = int(pct * 360)
    if sweep > 0:
        draw.arc(bbox, start=-90, end=-90 + sweep, fill=active_color, width=5)
    if text and font:
        draw.text((cx, cy), text, fill=text_color, font=font, anchor="mm")

def draw_donut_ratio(draw, cx, cy, radius, buy_pct, font_inner):
    bbox = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    buy_ang = int(buy_pct * 3.6)
    draw.pieslice(bbox, start=-90, end=-90 + buy_ang, fill=(0, 240, 120))
    draw.pieslice(bbox, start=-90 + buy_ang, end=270, fill=(240, 55, 55))
    inner_r = radius - 5
    draw.ellipse([(cx - inner_r, cy - inner_r), (cx + inner_r, cy + inner_r)], fill=(3, 14, 34))
    draw.text((cx, cy - 4), f"{buy_pct}%", fill=(0, 255, 136), font=font_inner, anchor="mm")
    sell_pct = 100 - buy_pct
    draw.text((cx, cy + 6), f"{sell_pct}%", fill=(255, 90, 90), font=font_inner, anchor="mm")

def draw_vector_arrow(draw, cx, cy, direction):
    if direction == "UP":
        col = (0, 255, 136)
        draw.line([(cx - 6, cy + 6), (cx + 6, cy - 6)], fill=col, width=3)
        draw.line([(cx - 1, cy - 6), (cx + 6, cy - 6)], fill=col, width=3)
        draw.line([(cx + 6, cy - 6), (cx + 6, cy + 1)], fill=col, width=3)
    elif direction == "DOWN":
        col = (255, 75, 75)
        draw.line([(cx - 6, cy - 6), (cx + 6, cy + 6)], fill=col, width=3)
        draw.line([(cx - 1, cy + 6), (cx + 6, cy + 6)], fill=col, width=3)
        draw.line([(cx + 6, cy + 6), (cx + 6, cy - 1)], fill=col, width=3)
    else:
        col = (255, 214, 0)
        draw.line([(cx - 6, cy), (cx + 6, cy)], fill=col, width=3)
        draw.line([(cx + 1, cy - 5), (cx + 6, cy)], fill=col, width=3)
        draw.line([(cx + 1, cy + 5), (cx + 6, cy)], fill=col, width=3)

def render_bloomberg_dashboard_card(data_list: list, output_path: str = None) -> Image.Image:
    W, H = 1920, 1080
    img = Image.new("RGBA", (W, H), (2, 8, 20, 255))
    draw = ImageDraw.Draw(img)

    # Grid background
    for x in range(0, W, 48):
        draw.line([(x, 0), (x, H)], fill=(5, 18, 42), width=1)
    for y in range(0, H, 48):
        draw.line([(0, y), (W, y)], fill=(5, 18, 42), width=1)

    # Outer border
    draw.rounded_rectangle([(8, 8), (W - 8, H - 8)], radius=10, outline=(0, 120, 240), width=2)

    # LARGER & CRISPER TYPOGRAPHY
    f_date = get_font(16, bold=False)
    f_time = get_font(28, bold=True)
    f_live = get_font(15, bold=True)
    f_main_title = get_font(28, bold=True)
    f_main_sub = get_font(15, bold=True)
    f_mode_title = get_font(15, bold=True)
    f_mode_sub = get_font(13, bold=False)
    f_news_title = get_font(14, bold=True)
    f_news_sub = get_font(12, bold=False)
    f_news_val = get_font(14, bold=True)

    f_hdr = get_font(16, bold=True)
    f_hdr_sub = get_font(13, bold=False)
    f_pair = get_font(26, bold=True)
    f_sub = get_font(14, bold=False)
    f_price = get_font(30, bold=True)
    f_chg = get_font(16, bold=True)
    f_chg_pct = get_font(14, bold=False)
    f_lvl_num = get_font(18, bold=True)
    f_snr_tick = get_font(14, bold=True)
    f_zone_box = get_font(13, bold=True)
    f_vol_num = get_font(17, bold=True)
    f_donut = get_font(14, bold=True)
    f_delta = get_font(22, bold=True)
    f_delta_sub = get_font(13, bold=False)
    f_trend = get_font(17, bold=True)
    f_grade = get_font(34, bold=True)
    f_status = get_font(20, bold=True)
    f_status_sub = get_font(13, bold=False)
    f_tick_mode_badge = get_font(16, bold=True)
    f_tick_mode_sub = get_font(13, bold=False)
    f_tpsl = get_font(14, bold=False)
    f_tpsl_num = get_font(15, bold=True)
    f_rr = get_font(19, bold=True)

    now_wib = datetime.now(WIB)
    date_str = now_wib.strftime("%a, %d %b %Y")
    time_str = now_wib.strftime("%H:%M:%S")

    # 1. TOP HEADER (Y: 14 to 86)
    # Left Box: Date / Time / LIVE
    draw.rounded_rectangle([(18, 14), (225, 86)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((28, 18), date_str, fill=(145, 185, 230), font=f_date)
    draw.text((28, 38), time_str, fill=(255, 255, 255), font=f_time)
    draw.rounded_rectangle([(152, 42), (216, 72)], radius=12, fill=(0, 60, 30), outline=(0, 220, 110), width=1)
    draw.text((187, 57), "LIVE", fill=(0, 255, 136), font=f_live, anchor="mm")
    draw.ellipse([(160, 54), (168, 62)], fill=(0, 255, 136))

    # Center Title & Subtitle
    draw.text((950, 32), "SNR + TICK MODE PROTOCOL + CONFIDENCE + SIGNAL GRADE", fill=(255, 220, 0), font=f_main_title, anchor="mm")
    draw.text((950, 66), "LOCATION → TICK FLOW RATIO → DELTA PRESSURE → TICK MODE EXECUTION → BASKET EXIT", fill=(0, 229, 255), font=f_main_sub, anchor="mm")

    # Right Box 1: TICK MODE ACTIVE Toggle
    draw.rounded_rectangle([(1435, 14), (1695, 86)], radius=6, fill=(3, 25, 25), outline=(0, 180, 90), width=1)
    draw.text((1448, 24), "TICK MODE: ACTIVE", fill=(0, 255, 136), font=f_mode_title)
    draw.text((1448, 52), "Basket L1-L2 + Dynamic Exit", fill=(130, 215, 255), font=f_mode_sub)
    draw.rounded_rectangle([(1635, 34), (1683, 64)], radius=12, fill=(0, 200, 100))
    draw.ellipse([(1659, 36), (1681, 62)], fill=(255, 255, 255))

    # Right Box 2: NEWS FILTER
    draw.rounded_rectangle([(1705, 14), (1902, 86)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((1716, 22), "NEWS FILTER", fill=(200, 225, 250), font=f_news_title)
    draw.rounded_rectangle([(1832, 20), (1892, 44)], radius=9, fill=(0, 200, 100))
    draw.text((1862, 32), "LOW", fill=(0, 0, 0), font=get_font(13, bold=True), anchor="mm")
    draw.text((1716, 46), "Next High Impact", fill=(140, 175, 215), font=f_news_sub)
    draw.text((1716, 64), "USD: NFP 5h 35m", fill=(255, 255, 255), font=f_news_val)

    # Header Divider Line
    draw.line([(18, 92), (W - 18, 92)], fill=(18, 60, 125), width=2)

    # 2. MAIN TABLE HEADER (Y: 96 to 142) - 10 BALANCED COLUMNS
    COLS = [
        ("PAIR", "", 18, 155),
        ("LIVE PRICE", "CHANGE (%)", 158, 305),
        ("SNR & PRICE LEVELS", "(S | RevUp | %SNR | RevDn | R)", 308, 665),
        ("TICK FLOW", "(Buy / Sell)", 668, 805),
        ("DELTA & RATIO", "(B-S / Pressure)", 808, 948),
        ("TREND & REV", "(MA / Score)", 951, 1072),
        ("CONF & ACTION", "(Confidence / Action)", 1075, 1205),
        ("TICK MODE (DAILY)", "(Basket Protocol)", 1208, 1410),
        ("GRADE & STATUS", "(Signal Grade)", 1413, 1635),
        ("DAILY TP / SL", "(TP1-3 | SL | R:R)", 1638, 1902),
    ]

    HDR_TEXT_COL = (215, 240, 255)
    for title, sub, x1, x2 in COLS:
        cx = (x1 + x2) // 2
        draw.rounded_rectangle([(x1, 96), (x2, 142)], radius=4, fill=(3, 16, 38), outline=(12, 45, 95), width=1)
        if sub and "\n" not in title:
            draw.text((cx, 108), title, fill=HDR_TEXT_COL, font=f_hdr, anchor="mm")
            draw.text((cx, 128), sub, fill=(130, 185, 235), font=f_hdr_sub, anchor="mm")
        elif "\n" in title:
            lines = title.split("\n")
            draw.text((cx, 108), lines[0], fill=HDR_TEXT_COL, font=f_hdr, anchor="mm")
            draw.text((cx, 127), lines[1], fill=HDR_TEXT_COL, font=f_hdr, anchor="mm")
        else:
            draw.text((cx, 119), title, fill=HDR_TEXT_COL, font=f_hdr, anchor="mm", align="center")

    # 3. FOUR INSTRUMENT ROWS (Y: 148 to 800)
    ROW_H = 162
    Y_START = 148

    for i, item in enumerate(data_list):
        r_top = Y_START + i * ROW_H
        r_btm = r_top + ROW_H - 6
        r_mid = (r_top + r_btm) // 2
        
        draw.rounded_rectangle([(18, r_top), (W - 18, r_btm)], radius=6, fill=(3, 14, 34), outline=(10, 40, 85), width=1)

        # 1. PAIR [18, 155]
        c_x1, c_x2 = 18, 155
        draw_flag_icon(draw, c_x1 + 24, r_mid - 2, 18, item.get("icon_type", "gold"))
        p_name = item["name"]
        p_col = (255, 214, 0) if p_name == "GOLD" else (255, 255, 255)
        draw.text((c_x1 + 54, r_mid - 22), p_name, fill=p_col, font=f_pair)
        draw.text((c_x1 + 54, r_mid + 8), item["subtitle"], fill=(155, 200, 255), font=f_sub)

        # 2. LIVE PRICE & CHANGE [158, 305]
        c_x1, c_x2 = 158, 305
        cx = (c_x1 + c_x2) // 2
        p_val = item["price"]
        digits = item.get("digits", 2)
        chg = item.get("change_val", item.get("change", 0.0))
        chg_pct = item.get("change_pct", 0.0)
        chg_sgn = "+" if chg >= 0 else ""
        chg_col = (0, 255, 136) if chg >= 0 else (255, 75, 75)
        draw.text((cx, r_mid - 16), f"{p_val:,.{digits}f}", fill=(255, 255, 255), font=f_price, anchor="mm")
        draw.text((cx, r_mid + 16), f"{chg_sgn}{chg:.{digits}f} ({chg_sgn}{chg_pct:.2f}%)", fill=chg_col, font=f_chg, anchor="mm")

        # 3. SNR & PRICE LEVELS [308, 665]
        c_x1, c_x2 = 308, 665
        BAR_X1 = c_x1 + 16
        BAR_X2 = c_x2 - 16
        BAR_W = BAR_X2 - BAR_X1

        supp = item["support"]
        res = item["resistance"]
        rev_up = supp + 0.20 * (res - supp)
        rev_dn = supp + 0.80 * (res - supp)

        cx_supp = BAR_X1
        cx_rup = BAR_X1 + int(BAR_W * 0.20)
        cx_mid = BAR_X1 + int(BAR_W * 0.50)
        cx_rdn = BAR_X1 + int(BAR_W * 0.80)
        cx_res = BAR_X2

        # Support & Resistance Labels (Bigger & Bolder)
        draw.text((cx_supp, r_mid - 46), f"S: {supp:,.{digits}f}", fill=(0, 255, 136), font=f_lvl_num, anchor="la")
        draw.text((cx_res, r_mid - 46), f"R: {res:,.{digits}f}", fill=(255, 75, 75), font=f_lvl_num, anchor="ra")
        
        # Intermediate Reversal Zones
        draw.text((cx_rup, r_mid - 25), f"RevUp: {rev_up:,.{digits}f}", fill=(130, 240, 180), font=get_font(13, bold=False), anchor="ma")
        draw.text((cx_rdn, r_mid - 25), f"RevDn: {rev_dn:,.{digits}f}", fill=(255, 150, 150), font=get_font(13, bold=False), anchor="ma")

        # Color Gradient Bar
        draw_gradient_bar(draw, BAR_X1, r_mid - 6, BAR_X2, r_mid + 4)

        # Needle position based on %SNR
        pct_snr = item["pct_snr"]
        clamped_pct = max(0.0, min(100.0, pct_snr))
        needle_x = BAR_X1 + int(BAR_W * (clamped_pct / 100.0))

        # Needle pointer
        draw.line([(needle_x, r_mid - 16), (needle_x, r_mid + 14)], fill=(255, 255, 255), width=3)
        draw.ellipse([(needle_x - 5, r_mid - 6), (needle_x + 5, r_mid + 4)], fill=(255, 255, 255))
        
        # Badge %SNR
        badge_w = 68
        bx1 = max(BAR_X1, min(BAR_X2 - badge_w, needle_x - badge_w // 2))
        draw.rounded_rectangle([(bx1, r_mid + 16), (bx1 + badge_w, r_mid + 40)], radius=4, fill=(10, 45, 95), outline=(0, 210, 255), width=1)
        draw.text((bx1 + badge_w // 2, r_mid + 28), f"{pct_snr:.1f}%", fill=(0, 255, 255), font=f_snr_tick, anchor="mm")

        # Zone labels
        draw.text((cx_supp + 28, r_mid + 50), "BUY ZONE", fill=(0, 255, 136), font=f_zone_box, anchor="mm")
        draw.text((cx_mid, r_mid + 50), "MID / WAIT", fill=(255, 220, 0), font=f_zone_box, anchor="mm")
        draw.text((cx_res - 28, r_mid + 50), "SELL ZONE", fill=(255, 75, 75), font=f_zone_box, anchor="mm")

        # 4. TICK FLOW & RATIO [668, 805]
        c_x1, c_x2 = 668, 805
        b_tick = item.get("buy_tick", 1200)
        s_tick = item.get("sell_tick", 1000)
        buy_pct = item.get("buy_pct", 55)
        
        # Donut Ratio on left side of cell
        d_cx = c_x1 + 34
        draw_donut_ratio(draw, d_cx, r_mid, 26, buy_pct, f_donut)
        # Numbers on right side of cell with clean left-alignment
        t_x = c_x1 + 68
        draw.text((t_x, r_mid - 16), f"B: {b_tick:,}", fill=(0, 255, 136), font=f_vol_num, anchor="lm")
        draw.text((t_x, r_mid + 14), f"S: {s_tick:,}", fill=(255, 75, 75), font=f_vol_num, anchor="lm")

        # 5. DELTA & PRESSURE [808, 948]
        c_x1, c_x2 = 808, 948
        cx = (c_x1 + c_x2) // 2
        delta = item.get("delta", 200)
        total_ticks = max(1, b_tick + s_tick)
        delta_pct = (delta / total_ticks) * 100.0
        d_sgn = "+" if delta >= 0 else ""
        d_col = (0, 255, 136) if delta >= 0 else (255, 75, 75)
        
        draw.text((cx, r_mid - 24), f"{d_sgn}{delta:,}", fill=d_col, font=f_delta, anchor="mm")
        draw.text((cx, r_mid - 4), f"Δ: {d_sgn}{delta_pct:.1f}%", fill=(160, 200, 240), font=f_delta_sub, anchor="mm")

        press = item.get("pressure", "BALANCED")
        pr_col = (0, 255, 136) if "BUY" in press else ((255, 75, 75) if "SELL" in press else (255, 220, 0))
        pr_bg = (10, 45, 30) if "BUY" in press else ((45, 15, 20) if "SELL" in press else (35, 35, 10))
        draw.rounded_rectangle([(cx - 52, r_mid + 12), (cx + 52, r_mid + 38)], radius=4, fill=pr_bg, outline=pr_col, width=1)
        draw.text((cx, r_mid + 25), press, fill=pr_col, font=get_font(12, bold=True), anchor="mm")

        # 6. TREND & REV SCORE [951, 1072]
        c_x1, c_x2 = 951, 1072
        cx = (c_x1 + c_x2) // 2
        trend = item.get("trend", "UP")
        draw_vector_arrow(draw, cx - 30, r_mid - 12, trend)
        tr_col = (0, 255, 136) if trend == "UP" else ((255, 75, 75) if trend == "DOWN" else (255, 220, 0))
        draw.text((cx + 6, r_mid - 12), trend, fill=tr_col, font=f_trend)
        
        rev_sc = item.get("reversal_score", 45)
        r_col = (0, 255, 136) if rev_sc >= 70 else ((255, 220, 0) if rev_sc >= 45 else (255, 75, 75))
        draw.text((cx - 28, r_mid + 24), f"Rev: {rev_sc}", fill=r_col, font=get_font(14, bold=True))

        # 7. CONFIDENCE & ACTION [1075, 1205]
        c_x1, c_x2 = 1075, 1205
        cx = (c_x1 + c_x2) // 2
        conf = item.get("confidence", 75)
        c_col = (0, 255, 136) if conf >= 80 else ((0, 229, 255) if conf >= 65 else (255, 150, 0))
        draw_circular_gauge(draw, cx - 28, r_mid, 24, conf, 100, c_col, text=f"{conf}%", font=get_font(13, bold=True))
        
        act = item.get("action_score", 65)
        a_col = (0, 255, 136) if act >= 80 else ((255, 220, 0) if act >= 60 else (255, 75, 75))
        draw_circular_gauge(draw, cx + 28, r_mid, 24, act, 100, a_col, text=str(act), font=get_font(13, bold=True))
        
        draw.text((cx - 28, r_mid + 34), "Conf", fill=(140, 180, 220), font=get_font(11, bold=False), anchor="mm")
        draw.text((cx + 28, r_mid + 34), "Action", fill=(140, 180, 220), font=get_font(11, bold=False), anchor="mm")

        # 8. TICK MODE (DAILY) [1208, 1410] - DEDICATED COLUMN!
        c_x1, c_x2 = 1208, 1410
        cx = (c_x1 + c_x2) // 2
        
        # Calculate Tick Mode State
        if delta < 0 or b_tick < s_tick:
            tm_title = "EXIT BASKET"
            tm_sub = "TICK BUY < SELL"
            tm_bg = (50, 12, 18)
            tm_col = (255, 70, 70)
        elif 5.0 <= delta_pct <= 10.0:
            tm_title = "L1 BUY READY"
            tm_sub = f"OP (+{delta_pct:.1f}% Δ)"
            tm_bg = (10, 50, 25)
            tm_col = (0, 255, 136)
        elif delta_pct > 10.0:
            tm_title = "STRONG ACCUM"
            tm_sub = f"Inflow (+{delta_pct:.1f}%)"
            tm_bg = (5, 45, 40)
            tm_col = (0, 230, 255)
        elif 0.0 < delta_pct < 5.0:
            tm_title = "L2 AVG VALID"
            tm_sub = f"Disc ≥ 2.5 pts (Δ>0)"
            tm_bg = (45, 40, 8)
            tm_col = (255, 215, 0)
        else:
            tm_title = "MONITOR FLOW"
            tm_sub = "Wait Delta Range"
            tm_bg = (15, 25, 45)
            tm_col = (150, 190, 235)

        draw.rounded_rectangle([(cx - 88, r_mid - 24), (cx + 88, r_mid + 10)], radius=5, fill=tm_bg, outline=tm_col, width=1)
        draw.text((cx, r_mid - 7), tm_title, fill=tm_col, font=f_tick_mode_badge, anchor="mm")
        draw.text((cx, r_mid + 26), tm_sub, fill=(210, 235, 255), font=f_tick_mode_sub, anchor="mm")

        # 9. GRADE & STATUS [1413, 1635]
        c_x1, c_x2 = 1413, 1635
        gr = item.get("grade", "A")
        g_col = (0, 255, 136) if "A" in gr else ((255, 220, 0) if "B" in gr else ((255, 150, 0) if "C" in gr else (255, 75, 75)))
        
        # Grade Box on left
        draw.rounded_rectangle([(c_x1 + 6, r_mid - 26), (c_x1 + 48, r_mid + 26)], radius=6, fill=(10, 25, 50), outline=g_col, width=1)
        draw.text((c_x1 + 27, r_mid), gr, fill=g_col, font=f_grade, anchor="mm")

        # Status on right with concise label
        st = item.get("status", "WAIT")
        clean_subs = {
            "BUY SETUP": "Scalp Buy Valid",
            "SELL SETUP": "Scalp Sell Valid",
            "BUY SCALP": "Entri Buy Aktif",
            "SELL SCALP": "Entri Sell Aktif",
            "STRONG BUY": "Strong Inflow",
            "STRONG SELL": "Strong Outflow",
            "BREAKOUT BUY": "Breakout Valid",
            "BREAKDOWN": "Breakdown Valid",
            "REVERSAL UP": "Pantulan Support",
            "REVERSAL DOWN": "Penolakan Resist",
            "BUY PRESSURE": "Flow Buyer Aktif",
            "SELL PRESSURE": "Flow Seller Aktif",
            "WAIT": "Konsolidasi Netral",
            "NO TRADE": "Disiplin Wait"
        }
        st_sub = clean_subs.get(st, item.get("status_sub", "Monitoring Market"))
        if len(st_sub) > 22:
            st_sub = st_sub[:22]
        st_col = (0, 255, 136) if "BUY" in st else ((255, 75, 75) if "SELL" in st or "DOWN" in st else (255, 220, 0))
        
        draw.text((c_x1 + 58, r_mid - 12), st, fill=st_col, font=f_status, anchor="lm")
        draw.text((c_x1 + 58, r_mid + 16), st_sub, fill=(170, 205, 245), font=f_status_sub, anchor="lm")

        # 10. DAILY TP / SL & R:R [1638, 1902]
        c_x1, c_x2 = 1638, 1902
        tp1 = item.get("tp1", 0.0)
        tp2 = item.get("tp2", 0.0)
        tp3 = item.get("tp3", 0.0)
        sl = item.get("sl", 0.0)
        rr = item.get("rr", "1:1.9")
        
        draw.text((c_x1 + 8, r_mid - 34), "TP1:", fill=(140, 180, 220), font=f_tpsl)
        draw.text((c_x1 + 44, r_mid - 34), f"{tp1:,.{digits}f}", fill=(0, 255, 136), font=f_tpsl_num)
        
        draw.text((c_x1 + 8, r_mid - 12), "TP2:", fill=(140, 180, 220), font=f_tpsl)
        draw.text((c_x1 + 44, r_mid - 12), f"{tp2:,.{digits}f}", fill=(0, 255, 136), font=f_tpsl_num)
        
        draw.text((c_x1 + 8, r_mid + 10), "TP3:", fill=(140, 180, 220), font=f_tpsl)
        draw.text((c_x1 + 44, r_mid + 10), f"{tp3:,.{digits}f}", fill=(0, 255, 136), font=f_tpsl_num)
        
        draw.text((c_x1 + 8, r_mid + 32), "SL:", fill=(140, 180, 220), font=f_tpsl)
        draw.text((c_x1 + 44, r_mid + 32), f"{sl:,.{digits}f}", fill=(255, 75, 75), font=f_tpsl_num)

        # R:R on right
        draw.text((c_x2 - 38, r_mid - 10), "R:R", fill=(140, 180, 220), font=get_font(12, bold=False), anchor="mm")
        draw.text((c_x2 - 38, r_mid + 14), rr, fill=(0, 229, 255), font=f_rr, anchor="mm")

    # 4. BOTTOM PANELS (Y: 808 to 1066) — GABUNG & PERJELAS TRADE DAILY DENGAN FONT BESAR
    Y_BTM = 808
    H_BTM = 258

    # PANEL 1: ZONA SNR & %SNR TARGET (Width: 320 px) [18 to 338]
    draw.rounded_rectangle([(18, Y_BTM), (338, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((28, Y_BTM + 12), "ZONA SNR & TARGET HARGA", fill=(225, 240, 255), font=get_font(16, bold=True))
    
    draw.rounded_rectangle([(28, Y_BTM + 44), (122, Y_BTM + 242)], radius=5, fill=(0, 135, 65))
    draw.text((75, Y_BTM + 60), "BUY ZONE", fill=(255, 255, 255), font=get_font(15, bold=True), anchor="ma")
    draw.text((75, Y_BTM + 90), "0% - 20%\n\nDekat\nSupport\n\nOptimal\nL1 Entry", fill=(220, 255, 235), font=get_font(13, bold=True), anchor="ma", align="center")

    draw.rounded_rectangle([(128, Y_BTM + 44), (228, Y_BTM + 242)], radius=5, fill=(195, 140, 0))
    draw.text((178, Y_BTM + 60), "WAIT ZONE", fill=(255, 255, 255), font=get_font(15, bold=True), anchor="ma")
    draw.text((178, Y_BTM + 90), "21% - 79%\n\nFair\nValue\n\nTunggu\nPullback\nSetup", fill=(255, 250, 220), font=get_font(13, bold=True), anchor="ma", align="center")

    draw.rounded_rectangle([(234, Y_BTM + 44), (328, Y_BTM + 242)], radius=5, fill=(195, 40, 40))
    draw.text((281, Y_BTM + 60), "SELL ZONE", fill=(255, 255, 255), font=get_font(15, bold=True), anchor="ma")
    draw.text((281, Y_BTM + 90), "80% - 100%\n\nDekat\nResist\n\nTake Profit\nReversal", fill=(255, 225, 225), font=get_font(13, bold=True), anchor="ma", align="center")

    # PANEL 2: [TICK MODE] DAILY BASKET PROTOCOL (Width: 630 px) [346 to 976] - CENTERPIECE!
    draw.rounded_rectangle([(346, Y_BTM), (976, Y_BTM + H_BTM)], radius=6, fill=(3, 20, 38), outline=(0, 200, 130), width=2)
    
    # Header
    draw.text((362, Y_BTM + 12), "[TICK MODE] DAILY BASKET PROTOCOL", fill=(255, 220, 0), font=get_font(17, bold=True))
    draw.text((362, Y_BTM + 36), "Magic: 888100 (Isolasi Basket) • Sizing: L1 0.08 / L2 0.12 Lot • Daily Scalp", fill=(0, 229, 255), font=get_font(13, bold=True))

    tm_rules = [
        ("1. ENTRY L1", (0, 255, 136), "OP BUY saat +5.0% <= Delta % <= +10.0% (Inflow di Support)"),
        ("2. AVERAGING L2", (255, 215, 0), "Tambah BUY jika Minus >= 2.5 Poin & TICK BUY > TICK SELL"),
        ("3. EXIT BASKET", (255, 75, 75), "TUTUP SEMUA LAYER jika TICK BUY < TICK SELL (Delta < 0%)"),
        ("4. KUNCI PROFIT", (0, 220, 255), "Kunci BEP saat profit >= +5.0 Pts ($500) | Hard SL: -15.0 Poin")
    ]
    f_rule_t = get_font(14, bold=True)
    f_rule_d = get_font(13, bold=False)
    for idx, (rt, rc, rd) in enumerate(tm_rules):
        ry = Y_BTM + 64 + idx * 46
        draw.rounded_rectangle([(362, ry), (496, ry + 24)], radius=4, fill=(10, 35, 55), outline=rc, width=1)
        draw.text((429, ry + 12), rt, fill=rc, font=f_rule_t, anchor="mm")
        draw.text((506, ry + 12), rd, fill=(235, 245, 255), font=f_rule_d, anchor="lm")

    # PANEL 3: ORDER FLOW DELTA & PRESSURE (Width: 440 px) [984 to 1424]
    draw.rounded_rectangle([(984, Y_BTM), (1424, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((998, Y_BTM + 12), "ORDER FLOW DELTA & PRESSURE", fill=(225, 240, 255), font=get_font(16, bold=True))
    draw.text((998, Y_BTM + 36), "Threshold Volume Ratio & Validasi Aliran Transaksi", fill=(140, 185, 235), font=get_font(13, bold=False))

    flow_thresholds = [
        ("> 65% / Δ > +10%", "STRONG BUY", (0, 255, 136), "Inflow institusi masif, buyer mutlak"),
        ("55% - 65% / Δ > 0%", "BUY PRESSURE", (0, 220, 110), "Kondisi ideal eksekusi L1 & L2"),
        ("45% - 55% / Δ ≈ 0", "BALANCED", (255, 220, 0), "Volume netral / pasar konsolidasi"),
        ("< 45% / Δ < 0%", "SELL DOMINANCE", (255, 75, 75), "Seller dominan → TRIGGER CLOSE ALL")
    ]
    for idx, (ft_rng, ft_lbl, ft_col, ft_note) in enumerate(flow_thresholds):
        fy = Y_BTM + 66 + idx * 44
        draw.text((998, fy), ft_rng, fill=(185, 220, 255), font=get_font(14, bold=True))
        draw.text((1165, fy), f"=  {ft_lbl}", fill=ft_col, font=get_font(14, bold=True))
        draw.text((998, fy + 20), f"    {ft_note}", fill=(160, 200, 240), font=get_font(12, bold=False))

    # PANEL 4: SIGNAL GRADE & FILTER HARIAN (Width: 468 px) [1432 to 1900]
    draw.rounded_rectangle([(1432, Y_BTM), (1900, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((1446, Y_BTM + 12), "SIGNAL GRADE & FILTER HARIAN", fill=(225, 240, 255), font=get_font(16, bold=True))
    draw.text((1446, Y_BTM + 36), "Hierarki Kelayakan Eksekusi & Batas Disiplin", fill=(140, 185, 235), font=get_font(13, bold=False))

    grades_info = [
        ("A+", "STRONG ENTRY", (0, 255, 136), "Conf >= 90 | Action >= 85 | Prioritas Utama Daily"),
        ("A",  "ENTRY CONFIRMED", (0, 220, 110), "Conf >= 85 | Action >= 75 | Flow & SNR Valid"),
        ("B",  "SETUP / WATCH", (255, 220, 0), "Conf >= 75 | Action >= 65 | Tunggu Rejection Candle"),
        ("C/D", "WAIT / NO TRADE", (255, 75, 75), "Di bawah threshold | DISIPLIN DILARANG OP")
    ]
    for idx, (glbl, gtitle, gcol, gdesc) in enumerate(grades_info):
        gy = Y_BTM + 66 + idx * 44
        draw.rounded_rectangle([(1446, gy - 2), (1484, gy + 22)], radius=4, fill=gcol)
        draw.text((1465, gy + 10), glbl, fill=(0, 0, 0) if "A" in glbl or "B" in glbl else (255, 255, 255), font=get_font(14, bold=True), anchor="mm")
        draw.text((1494, gy), f"→  {gtitle}", fill=gcol, font=get_font(14, bold=True))
        draw.text((1494, gy + 20), gdesc, fill=(170, 205, 245), font=get_font(12, bold=False))

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path, "PNG", optimize=True)

    return img

def generate_sr_card_bytes(data_list: list) -> bytes:
    img = render_bloomberg_dashboard_card(data_list)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
