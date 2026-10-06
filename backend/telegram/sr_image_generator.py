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
    W, H = 1600, 900
    img = Image.new("RGBA", (W, H), (2, 10, 24, 255))
    draw = ImageDraw.Draw(img)

    # Grid background
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill=(5, 18, 42), width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=(5, 18, 42), width=1)

    # Outer border
    draw.rounded_rectangle([(8, 8), (W - 8, H - 8)], radius=8, outline=(0, 110, 230), width=2)

    # Typography
    f_date = get_font(11, bold=False)
    f_time = get_font(22, bold=True)
    f_live = get_font(11, bold=True)
    f_main_title = get_font(21, bold=True)
    f_main_sub = get_font(12, bold=True)
    f_mode_title = get_font(12, bold=True)
    f_mode_sub = get_font(10, bold=False)
    f_news_title = get_font(10, bold=True)
    f_news_sub = get_font(9, bold=False)
    f_news_val = get_font(10, bold=True)

    f_hdr = get_font(11, bold=True)
    f_hdr_sub = get_font(9, bold=False)
    f_pair = get_font(15, bold=True)
    f_sub = get_font(10, bold=False)
    f_price = get_font(20, bold=True)
    f_chg = get_font(12, bold=True)
    f_chg_pct = get_font(11, bold=False)
    f_lvl_num = get_font(11, bold=True)
    f_snr_tick = get_font(9, bold=True)
    f_zone_box = get_font(8, bold=True)
    f_badge = get_font(10, bold=True)
    f_vol_num = get_font(11, bold=True)
    f_donut = get_font(9, bold=True)
    f_delta = get_font(12, bold=True)
    f_delta_sub = get_font(10, bold=False)
    f_trend = get_font(11, bold=True)
    f_trend_sub = get_font(8, bold=False)
    f_gauge_val = get_font(11, bold=True)
    f_grade = get_font(22, bold=True)
    f_status = get_font(13, bold=True)
    f_status_sub = get_font(9, bold=False)
    f_tpsl = get_font(10, bold=False)
    f_tpsl_num = get_font(10, bold=True)
    f_rr = get_font(13, bold=True)

    now_wib = datetime.now(WIB)
    date_str = now_wib.strftime("%a, %d %b %Y")
    time_str = now_wib.strftime("%H:%M:%S")

    # 1. TOP HEADER (Y: 12 to 78)
    # Left Box: Date / Time / LIVE
    draw.rounded_rectangle([(16, 12), (180, 78)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((26, 16), date_str, fill=(145, 185, 230), font=f_date)
    draw.text((26, 32), time_str, fill=(255, 255, 255), font=f_time)
    draw.rounded_rectangle([(120, 36), (172, 60)], radius=12, fill=(0, 60, 30), outline=(0, 220, 110), width=1)
    draw.text((146, 48), "LIVE", fill=(0, 255, 136), font=f_live, anchor="mm")
    draw.ellipse([(126, 45), (132, 51)], fill=(0, 255, 136))

    # Center Title & Subtitle
    draw.text((800, 28), "SNR + TICK FLOW + CONFIDENCE + ACTION SCORE + SIGNAL GRADE", fill=(255, 220, 0), font=f_main_title, anchor="mm")
    draw.text((800, 56), "LOCATION → PRESSURE → TREND → PRICE ACTION → CONFIDENCE → ACTION SCORE → STATUS", fill=(0, 229, 255), font=f_main_sub, anchor="mm")

    # Right Box 1: A+ HIGH WIN-RATE MODE Toggle
    draw.rounded_rectangle([(1190, 12), (1420, 78)], radius=6, fill=(3, 25, 25), outline=(0, 180, 90), width=1)
    draw.text((1202, 20), "A+ HIGH WIN-RATE MODE", fill=(0, 255, 136), font=f_mode_title)
    draw.text((1202, 42), "Entry hanya A+ dan A", fill=(130, 215, 255), font=f_mode_sub)
    draw.rounded_rectangle([(1365, 30), (1408, 54)], radius=12, fill=(0, 200, 100))
    draw.ellipse([(1388, 32), (1406, 52)], fill=(255, 255, 255))

    # Right Box 2: NEWS FILTER
    draw.rounded_rectangle([(1428, 12), (1584, 78)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((1438, 18), "NEWS FILTER", fill=(200, 225, 250), font=f_news_title)
    draw.rounded_rectangle([(1530, 16), (1574, 34)], radius=9, fill=(0, 200, 100))
    draw.text((1552, 25), "LOW", fill=(0, 0, 0), font=get_font(10, bold=True), anchor="mm")
    draw.text((1438, 38), "Next High Impact", fill=(140, 175, 215), font=f_news_sub)
    draw.text((1438, 52), "USD: NFP 5h 35m", fill=(255, 255, 255), font=f_news_val)

    # Header Divider Line
    draw.line([(14, 84), (W - 14, 84)], fill=(18, 60, 125), width=2)

    # 2. MAIN TABLE HEADER (Y: 88 to 128)
    COLS = [
        ("PAIR", "", 16, 124),
        ("LIVE\nPRICE", "", 126, 218),
        ("CHANGE\n(%)", "", 220, 302),
        ("SNR & LEVELS", "(S | REV-UP | %SNR | REV-DOWN | R)", 304, 636),
        ("TICK FLOW", "(BUY / SELL)", 638, 722),
        ("VOLUME RATIO", "(Buy % / Sell %)", 724, 804),
        ("DELTA", "(B - S)", 806, 874),
        ("PRESSURE", "", 876, 960),
        ("TREND", "(MA + Structure)", 962, 1044),
        ("REVERSAL\nSCORE", "", 1046, 1114),
        ("CONFIDENCE", "(0 - 100%)", 1116, 1198),
        ("ACTION\nSCORE", "(0 - 100)", 1200, 1282),
        ("GRADE", "", 1284, 1340),
        ("FINAL STATUS", "(Entry Signal)", 1342, 1464),
        ("TP / SL SUGGESTION", "(TP1 / TP2 / TP3 | SL)", 1466, 1546),
        ("R:R", "", 1548, 1584),
    ]

    HDR_TEXT_COL = (210, 235, 255)
    for title, sub, x1, x2 in COLS:
        cx = (x1 + x2) // 2
        draw.rounded_rectangle([(x1, 88), (x2, 126)], radius=4, fill=(3, 16, 38), outline=(12, 45, 95), width=1)
        if sub:
            draw.text((cx, 98), title, fill=HDR_TEXT_COL, font=f_hdr, anchor="mm")
            draw.text((cx, 114), sub, fill=(130, 180, 230), font=f_hdr_sub, anchor="mm")
        else:
            draw.text((cx, 107), title, fill=HDR_TEXT_COL, font=f_hdr, anchor="mm", align="center")

    # 3. FOUR INSTRUMENT ROWS (Y: 132 to 684)
    ROW_H = 138
    Y_START = 132

    for i, item in enumerate(data_list):
        r_top = Y_START + i * ROW_H
        r_btm = r_top + ROW_H - 4
        r_mid = (r_top + r_btm) // 2
        
        draw.rounded_rectangle([(14, r_top), (W - 14, r_btm)], radius=6, fill=(3, 14, 34), outline=(10, 40, 85), width=1)

        # 1. PAIR
        c_x1, c_x2 = 16, 124
        draw_flag_icon(draw, c_x1 + 18, r_mid - 2, 16, item.get("icon_type", "gold"))
        p_name = item["name"]
        p_col = (255, 214, 0) if p_name == "GOLD" else (255, 255, 255)
        draw.text((c_x1 + 42, r_mid - 16), p_name, fill=p_col, font=f_pair)
        draw.text((c_x1 + 42, r_mid + 6), item["subtitle"], fill=(150, 195, 250), font=f_sub)

        # 2. LIVE PRICE
        c_x1, c_x2 = 126, 218
        p_val = item["price"]
        digits = item.get("digits", 2)
        cx = (c_x1 + c_x2) // 2
        draw.text((cx, r_mid - 2), f"{p_val:,.{digits}f}", fill=(255, 255, 255), font=f_price, anchor="mm")

        # 3. CHANGE %
        c_x1, c_x2 = 220, 302
        cx = (c_x1 + c_x2) // 2
        chg = item.get("change_val", item.get("change", 0.0))
        chg_pct = item.get("change_pct", 0.0)
        chg_sgn = "+" if chg >= 0 else ""
        chg_col = (0, 255, 136) if chg >= 0 else (255, 75, 75)
        draw.text((cx, r_mid - 10), f"{chg_sgn}{chg:.{digits}f}", fill=chg_col, font=f_chg, anchor="mm")
        draw.text((cx, r_mid + 10), f"({chg_sgn}{chg_pct:.2f}%)", fill=chg_col, font=f_chg_pct, anchor="mm")

        # 4. SNR & LEVELS
        c_x1, c_x2 = 304, 636
        BAR_X1 = c_x1 + 12
        BAR_X2 = c_x2 - 12
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

        # Level numbers above
        draw.text((cx_supp, r_top + 14), f"{supp:,.{digits}f}", fill=(0, 255, 136), font=f_lvl_num, anchor="ma")
        draw.text((cx_rup, r_top + 14), f"{rev_up:,.{digits}f}", fill=(0, 255, 136), font=f_lvl_num, anchor="ma")
        draw.text((cx_rdn, r_top + 14), f"{rev_dn:,.{digits}f}", fill=(255, 75, 75), font=f_lvl_num, anchor="ma")
        draw.text((cx_res, r_top + 14), f"{res:,.{digits}f}", fill=(255, 75, 75), font=f_lvl_num, anchor="ma")

        # Slider track
        bar_y1 = r_top + 54
        bar_y2 = r_top + 62
        draw_gradient_bar(draw, BAR_X1, bar_y1, BAR_X2, bar_y2)

        # Connector ticks
        draw.line([(cx_supp, r_top + 30), (cx_supp, bar_y1)], fill=(0, 255, 136), width=1)
        draw.line([(cx_rup, r_top + 30), (cx_rup, bar_y1)], fill=(0, 255, 136), width=1)
        draw.line([(cx_rdn, r_top + 30), (cx_rdn, bar_y1)], fill=(255, 75, 75), width=1)
        draw.line([(cx_res, r_top + 30), (cx_res, bar_y1)], fill=(255, 75, 75), width=1)

        # Live pointer
        pct_snr = (p_val - supp) / (res - supp) * 100.0 if res > supp else 50.0
        clamp_pct = max(0.0, min(100.0, pct_snr))
        pin_x = int(BAR_X1 + BAR_W * (clamp_pct / 100.0))

        # Floating %SNR Tooltip badge
        b_txt = f"{pct_snr:.1f}%"
        draw.rounded_rectangle([(pin_x - 22, r_top + 28), (pin_x + 22, r_top + 48)], radius=7, fill=(255, 214, 0))
        draw.text((pin_x, r_top + 38), b_txt, fill=(0, 0, 0), font=f_badge, anchor="mm")
        draw.line([(pin_x, r_top + 48), (pin_x, (bar_y1 + bar_y2) // 2)], fill=(255, 214, 0), width=2)
        draw.ellipse([(pin_x - 7, (bar_y1 + bar_y2)//2 - 7), (pin_x + 7, (bar_y1 + bar_y2)//2 + 7)], fill=(0, 160, 255), outline=(255, 255, 255), width=2)
        draw.ellipse([(pin_x - 4, (bar_y1 + bar_y2)//2 - 4), (pin_x + 4, (bar_y1 + bar_y2)//2 + 4)], fill=(255, 255, 255))

        # Ticks below bar
        TICK_COL = (165, 205, 250)
        draw.text((cx_supp, bar_y2 + 4), "0%", fill=TICK_COL, font=f_snr_tick, anchor="mt")
        draw.text((cx_rup, bar_y2 + 4), "20%", fill=TICK_COL, font=f_snr_tick, anchor="mt")
        draw.text((cx_mid, bar_y2 + 4), "50%", fill=TICK_COL, font=f_snr_tick, anchor="mt")
        draw.text((cx_rdn, bar_y2 + 4), "80%", fill=TICK_COL, font=f_snr_tick, anchor="mt")
        draw.text((cx_res, bar_y2 + 4), "100%", fill=TICK_COL, font=f_snr_tick, anchor="mt")

        # Three Zone Boxes
        z_y1 = bar_y2 + 18
        z_y2 = z_y1 + 22
        draw.rounded_rectangle([(BAR_X1, z_y1), (cx_rup, z_y2)], radius=3, fill=(4, 45, 25), outline=(0, 220, 110), width=1)
        draw.text((BAR_X1 + int((cx_rup - BAR_X1) * 0.50), z_y1 + 2), "BUY ZONE\n0% - 20%", fill=(0, 255, 136), font=f_zone_box, anchor="ma", align="center")

        draw.rounded_rectangle([(cx_rup + 4, z_y1), (cx_rdn - 4, z_y2)], radius=3, fill=(45, 38, 12), outline=(220, 180, 0), width=1)
        draw.text((cx_rup + int((cx_rdn - cx_rup) * 0.50), z_y1 + 2), "WAIT ZONE\n20% - 80%", fill=(255, 225, 0), font=f_zone_box, anchor="ma", align="center")

        draw.rounded_rectangle([(cx_rdn, z_y1), (BAR_X2, z_y2)], radius=3, fill=(55, 16, 24), outline=(240, 50, 60), width=1)
        draw.text((cx_rdn + int((BAR_X2 - cx_rdn) * 0.50), z_y1 + 2), "SELL ZONE\n80% - 100%", fill=(255, 80, 80), font=f_zone_box, anchor="ma", align="center")

        # 5. TICK FLOW
        c_x1, c_x2 = 638, 722
        cx = (c_x1 + c_x2) // 2
        b_vol = item.get("buy_tick", 1240)
        s_vol = item.get("sell_tick", 980)
        draw.text((cx - 18, r_mid - 24), f"{b_vol:,}", fill=(0, 255, 136), font=f_vol_num, anchor="ma")
        draw.text((cx + 18, r_mid - 24), f"{s_vol:,}", fill=(255, 80, 80), font=f_vol_num, anchor="ma")
        tot_vol = max(1, b_vol + s_vol)
        b_h = int((b_vol / tot_vol) * 40)
        s_h = int((s_vol / tot_vol) * 40)
        draw.rounded_rectangle([(cx - 26, r_mid + 20 - b_h), (cx - 8, r_mid + 20)], radius=3, fill=(0, 240, 120))
        draw.rounded_rectangle([(cx + 8, r_mid + 20 - s_h), (cx + 26, r_mid + 20)], radius=3, fill=(240, 50, 50))

        # 6. VOLUME RATIO
        c_x1, c_x2 = 724, 804
        cx = (c_x1 + c_x2) // 2
        b_pct = round(b_vol / tot_vol * 100)
        draw_donut_ratio(draw, cx, r_mid, 22, b_pct, f_donut)

        # 7. DELTA
        c_x1, c_x2 = 806, 874
        cx = (c_x1 + c_x2) // 2
        delta = b_vol - s_vol
        delta_pct = round((delta / tot_vol) * 100)
        d_sgn = "+" if delta >= 0 else ""
        d_col = (0, 255, 136) if delta >= 0 else (255, 75, 75)
        draw.text((cx, r_mid - 12), f"{d_sgn}{delta:,}", fill=d_col, font=f_delta, anchor="mm")
        draw.text((cx, r_mid + 10), f"({d_sgn}{delta_pct}%)", fill=d_col, font=f_delta_sub, anchor="mm")

        # 8. PRESSURE
        c_x1, c_x2 = 876, 960
        cx = (c_x1 + c_x2) // 2
        pressure = item.get("pressure", "BUY PRESSURE").replace("_", " ").upper()
        if "BUY" in pressure:
            pr_col = (0, 255, 136)
            pr_bg = (4, 40, 22)
        elif "SELL" in pressure:
            pr_col = (255, 75, 75)
            pr_bg = (45, 14, 20)
        else:
            pr_col = (255, 214, 0)
            pr_bg = (40, 35, 10)
        draw.rounded_rectangle([(c_x1 + 4, r_mid - 18), (c_x2 - 4, r_mid + 18)], radius=6, fill=pr_bg, outline=pr_col, width=1)
        pr_lines = pressure.split()
        if len(pr_lines) > 1:
            draw.text((cx, r_mid - 8), pr_lines[0], fill=pr_col, font=get_font(10, bold=True), anchor="mm")
            draw.text((cx, r_mid + 7), " ".join(pr_lines[1:]), fill=pr_col, font=get_font(10, bold=True), anchor="mm")
        else:
            draw.text((cx, r_mid), pressure, fill=pr_col, font=get_font(10, bold=True), anchor="mm")

        # 9. TREND
        c_x1, c_x2 = 962, 1044
        cx = (c_x1 + c_x2) // 2
        trend = item.get("trend", "UP").upper()
        if "UP" in trend:
            tr_col = (0, 255, 136)
            tr_dir = "UP"
            tr_sub = "(EMA50 > EMA200)"
        elif "DOWN" in trend:
            tr_col = (255, 75, 75)
            tr_dir = "DOWN"
            tr_sub = "(EMA50 < EMA200)"
        else:
            tr_col = (255, 214, 0)
            tr_dir = "SIDE"
            tr_sub = "(RANGE)"

        draw_vector_arrow(draw, cx, r_mid - 16, tr_dir)
        draw.text((cx, r_mid + 2), tr_dir, fill=tr_col, font=f_trend, anchor="mm")
        draw.text((cx, r_mid + 18), tr_sub, fill=(150, 190, 230), font=f_trend_sub, anchor="mm")

        # 10. REVERSAL SCORE
        c_x1, c_x2 = 1046, 1114
        cx = (c_x1 + c_x2) // 2
        rev_score = item.get("reversal_score", 48)
        rev_col = (0, 229, 255) if rev_score >= 60 else (255, 214, 0) if rev_score >= 40 else (160, 180, 210)
        draw_circular_gauge(draw, cx, r_mid, 22, rev_score, 100, rev_col, text=str(rev_score), font=f_gauge_val)

        # 11. CONFIDENCE
        c_x1, c_x2 = 1116, 1198
        cx = (c_x1 + c_x2) // 2
        conf_score = item.get("confidence", 82)
        conf_col = (0, 255, 136) if conf_score >= 85 else (0, 229, 255) if conf_score >= 70 else (255, 214, 0) if conf_score >= 55 else (255, 75, 75)
        draw_circular_gauge(draw, cx, r_mid, 22, conf_score, 100, conf_col, text=f"{conf_score}%", font=f_gauge_val)

        # 12. ACTION SCORE
        c_x1, c_x2 = 1200, 1282
        cx = (c_x1 + c_x2) // 2
        act_score = item.get("action_score", 72)
        act_col = (0, 255, 136) if act_score >= 85 else (0, 229, 255) if act_score >= 75 else (255, 180, 0) if act_score >= 65 else (255, 75, 75)
        draw_circular_gauge(draw, cx, r_mid, 22, act_score, 100, act_col, text=str(act_score), font=f_gauge_val)

        # 13. GRADE
        c_x1, c_x2 = 1284, 1340
        cx = (c_x1 + c_x2) // 2
        grade = item.get("grade", "B").upper()
        if "A+" in grade:
            gr_bg = (0, 200, 80)
            gr_txt = (0, 0, 0)
        elif "A" in grade:
            gr_bg = (0, 160, 70)
            gr_txt = (255, 255, 255)
        elif "B" in grade:
            gr_bg = (245, 185, 0)
            gr_txt = (0, 0, 0)
        elif "C" in grade:
            gr_bg = (240, 110, 0)
            gr_txt = (255, 255, 255)
        else:
            gr_bg = (180, 40, 40)
            gr_txt = (255, 255, 255)
        draw.rounded_rectangle([(c_x1 + 4, r_mid - 24), (c_x2 - 4, r_mid + 24)], radius=8, fill=gr_bg)
        draw.text((cx, r_mid - 1), grade, fill=gr_txt, font=f_grade, anchor="mm")

        # 14. FINAL STATUS
        c_x1, c_x2 = 1342, 1464
        cx = (c_x1 + c_x2) // 2
        status = item.get("status", "WAIT").upper()
        status_sub = item.get("status_sub", "Konsolidasi di tengah")
        if "BUY" in status:
            st_col = (0, 255, 136)
            st_bg = (4, 40, 22)
        elif "SELL" in status:
            st_col = (255, 75, 75)
            st_bg = (45, 14, 20)
        elif "REVERSAL" in status:
            st_col = (255, 160, 0)
            st_bg = (45, 28, 8)
        else:
            st_col = (255, 214, 0)
            st_bg = (40, 35, 10)
        draw.rounded_rectangle([(c_x1 + 4, r_mid - 24), (c_x2 - 4, r_mid + 24)], radius=7, fill=st_bg, outline=st_col, width=1)
        draw.text((cx, r_mid - 10), status, fill=st_col, font=f_status, anchor="mm")
        draw.text((cx, r_mid + 10), status_sub, fill=(215, 235, 255), font=f_status_sub, anchor="mm")

        # 15. TP / SL SUGGESTION
        c_x1, c_x2 = 1466, 1546
        tp1 = item.get("tp1", p_val)
        tp2 = item.get("tp2", p_val)
        tp3 = item.get("tp3", p_val)
        sl = item.get("sl", p_val)
        draw.text((c_x1 + 6, r_mid - 24), "TP1", fill=(140, 185, 230), font=f_tpsl)
        draw.text((c_x2 - 6, r_mid - 24), f"{tp1:,.{digits}f}", fill=(0, 255, 136), font=f_tpsl_num, anchor="ra")
        draw.text((c_x1 + 6, r_mid - 8), "TP2", fill=(140, 185, 230), font=f_tpsl)
        draw.text((c_x2 - 6, r_mid - 8), f"{tp2:,.{digits}f}", fill=(0, 255, 136), font=f_tpsl_num, anchor="ra")
        draw.text((c_x1 + 6, r_mid + 8), "TP3", fill=(140, 185, 230), font=f_tpsl)
        draw.text((c_x2 - 6, r_mid + 8), f"{tp3:,.{digits}f}", fill=(0, 255, 136), font=f_tpsl_num, anchor="ra")
        draw.text((c_x1 + 6, r_mid + 24), "SL", fill=(255, 120, 120), font=f_tpsl)
        draw.text((c_x2 - 6, r_mid + 24), f"{sl:,.{digits}f}", fill=(255, 75, 75), font=f_tpsl_num, anchor="ra")

        # 16. R:R
        c_x1, c_x2 = 1548, 1584
        cx = (c_x1 + c_x2) // 2
        rr_str = item.get("rr", "1:1.9")
        draw.text((cx, r_mid), rr_str, fill=(255, 255, 255), font=f_rr, anchor="mm")

    # 4. BOTTOM PANELS (Y: 694 to 884)
    draw.line([(14, 690), (W - 14, 690)], fill=(18, 60, 125), width=2)
    Y_BTM = 696
    H_BTM = 190

    # Panel 1: ZONA %SNR (LOKASI HARGA) [w: 264]
    draw.rounded_rectangle([(16, Y_BTM), (280, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((26, Y_BTM + 8), "ZONA %SNR (LOKASI HARGA)", fill=(215, 235, 255), font=get_font(10, bold=True))
    draw.rounded_rectangle([(26, Y_BTM + 30), (102, Y_BTM + 176)], radius=4, fill=(0, 200, 100))
    draw.text((64, Y_BTM + 55), "BUY ZONE\n0% - 20%\nDekat\nSupport", fill=(0, 0, 0), font=get_font(10, bold=True), anchor="ma", align="center")
    draw.rounded_rectangle([(108, Y_BTM + 30), (188, Y_BTM + 176)], radius=4, fill=(245, 185, 0))
    draw.text((148, Y_BTM + 55), "WAIT ZONE\n20% - 80%\nTunggu\nkonfirmasi", fill=(0, 0, 0), font=get_font(10, bold=True), anchor="ma", align="center")
    draw.rounded_rectangle([(194, Y_BTM + 30), (270, Y_BTM + 176)], radius=4, fill=(240, 50, 50))
    draw.text((232, Y_BTM + 55), "SELL ZONE\n80% - 100%\nDekat\nResist", fill=(255, 255, 255), font=get_font(10, bold=True), anchor="ma", align="center")

    # Panel 2: THRESHOLD PRESSURE (TICK VOLUME) [w: 292]
    draw.rounded_rectangle([(288, Y_BTM), (580, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((298, Y_BTM + 8), "THRESHOLD PRESSURE (TICK VOLUME)", fill=(215, 235, 255), font=get_font(10, bold=True))
    p_info = [
        ("> 70%", "STRONG BUY", (0, 255, 136)),
        ("65% - 70%", "BUY PRESSURE", (0, 220, 110)),
        ("55% - 65%", "BUY PRESSURE MODERATE", (120, 240, 170)),
        ("45% - 55%", "BALANCED", (255, 220, 0)),
        ("35% - 45%", "SELL PRESSURE MODERATE", (255, 140, 140)),
        ("30% - 35%", "SELL PRESSURE", (255, 90, 90)),
        ("< 30%", "STRONG SELL", (255, 50, 50))
    ]
    f_p = get_font(9, bold=True)
    for idx, (p_rng, p_lbl, p_c) in enumerate(p_info):
        py = Y_BTM + 28 + idx * 22
        draw.text((304, py), p_rng, fill=(180, 215, 250), font=f_p)
        draw.text((410, py), f"=  {p_lbl}", fill=p_c, font=f_p)

    # Panel 3: CONFIDENCE THRESHOLD (0 - 100) [w: 272]
    draw.rounded_rectangle([(588, Y_BTM), (860, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((598, Y_BTM + 8), "CONFIDENCE THRESHOLD (0 - 100)", fill=(215, 235, 255), font=get_font(10, bold=True))
    c_info = [
        ("85 - 100", "VERY HIGH", (0, 255, 136)),
        ("70 - 84", "HIGH", (0, 229, 255)),
        ("55 - 69", "MODERATE", (255, 220, 0)),
        ("40 - 54", "LOW", (255, 150, 0)),
        ("0 - 39", "WEAK", (255, 75, 75))
    ]
    for idx, (c_rng, c_lbl, c_c) in enumerate(c_info):
        cy_pos = Y_BTM + 32 + idx * 28
        draw.text((604, cy_pos), c_rng, fill=(180, 215, 250), font=f_p)
        draw.text((700, cy_pos), f"=  {c_lbl}", fill=c_c, font=f_p)

    # Panel 4: ACTION SCORE & SIGNAL GRADE [w: 312]
    draw.rounded_rectangle([(868, Y_BTM), (1180, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((878, Y_BTM + 8), "ACTION SCORE & SIGNAL GRADE", fill=(215, 235, 255), font=get_font(10, bold=True))
    g_info = [
        ("A+", "Conf >= 90  |  Action >= 85", "STRONG ENTRY", (0, 255, 136)),
        ("A",  "Conf >= 85  |  Action >= 75", "ENTRY", (0, 220, 110)),
        ("B",  "Conf >= 75  |  Action >= 65", "SETUP / WATCH", (255, 220, 0)),
        ("C",  "Conf >= 65  |  Action >= 50", "WAIT", (255, 140, 0)),
        ("D",  "Below threshold", "NO TRADE", (255, 75, 75))
    ]
    for idx, (gr_lbl, gr_req, gr_st, gr_c) in enumerate(g_info):
        gy = Y_BTM + 30 + idx * 30
        draw.rounded_rectangle([(878, gy - 2), (904, gy + 18)], radius=4, fill=gr_c)
        draw.text((891, gy + 8), gr_lbl, fill=(0, 0, 0) if gr_lbl in ["A+", "B"] else (255, 255, 255), font=get_font(10, bold=True), anchor="mm")
        draw.text((914, gy), gr_req, fill=(180, 215, 250), font=get_font(9, bold=False))
        draw.text((914, gy + 12), f"→ {gr_st}", fill=gr_c, font=get_font(9, bold=True))

    # Panel 5: TRADING PRINCIPLE & DISCIPLINE [w: 396]
    draw.rounded_rectangle([(1188, Y_BTM), (1584, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(15, 50, 105), width=1)
    draw.text((1198, Y_BTM + 8), "TRADING PRINCIPLE & DISCIPLINE", fill=(215, 235, 255), font=get_font(10, bold=True))
    draw.text((1198, Y_BTM + 28), "LOCATION → PRESSURE → TREND → REJECTION\n→ CONFIDENCE → ACTION SCORE → STATUS", fill=(0, 229, 255), font=get_font(9, bold=True))
    f_rule = get_font(9, bold=False)
    draw.text((1198, Y_BTM + 65), "• SNR = LOCATION (Zona risiko optimal)", fill=(190, 220, 255), font=f_rule)
    draw.text((1198, Y_BTM + 85), "• TICK FLOW = PRESSURE (Dominasi buyers vs sellers)", fill=(190, 220, 255), font=f_rule)
    draw.text((1198, Y_BTM + 105), "• TREND = DIRECTION (Arah momentum pasar mayor)", fill=(190, 220, 255), font=f_rule)
    draw.text((1198, Y_BTM + 125), "• PRICE ACTION = CONFIRMATION (Rejection valid)", fill=(190, 220, 255), font=f_rule)
    draw.text((1198, Y_BTM + 145), "• CONFIDENCE = EVIDENCE  |  ACTION = TRADEABILITY", fill=(255, 220, 0), font=f_rule)
    draw.text((1198, Y_BTM + 165), "Discipline: A+ rare. Tanpa konfirmasi lengkap = NO TRADE.", fill=(255, 120, 120), font=f_rule)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path, "PNG", optimize=True)

    return img

def generate_sr_card_bytes(data_list: list) -> bytes:
    img = render_bloomberg_dashboard_card(data_list)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
