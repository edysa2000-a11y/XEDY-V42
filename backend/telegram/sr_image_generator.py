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
    draw.rounded_rectangle([(8, 8), (W - 8, H - 8)], radius=10, outline=(0, 110, 230), width=2)

    # 2X TYPOGRAPHY
    f_date = get_font(16, bold=False)
    f_time = get_font(28, bold=True)
    f_live = get_font(15, bold=True)
    f_main_title = get_font(28, bold=True)
    f_main_sub = get_font(16, bold=True)
    f_mode_title = get_font(16, bold=True)
    f_mode_sub = get_font(13, bold=False)
    f_news_title = get_font(14, bold=True)
    f_news_sub = get_font(12, bold=False)
    f_news_val = get_font(14, bold=True)

    f_hdr = get_font(15, bold=True)
    f_hdr_sub = get_font(12, bold=False)
    f_pair = get_font(22, bold=True)
    f_sub = get_font(13, bold=False)
    f_price = get_font(26, bold=True)
    f_chg = get_font(16, bold=True)
    f_chg_pct = get_font(14, bold=False)
    f_lvl_num = get_font(16, bold=True)
    f_snr_tick = get_font(13, bold=True)
    f_zone_box = get_font(12, bold=True)
    f_badge = get_font(14, bold=True)
    f_vol_num = get_font(15, bold=True)
    f_donut = get_font(13, bold=True)
    f_delta = get_font(18, bold=True)
    f_delta_sub = get_font(13, bold=False)
    f_trend = get_font(16, bold=True)
    f_trend_sub = get_font(11, bold=False)
    f_gauge_val = get_font(15, bold=True)
    f_grade = get_font(30, bold=True)
    f_status = get_font(18, bold=True)
    f_status_sub = get_font(12, bold=False)
    f_tpsl = get_font(13, bold=False)
    f_tpsl_num = get_font(14, bold=True)
    f_rr = get_font(18, bold=True)

    now_wib = datetime.now(WIB)
    date_str = now_wib.strftime("%a, %d %b %Y")
    time_str = now_wib.strftime("%H:%M:%S")

    # 1. TOP HEADER (Y: 14 to 86)
    # Left Box: Date / Time / LIVE
    draw.rounded_rectangle([(18, 14), (220, 86)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((28, 18), date_str, fill=(145, 185, 230), font=f_date)
    draw.text((28, 38), time_str, fill=(255, 255, 255), font=f_time)
    draw.rounded_rectangle([(148, 42), (210, 72)], radius=12, fill=(0, 60, 30), outline=(0, 220, 110), width=1)
    draw.text((182, 57), "LIVE", fill=(0, 255, 136), font=f_live, anchor="mm")
    draw.ellipse([(156, 54), (164, 62)], fill=(0, 255, 136))

    # Center Title & Subtitle
    draw.text((950, 32), "SNR + TICK FLOW + CONFIDENCE + ACTION SCORE + SIGNAL GRADE", fill=(255, 220, 0), font=f_main_title, anchor="mm")
    draw.text((950, 66), "LOCATION → PRESSURE → TREND → PRICE ACTION → CONFIDENCE → ACTION SCORE → STATUS", fill=(0, 229, 255), font=f_main_sub, anchor="mm")

    # Right Box 1: A+ HIGH WIN-RATE MODE Toggle
    draw.rounded_rectangle([(1430, 14), (1690, 86)], radius=6, fill=(3, 25, 25), outline=(0, 180, 90), width=1)
    draw.text((1444, 24), "A+ HIGH WIN-RATE MODE", fill=(0, 255, 136), font=f_mode_title)
    draw.text((1444, 52), "Entry hanya A+ dan A", fill=(130, 215, 255), font=f_mode_sub)
    draw.rounded_rectangle([(1630, 34), (1678, 64)], radius=12, fill=(0, 200, 100))
    draw.ellipse([(1654, 36), (1676, 62)], fill=(255, 255, 255))

    # Right Box 2: NEWS FILTER
    draw.rounded_rectangle([(1700, 14), (1902, 86)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((1712, 22), "NEWS FILTER", fill=(200, 225, 250), font=f_news_title)
    draw.rounded_rectangle([(1828, 20), (1888, 44)], radius=9, fill=(0, 200, 100))
    draw.text((1858, 32), "LOW", fill=(0, 0, 0), font=get_font(13, bold=True), anchor="mm")
    draw.text((1712, 46), "Next High Impact", fill=(140, 175, 215), font=f_news_sub)
    draw.text((1712, 64), "USD: NFP 5h 35m", fill=(255, 255, 255), font=f_news_val)

    # Header Divider Line
    draw.line([(18, 92), (W - 18, 92)], fill=(18, 60, 125), width=2)

    # 2. MAIN TABLE HEADER (Y: 96 to 142)
    COLS = [
        ("PAIR", "", 18, 150),
        ("LIVE\nPRICE", "", 152, 265),
        ("CHANGE\n(%)", "", 267, 368),
        ("SNR & LEVELS", "(S | REV-UP | %SNR | REV-DOWN | R)", 370, 765),
        ("TICK FLOW", "(BUY / SELL)", 767, 868),
        ("VOLUME RATIO", "(Buy % / Sell %)", 870, 968),
        ("DELTA", "(B - S)", 970, 1052),
        ("PRESSURE", "", 1054, 1156),
        ("TREND", "(MA + Struct)", 1158, 1258),
        ("REV\nSCORE", "(0 - 100)", 1260, 1338),
        ("CONFIDENCE", "(0 - 100%)", 1340, 1438),
        ("ACTION\nSCORE", "(0 - 100)", 1440, 1538),
        ("GRADE", "", 1540, 1610),
        ("FINAL STATUS", "(Entry Signal)", 1612, 1750),
        ("TP / SL", "(TP1-3 | SL)", 1752, 1852),
        ("R:R", "", 1854, 1910),
    ]

    HDR_TEXT_COL = (210, 235, 255)
    for title, sub, x1, x2 in COLS:
        cx = (x1 + x2) // 2
        draw.rounded_rectangle([(x1, 96), (x2, 142)], radius=4, fill=(3, 16, 38), outline=(12, 45, 95), width=1)
        if sub and "\n" not in title:
            draw.text((cx, 108), title, fill=HDR_TEXT_COL, font=f_hdr, anchor="mm")
            draw.text((cx, 128), sub, fill=(130, 180, 230), font=f_hdr_sub, anchor="mm")
        elif "\n" in title:
            lines = title.split("\n")
            draw.text((cx, 108), lines[0], fill=HDR_TEXT_COL, font=f_hdr, anchor="mm")
            draw.text((cx, 127), lines[1], fill=HDR_TEXT_COL, font=f_hdr, anchor="mm")
        else:
            draw.text((cx, 119), title, fill=HDR_TEXT_COL, font=f_hdr, anchor="mm", align="center")

    # 3. FOUR INSTRUMENT ROWS (Y: 148 to 804)
    ROW_H = 162
    Y_START = 148

    for i, item in enumerate(data_list):
        r_top = Y_START + i * ROW_H
        r_btm = r_top + ROW_H - 6
        r_mid = (r_top + r_btm) // 2
        
        draw.rounded_rectangle([(18, r_top), (W - 18, r_btm)], radius=6, fill=(3, 14, 34), outline=(10, 40, 85), width=1)

        # 1. PAIR
        c_x1, c_x2 = 18, 150
        draw_flag_icon(draw, c_x1 + 22, r_mid - 2, 18, item.get("icon_type", "gold"))
        p_name = item["name"]
        p_col = (255, 214, 0) if p_name == "GOLD" else (255, 255, 255)
        draw.text((c_x1 + 52, r_mid - 20), p_name, fill=p_col, font=f_pair)
        draw.text((c_x1 + 52, r_mid + 8), item["subtitle"], fill=(150, 195, 250), font=f_sub)

        # 2. LIVE PRICE
        c_x1, c_x2 = 152, 265
        p_val = item["price"]
        digits = item.get("digits", 2)
        cx = (c_x1 + c_x2) // 2
        draw.text((cx, r_mid), f"{p_val:,.{digits}f}", fill=(255, 255, 255), font=f_price, anchor="mm")

        # 3. CHANGE %
        c_x1, c_x2 = 267, 368
        cx = (c_x1 + c_x2) // 2
        chg = item.get("change_val", item.get("change", 0.0))
        chg_pct = item.get("change_pct", 0.0)
        chg_sgn = "+" if chg >= 0 else ""
        chg_col = (0, 255, 136) if chg >= 0 else (255, 75, 75)
        draw.text((cx, r_mid - 14), f"{chg_sgn}{chg:.{digits}f}", fill=chg_col, font=f_chg, anchor="mm")
        draw.text((cx, r_mid + 12), f"({chg_sgn}{chg_pct:.2f}%)", fill=chg_col, font=f_chg_pct, anchor="mm")

        # 4. SNR & LEVELS
        c_x1, c_x2 = 370, 765
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

        # Support & Resistance Price Labels (Row 1: S on left, R on right)
        draw.text((cx_supp, r_mid - 44), f"S: {supp:,.{digits}f}", fill=(0, 255, 136), font=f_lvl_num, anchor="la")
        draw.text((cx_res, r_mid - 44), f"R: {res:,.{digits}f}", fill=(255, 75, 75), font=f_lvl_num, anchor="ra")
        
        # Intermediate Reversal Zones (Row 2: RevUp at 20%, RevDn at 80%)
        draw.text((cx_rup, r_mid - 24), f"RevUp: {rev_up:,.{digits}f}", fill=(130, 240, 180), font=get_font(12, bold=False), anchor="ma")
        draw.text((cx_rdn, r_mid - 24), f"RevDn: {rev_dn:,.{digits}f}", fill=(255, 150, 150), font=get_font(12, bold=False), anchor="ma")

        # Color Gradient Bar
        draw_gradient_bar(draw, BAR_X1, r_mid - 6, BAR_X2, r_mid + 4)

        # Needle position based on %SNR
        pct_snr = item["pct_snr"]
        clamped_pct = max(0.0, min(100.0, pct_snr))
        needle_x = BAR_X1 + int(BAR_W * (clamped_pct / 100.0))

        # Vertical Needle line & pointer
        draw.line([(needle_x, r_mid - 16), (needle_x, r_mid + 14)], fill=(255, 255, 255), width=3)
        draw.ellipse([(needle_x - 5, r_mid - 6), (needle_x + 5, r_mid + 4)], fill=(255, 255, 255))
        
        # Badge %SNR
        badge_w = 64
        bx1 = max(BAR_X1, min(BAR_X2 - badge_w, needle_x - badge_w // 2))
        draw.rounded_rectangle([(bx1, r_mid + 16), (bx1 + badge_w, r_mid + 38)], radius=4, fill=(10, 45, 95), outline=(0, 210, 255), width=1)
        draw.text((bx1 + badge_w // 2, r_mid + 27), f"{pct_snr:.1f}%", fill=(0, 255, 255), font=f_snr_tick, anchor="mm")

        # Zone pill labels on the bottom
        draw.text((cx_supp + 25, r_mid + 48), "BUY ZONE", fill=(0, 255, 136), font=f_zone_box, anchor="mm")
        draw.text((cx_mid, r_mid + 48), "MID / WAIT", fill=(255, 220, 0), font=f_zone_box, anchor="mm")
        draw.text((cx_res - 25, r_mid + 48), "SELL ZONE", fill=(255, 75, 75), font=f_zone_box, anchor="mm")

        # 5. TICK FLOW
        c_x1, c_x2 = 767, 868
        cx = (c_x1 + c_x2) // 2
        b_tick = item.get("buy_tick", 1200)
        s_tick = item.get("sell_tick", 1000)
        draw.text((cx, r_mid - 18), f"B: {b_tick:,}", fill=(0, 255, 136), font=f_vol_num, anchor="mm")
        draw.text((cx, r_mid + 14), f"S: {s_tick:,}", fill=(255, 75, 75), font=f_vol_num, anchor="mm")

        # 6. VOLUME RATIO DONUT
        c_x1, c_x2 = 870, 968
        cx = (c_x1 + c_x2) // 2
        buy_pct = item.get("buy_pct", 55)
        draw_donut_ratio(draw, cx, r_mid, 28, buy_pct, f_donut)

        # 7. DELTA
        c_x1, c_x2 = 970, 1052
        cx = (c_x1 + c_x2) // 2
        delta = item.get("delta", 200)
        d_sgn = "+" if delta >= 0 else ""
        d_col = (0, 255, 136) if delta >= 0 else (255, 75, 75)
        draw.text((cx, r_mid - 12), f"{d_sgn}{delta:,}", fill=d_col, font=f_delta, anchor="mm")
        draw.text((cx, r_mid + 14), "Delta", fill=(140, 180, 220), font=f_delta_sub, anchor="mm")

        # 8. PRESSURE
        c_x1, c_x2 = 1054, 1156
        cx = (c_x1 + c_x2) // 2
        press = item.get("pressure", "BALANCED")
        pr_col = (0, 255, 136) if "BUY" in press else ((255, 75, 75) if "SELL" in press else (255, 220, 0))
        pr_bg = (10, 45, 30) if "BUY" in press else ((45, 15, 20) if "SELL" in press else (35, 35, 10))
        draw.rounded_rectangle([(cx - 46, r_mid - 20), (cx + 46, r_mid + 20)], radius=4, fill=pr_bg, outline=pr_col, width=1)
        p_lines = press.split()
        if len(p_lines) == 1:
            draw.text((cx, r_mid), press, fill=pr_col, font=f_badge, anchor="mm")
        else:
            draw.text((cx, r_mid - 8), p_lines[0], fill=pr_col, font=f_badge, anchor="mm")
            draw.text((cx, r_mid + 10), " ".join(p_lines[1:]), fill=pr_col, font=get_font(12, bold=True), anchor="mm")

        # 9. TREND
        c_x1, c_x2 = 1158, 1258
        cx = (c_x1 + c_x2) // 2
        trend = item.get("trend", "UP")
        draw_vector_arrow(draw, cx - 22, r_mid, trend)
        tr_col = (0, 255, 136) if trend == "UP" else ((255, 75, 75) if trend == "DOWN" else (255, 220, 0))
        draw.text((cx + 8, r_mid - 8), trend, fill=tr_col, font=f_trend)
        draw.text((cx + 8, r_mid + 12), "Structure", fill=(140, 180, 220), font=f_trend_sub)

        # 10. REVERSAL SCORE
        c_x1, c_x2 = 1260, 1344
        cx = (c_x1 + c_x2) // 2
        rev_sc = item.get("reversal_score", 45)
        r_col = (0, 255, 136) if rev_sc >= 70 else ((255, 220, 0) if rev_sc >= 45 else (255, 75, 75))
        draw_circular_gauge(draw, cx, r_mid, 26, rev_sc, 100, r_col, text=str(rev_sc), font=f_gauge_val)

        # 11. CONFIDENCE
        c_x1, c_x2 = 1346, 1444
        cx = (c_x1 + c_x2) // 2
        conf = item.get("confidence", 75)
        c_col = (0, 255, 136) if conf >= 80 else ((0, 229, 255) if conf >= 65 else (255, 150, 0))
        draw_circular_gauge(draw, cx, r_mid, 26, conf, 100, c_col, text=f"{conf}%", font=f_gauge_val)

        # 12. ACTION SCORE
        c_x1, c_x2 = 1446, 1546
        cx = (c_x1 + c_x2) // 2
        act = item.get("action_score", 65)
        a_col = (0, 255, 136) if act >= 80 else ((255, 220, 0) if act >= 60 else (255, 75, 75))
        draw_circular_gauge(draw, cx, r_mid, 26, act, 100, a_col, text=str(act), font=f_gauge_val)

        # 13. GRADE
        c_x1, c_x2 = 1548, 1618
        cx = (c_x1 + c_x2) // 2
        gr = item.get("grade", "A")
        g_col = (0, 255, 136) if "A" in gr else ((255, 220, 0) if "B" in gr else ((255, 150, 0) if "C" in gr else (255, 75, 75)))
        draw.text((cx, r_mid), gr, fill=g_col, font=f_grade, anchor="mm")

        # 14. FINAL STATUS
        c_x1, c_x2 = 1620, 1768
        cx = (c_x1 + c_x2) // 2
        st = item.get("status", "WAIT")
        st_sub = item.get("status_sub", "Monitoring...")
        st_col = (0, 255, 136) if "BUY" in st else ((255, 75, 75) if "SELL" in st or "DOWN" in st else (255, 220, 0))
        draw.rounded_rectangle([(cx - 68, r_mid - 24), (cx + 68, r_mid + 10)], radius=4, fill=(15, 30, 60), outline=st_col, width=1)
        draw.text((cx, r_mid - 7), st, fill=st_col, font=f_status, anchor="mm")
        draw.text((cx, r_mid + 24), st_sub, fill=(180, 215, 255), font=f_status_sub, anchor="mm")

        # 15. TP / SL
        c_x1, c_x2 = 1770, 1865
        tp1 = item.get("tp1", 0.0)
        tp2 = item.get("tp2", 0.0)
        tp3 = item.get("tp3", 0.0)
        sl = item.get("sl", 0.0)
        draw.text((c_x1 + 6, r_mid - 32), "TP1:", fill=(140, 180, 220), font=f_tpsl)
        draw.text((c_x1 + 38, r_mid - 32), f"{tp1:,.{digits}f}", fill=(0, 255, 136), font=f_tpsl_num)
        draw.text((c_x1 + 6, r_mid - 12), "TP2:", fill=(140, 180, 220), font=f_tpsl)
        draw.text((c_x1 + 38, r_mid - 12), f"{tp2:,.{digits}f}", fill=(0, 255, 136), font=f_tpsl_num)
        draw.text((c_x1 + 6, r_mid + 8), "TP3:", fill=(140, 180, 220), font=f_tpsl)
        draw.text((c_x1 + 38, r_mid + 8), f"{tp3:,.{digits}f}", fill=(0, 255, 136), font=f_tpsl_num)
        draw.text((c_x1 + 6, r_mid + 28), "SL:", fill=(140, 180, 220), font=f_tpsl)
        draw.text((c_x1 + 38, r_mid + 28), f"{sl:,.{digits}f}", fill=(255, 75, 75), font=f_tpsl_num)

        # 16. R:R
        c_x1, c_x2 = 1867, 1910
        cx = (c_x1 + c_x2) // 2
        rr = item.get("rr", "1:1.8")
        draw.text((cx, r_mid), rr, fill=(0, 229, 255), font=f_rr, anchor="mm")

    # 4. BOTTOM PANELS (Y: 812 to 1066)
    Y_BTM = 812
    H_BTM = 254

    # Panel 1: SNR ZONES [w: 325]
    draw.rounded_rectangle([(18, Y_BTM), (345, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((28, Y_BTM + 10), "ZONA SNR & INTERPRETASI %SNR", fill=(215, 235, 255), font=get_font(15, bold=True))
    draw.rounded_rectangle([(28, Y_BTM + 40), (122, Y_BTM + 236)], radius=4, fill=(0, 140, 65))
    draw.text((75, Y_BTM + 70), "BUY ZONE\n0% - 20%\nDekat\nSupport", fill=(255, 255, 255), font=get_font(14, bold=True), anchor="ma", align="center")
    draw.rounded_rectangle([(128, Y_BTM + 40), (222, Y_BTM + 236)], radius=4, fill=(210, 150, 0))
    draw.text((175, Y_BTM + 70), "WAIT ZONE\n21% - 79%\nTengah / Fair\nValue", fill=(255, 255, 255), font=get_font(14, bold=True), anchor="ma", align="center")
    draw.rounded_rectangle([(228, Y_BTM + 40), (322, Y_BTM + 236)], radius=4, fill=(210, 45, 45))
    draw.text((275, Y_BTM + 70), "SELL ZONE\n80% - 100%\nDekat\nResist", fill=(255, 255, 255), font=get_font(14, bold=True), anchor="ma", align="center")

    # Panel 2: THRESHOLD PRESSURE (TICK VOLUME) [w: 345]
    draw.rounded_rectangle([(355, Y_BTM), (700, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((368, Y_BTM + 10), "THRESHOLD PRESSURE (TICK VOL)", fill=(215, 235, 255), font=get_font(15, bold=True))
    p_info = [
        ("> 70%", "STRONG BUY", (0, 255, 136)),
        ("65% - 70%", "BUY PRESSURE", (0, 220, 110)),
        ("55% - 65%", "BUY MODERATE", (120, 240, 170)),
        ("45% - 55%", "BALANCED", (255, 220, 0)),
        ("35% - 45%", "SELL MODERATE", (255, 140, 140)),
        ("30% - 35%", "SELL PRESSURE", (255, 90, 90)),
        ("< 30%", "STRONG SELL", (255, 50, 50))
    ]
    f_p = get_font(14, bold=True)
    for idx, (p_rng, p_lbl, p_c) in enumerate(p_info):
        py = Y_BTM + 42 + idx * 28
        draw.text((375, py), p_rng, fill=(180, 215, 250), font=f_p)
        draw.text((495, py), f"=  {p_lbl}", fill=p_c, font=f_p)

    # Panel 3: CONFIDENCE THRESHOLD (0 - 100) [w: 335]
    draw.rounded_rectangle([(710, Y_BTM), (1045, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((724, Y_BTM + 10), "CONFIDENCE THRESHOLD (0 - 100)", fill=(215, 235, 255), font=get_font(15, bold=True))
    c_info = [
        ("85 - 100", "VERY HIGH", (0, 255, 136)),
        ("70 - 84", "HIGH", (0, 229, 255)),
        ("55 - 69", "MODERATE", (255, 220, 0)),
        ("40 - 54", "LOW", (255, 150, 0)),
        ("0 - 39", "WEAK", (255, 75, 75))
    ]
    for idx, (c_rng, c_lbl, c_c) in enumerate(c_info):
        cy_pos = Y_BTM + 48 + idx * 36
        draw.text((730, cy_pos), c_rng, fill=(180, 215, 250), font=f_p)
        draw.text((845, cy_pos), f"=  {c_lbl}", fill=c_c, font=f_p)

    # Panel 4: ACTION SCORE & SIGNAL GRADE [w: 375]
    draw.rounded_rectangle([(1055, Y_BTM), (1430, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((1068, Y_BTM + 10), "ACTION SCORE & SIGNAL GRADE", fill=(215, 235, 255), font=get_font(15, bold=True))
    g_info = [
        ("A+", "Conf >= 90  |  Action >= 85", "STRONG ENTRY", (0, 255, 136)),
        ("A",  "Conf >= 85  |  Action >= 75", "ENTRY", (0, 220, 110)),
        ("B",  "Conf >= 75  |  Action >= 65", "SETUP / WATCH", (255, 220, 0)),
        ("C",  "Conf >= 65  |  Action >= 50", "WAIT", (255, 140, 0)),
        ("D",  "Below threshold", "NO TRADE", (255, 75, 75))
    ]
    for idx, (gr_lbl, gr_req, gr_st, gr_c) in enumerate(g_info):
        gy = Y_BTM + 42 + idx * 40
        draw.rounded_rectangle([(1068, gy - 2), (1102, gy + 24)], radius=4, fill=gr_c)
        draw.text((1085, gy + 11), gr_lbl, fill=(0, 0, 0) if gr_lbl in ["A+", "B"] else (255, 255, 255), font=get_font(15, bold=True), anchor="mm")
        draw.text((1115, gy), gr_req, fill=(180, 215, 250), font=get_font(14, bold=False))
        draw.text((1115, gy + 18), f"→ {gr_st}", fill=gr_c, font=get_font(14, bold=True))

    # Panel 5: LEGEND FINAL STATUS [w: 470]
    draw.rounded_rectangle([(1440, Y_BTM), (1902, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((1452, Y_BTM + 10), "LEGEND FINAL STATUS (RULE STATUS)", fill=(215, 235, 255), font=get_font(15, bold=True))
    
    st_rules = [
        ("STRONG BUY / SELL", (0, 255, 136), "SNR Ekstrem (<=15% / >=85%) + Vol >=65% + Conf >=90"),
        ("BREAKOUT / BREAKDOWN", (0, 229, 255), "Harga menembus level S/R + Vol >=60% searah tren"),
        ("REVERSAL UP / DOWN", (255, 160, 0), "Zona Pantul (<=20% / >=80%) + Rev Score >=60 valid"),
        ("BUY / SELL SETUP", (255, 220, 0), "Mendekati zona SNR + dominasi volume terkonfirmasi"),
        ("BUY / SELL PRESSURE", (255, 120, 120), "Arus volume mengalir searah (>55%), cari momentum"),
        ("WAIT / NO TRADE", (160, 190, 225), "Konsolidasi di tengah / belum ada setup yang valid")
    ]
    f_st_t = get_font(14, bold=True)
    f_st_d = get_font(13, bold=False)
    for idx, (st_name, st_col, st_desc) in enumerate(st_rules):
        sy = Y_BTM + 38 + idx * 34
        draw.text((1452, sy), f"• {st_name}", fill=st_col, font=f_st_t)
        draw.text((1452, sy + 16), f"   {st_desc}", fill=(180, 215, 250), font=f_st_d)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path, "PNG", optimize=True)

    return img

def generate_sr_card_bytes(data_list: list) -> bytes:
    img = render_bloomberg_dashboard_card(data_list)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
