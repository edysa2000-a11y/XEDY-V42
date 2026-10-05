import os
import io
import math
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

WIB = timezone(timedelta(hours=7))

def get_font(size: int, bold: bool = False):
    candidates = [
        # Windows
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        # Linux / Container fallback
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_sphere(draw, cx: int, cy: int, radius: int, base_color: tuple):
    r, g, b = base_color
    for i in range(radius, 0, -1):
        factor = 1.0 - (i / radius) * 0.65
        ox = cx - int((radius - i) * 0.38)
        oy = cy - int((radius - i) * 0.38)
        cr = min(255, int(r + (255 - r) * factor * 0.85))
        cg = min(255, int(g + (255 - g) * factor * 0.85))
        cb = min(255, int(b + (255 - b) * factor * 0.85))
        draw.ellipse([(ox - i, oy - i), (ox + i, oy + i)], fill=(cr, cg, cb))

def draw_flag_icon(draw, cx: int, cy: int, radius: int, icon_type: str):
    box = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    if icon_type == "gold":
        draw_sphere(draw, cx, cy, radius, (255, 190, 0))
        draw.line([(cx - 7, cy - 2), (cx + 7, cy - 2)], fill=(255, 245, 180), width=2)
    elif icon_type == "eu":
        draw.ellipse(box, fill=(0, 51, 153), outline=(0, 102, 204), width=1)
        for ang in range(0, 360, 30):
            rad = math.radians(ang)
            sx = int(cx + (radius - 5) * math.cos(rad))
            sy = int(cy + (radius - 5) * math.sin(rad))
            draw.point((sx, sy), fill=(255, 204, 0))
            draw.point((sx + 1, sy), fill=(255, 204, 0))
    elif icon_type == "oil":
        draw_sphere(draw, cx, cy, radius, (30, 35, 45))
        draw.ellipse([(cx - 4, cy - 1), (cx + 4, cy + 7)], fill=(0, 0, 0))
        draw.polygon([(cx, cy - 6), (cx - 4, cy + 1), (cx + 4, cy + 1)], fill=(0, 0, 0))
    elif icon_type == "japan":
        draw.ellipse(box, fill=(245, 245, 245), outline=(180, 180, 180), width=1)
        sun_r = int(radius * 0.55)
        draw.ellipse([(cx - sun_r, cy - sun_r), (cx + sun_r, cy + sun_r)], fill=(188, 0, 45))
    else:
        draw_sphere(draw, cx, cy, radius, (0, 150, 255))

def draw_vector_arrow(draw, cx: int, cy: int, direction: str, color: tuple):
    if direction == "UP":
        draw.line([(cx - 7, cy + 7), (cx + 7, cy - 7)], fill=color, width=3)
        draw.line([(cx - 1, cy - 7), (cx + 7, cy - 7)], fill=color, width=3)
        draw.line([(cx + 7, cy - 7), (cx + 7, cy + 1)], fill=color, width=3)
    elif direction == "DOWN":
        draw.line([(cx - 7, cy - 7), (cx + 7, cy + 7)], fill=color, width=3)
        draw.line([(cx - 1, cy + 7), (cx + 7, cy + 7)], fill=color, width=3)
        draw.line([(cx + 7, cy + 7), (cx + 7, cy - 1)], fill=color, width=3)
    else:
        draw.line([(cx - 7, cy), (cx + 7, cy)], fill=color, width=3)
        draw.line([(cx + 2, cy - 5), (cx + 7, cy)], fill=color, width=3)
        draw.line([(cx + 2, cy + 5), (cx + 7, cy)], fill=color, width=3)

def draw_donut_ratio(draw, cx: int, cy: int, radius: int, buy_pct: float, font_inner):
    buy_ang = int(buy_pct / 100.0 * 360)
    box = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    inner_r = radius - 5
    inner_box = [(cx - inner_r, cy - inner_r), (cx + inner_r, cy + inner_r)]
    
    draw.ellipse(box, fill=(235, 50, 50))
    if buy_ang > 0:
        draw.pieslice(box, start=-90, end=-90 + buy_ang, fill=(0, 230, 118))
        
    draw.ellipse(inner_box, fill=(2, 14, 38))
    
    sell_pct = 100 - buy_pct
    draw.text((cx, cy - 8), f"{int(buy_pct)}%", fill=(0, 230, 118), font=font_inner, anchor="mm")
    draw.text((cx, cy + 6), f"{int(sell_pct)}%", fill=(255, 68, 68), font=font_inner, anchor="mm")

def draw_gradient_bar(draw, x1: int, y1: int, x2: int, y2: int):
    w = x2 - x1
    for x in range(w):
        t = x / max(1, w - 1)
        if t < 0.5:
            lt = t / 0.5
            cr = int(0 + (255 - 0) * lt)
            cg = int(230 + (214 - 230) * lt)
            cb = int(118 + (0 - 118) * lt)
        else:
            lt = (t - 0.5) / 0.5
            cr = int(255 + (255 - 255) * lt)
            cg = int(214 + (68 - 214) * lt)
            cb = int(0 + (68 - 0) * lt)
        draw.line([(x1 + x, y1), (x1 + x, y2)], fill=(cr, cg, cb), width=1)

def render_bloomberg_dashboard_card(data_list: list, output_path: str = None) -> Image.Image:
    """
    Renders 16:9 Landscape (1200 x 675) Live Institutional Trading Dashboard:
    Bloomberg Terminal + TradingView + Hedge Fund Desk.
    """
    W, H = 1200, 675
    im = Image.new("RGB", (W, H), (2, 13, 34)) # Institutional Deep Navy
    draw = ImageDraw.Draw(im)

    # Glowing outer border
    draw.rounded_rectangle([(6, 6), (W - 6, H - 6)], radius=16, outline=(0, 95, 204), width=3)
    draw.rounded_rectangle([(9, 9), (W - 9, H - 9)], radius=14, outline=(0, 45, 110), width=1)

    # Fonts
    f_hdr = get_font(10, bold=True)
    f_pair = get_font(15, bold=True)
    f_sub = get_font(10, bold=True)
    f_price = get_font(19, bold=True)
    f_chg = get_font(11, bold=True)
    f_lvl_num = get_font(11, bold=True)
    f_lvl_pill = get_font(9, bold=True)
    f_snr_tick = get_font(9, bold=False)
    f_zone_box = get_font(8, bold=True)
    f_vol_num = get_font(10, bold=True)
    f_donut = get_font(9, bold=True)
    f_delta = get_font(13, bold=True)
    f_delta_sub = get_font(10, bold=True)
    f_trend = get_font(11, bold=True)
    f_status = get_font(13, bold=True)
    f_status_sub = get_font(9, bold=False)
    f_badge = get_font(10, bold=True)

    # Precise column centers and anchors
    X_PAIR = 18
    X_PRICE = 135
    X_CHG = 228
    
    # SNR Section: 295 to 655 (Width 360px)
    X_BAR_START = 295
    X_BAR_END = 655
    BAR_W = X_BAR_END - X_BAR_START # 360
    
    CX_SUPP = X_BAR_START # 295 (0%)
    CX_REV_UP = X_BAR_START + int(BAR_W * 0.20) # 367 (20%)
    CX_BAR_MID = X_BAR_START + int(BAR_W * 0.50) # 475 (50%)
    CX_REV_DN = X_BAR_START + int(BAR_W * 0.80) # 583 (80%)
    CX_RES = X_BAR_END # 655 (100%)
    
    CX_VOL = 718
    CX_RATIO = 795
    CX_DELTA = 862
    CX_TREND = 925
    X_STATUS = 965
    STATUS_W = 215

    # 1. HEADER ROW (Y: 14 to 52)
    Y_HDR = 20
    draw.text((X_PAIR + 18, Y_HDR), "PAIR", fill=(130, 170, 215), font=f_hdr)
    draw.text((X_PRICE + 25, Y_HDR - 6), "LIVE\nPRICE", fill=(130, 170, 215), font=f_hdr, anchor="ma")
    draw.text((X_CHG + 15, Y_HDR - 6), "CHANGE\n(%)", fill=(130, 170, 215), font=f_hdr, anchor="ma")
    
    draw.text((CX_SUPP, Y_HDR - 6), "SUPPORT\n(S)", fill=(0, 230, 118), font=f_hdr, anchor="ma")
    draw.text((CX_REV_UP, Y_HDR - 6), "REV-UP\n(20%)", fill=(0, 230, 118), font=f_hdr, anchor="ma")
    draw.text((CX_BAR_MID, Y_HDR - 6), "POSITION\n%SNR", fill=(255, 204, 0), font=f_hdr, anchor="ma")
    draw.text((CX_REV_DN, Y_HDR - 6), "REV-DOWN\n(80%)", fill=(255, 68, 68), font=f_hdr, anchor="ma")
    draw.text((CX_RES, Y_HDR - 6), "RESISTANCE\n(R)", fill=(255, 68, 68), font=f_hdr, anchor="ma")
    
    draw.text((CX_VOL, Y_HDR - 6), "TICK VOLUME\n(BUY / SELL)", fill=(130, 170, 215), font=f_hdr, anchor="ma")
    draw.text((CX_RATIO, Y_HDR - 6), "VOLUME RATIO\n(B% / S%)", fill=(130, 170, 215), font=f_hdr, anchor="ma")
    draw.text((CX_DELTA, Y_HDR - 6), "DELTA\n(B-S)", fill=(130, 170, 215), font=f_hdr, anchor="ma")
    draw.text((CX_TREND, Y_HDR), "TREND", fill=(130, 170, 215), font=f_hdr, anchor="ma")
    draw.text((X_STATUS + STATUS_W // 2, Y_HDR), "STATUS", fill=(130, 170, 215), font=f_hdr, anchor="ma")

    # Header horizontal line
    draw.line([(14, 54), (W - 14, 54)], fill=(12, 38, 78), width=1)

    # 2. INSTRUMENT ROWS (4 rows)
    ROW_H = 120
    Y_START = 56

    for i, item in enumerate(data_list):
        r_top = Y_START + i * ROW_H
        r_mid = r_top + 60
        
        # Row divider
        if i > 0:
            draw.line([(14, r_top), (W - 14, r_top)], fill=(12, 38, 78), width=1)

        # A. PAIR (Icon + Name + Subtitle)
        draw_flag_icon(draw, X_PAIR + 14, r_mid - 2, 16, item.get("icon_type", "gold"))
        p_name = item["name"]
        p_col = (255, 204, 0) if p_name == "GOLD" else (255, 255, 255)
        draw.text((X_PAIR + 38, r_mid - 18), p_name, fill=p_col, font=f_pair)
        draw.text((X_PAIR + 38, r_mid + 4), item["subtitle"], fill=(100, 145, 195), font=f_sub)

        # B. LIVE PRICE & CHANGE
        p_val = item["price"]
        digits = item.get("digits", 2)
        draw.text((X_PRICE, r_mid - 18), f"{p_val:,.{digits}f}", fill=(255, 255, 255), font=f_price)
        
        c_val = item.get("change_val", 0.0)
        c_pct = item.get("change_pct", 0.0)
        c_sgn = "+" if c_val >= 0 else ""
        c_col = (0, 230, 118) if c_val >= 0 else (255, 68, 68)
        draw.text((X_CHG, r_mid - 14), f"{c_sgn}{c_val:.{digits}f}", fill=c_col, font=f_chg)
        draw.text((X_CHG, r_mid + 4), f"({c_sgn}{c_pct:.2f}%)", fill=c_col, font=f_chg)

        # C. S, REV-UP, REV-DOWN, R VALUES & PILLS
        supp = item["support"]
        res = item["resistance"]
        rev_up = supp + 0.20 * (res - supp)
        rev_dn = supp + 0.80 * (res - supp)

        fmt_s = f"{int(supp):,}" if digits == 0 or (supp == int(supp) and supp >= 100) else f"{supp:,.{digits}f}"
        fmt_rup = f"{int(rev_up):,}" if digits == 0 or (rev_up == int(rev_up) and rev_up >= 100) else f"{rev_up:,.{digits}f}"
        fmt_rdn = f"{int(rev_dn):,}" if digits == 0 or (rev_dn == int(rev_dn) and rev_dn >= 100) else f"{rev_dn:,.{digits}f}"
        fmt_r = f"{int(res):,}" if digits == 0 or (res == int(res) and res >= 100) else f"{res:,.{digits}f}"

        # Levels Top Labels
        draw.text((CX_SUPP, r_top + 14), fmt_s, fill=(0, 230, 118), font=f_lvl_num, anchor="ma")
        draw.text((CX_REV_UP, r_top + 14), fmt_rup, fill=(0, 230, 118), font=f_lvl_num, anchor="ma")
        draw.text((CX_REV_DN, r_top + 14), fmt_rdn, fill=(255, 68, 68), font=f_lvl_num, anchor="ma")
        draw.text((CX_RES, r_top + 14), fmt_r, fill=(255, 68, 68), font=f_lvl_num, anchor="ma")

        # Level indicator pills
        # S pill
        draw.rounded_rectangle([(CX_SUPP - 10, r_top + 29), (CX_SUPP + 10, r_top + 41)], radius=3, fill=(0, 200, 100))
        draw.text((CX_SUPP, r_top + 30), "S", fill=(0, 0, 0), font=f_lvl_pill, anchor="ma")
        # REV-UP pill
        draw.rounded_rectangle([(CX_REV_UP - 22, r_top + 29), (CX_REV_UP + 22, r_top + 41)], radius=3, fill=(0, 50, 30), outline=(0, 230, 118), width=1)
        draw.text((CX_REV_UP, r_top + 30), "REV-UP", fill=(0, 230, 118), font=f_lvl_pill, anchor="ma")
        # REV-DOWN pill
        draw.rounded_rectangle([(CX_REV_DN - 26, r_top + 29), (CX_REV_DN + 26, r_top + 41)], radius=3, fill=(50, 15, 20), outline=(255, 68, 68), width=1)
        draw.text((CX_REV_DN, r_top + 30), "REV-DOWN", fill=(255, 68, 68), font=f_lvl_pill, anchor="ma")
        # R pill
        draw.rounded_rectangle([(CX_RES - 10, r_top + 29), (CX_RES + 10, r_top + 41)], radius=3, fill=(235, 50, 50))
        draw.text((CX_RES, r_top + 30), "R", fill=(255, 255, 255), font=f_lvl_pill, anchor="ma")

        # D. SNR BAR & ZONES
        bar_y1 = r_top + 49
        bar_y2 = r_top + 57
        draw_gradient_bar(draw, X_BAR_START, bar_y1, X_BAR_END, bar_y2)

        # Vertical connector tick lines from pills to bar
        draw.line([(CX_SUPP, r_top + 41), (CX_SUPP, bar_y1)], fill=(0, 230, 118), width=1)
        draw.line([(CX_REV_UP, r_top + 41), (CX_REV_UP, bar_y1)], fill=(0, 230, 118), width=1)
        draw.line([(CX_REV_DN, r_top + 41), (CX_REV_DN, bar_y1)], fill=(255, 68, 68), width=1)
        draw.line([(CX_RES, r_top + 41), (CX_RES, bar_y1)], fill=(255, 68, 68), width=1)

        # 0%, 20%, 50%, 80%, 100% percentage tick labels below bar
        draw.text((CX_SUPP, bar_y2 + 3), "0%", fill=(100, 140, 180), font=f_snr_tick, anchor="mt")
        draw.text((CX_REV_UP, bar_y2 + 3), "20%", fill=(100, 140, 180), font=f_snr_tick, anchor="mt")
        draw.text((CX_BAR_MID, bar_y2 + 3), "50%", fill=(100, 140, 180), font=f_snr_tick, anchor="mt")
        draw.text((CX_REV_DN, bar_y2 + 3), "80%", fill=(100, 140, 180), font=f_snr_tick, anchor="mt")
        draw.text((CX_RES, bar_y2 + 3), "100%", fill=(100, 140, 180), font=f_snr_tick, anchor="mt")

        # Three Zone Boxes below ticks
        z_y1 = bar_y2 + 16
        z_y2 = z_y1 + 16
        # Buy Zone (0-20%)
        draw.rounded_rectangle([(X_BAR_START, z_y1), (CX_REV_UP, z_y2)], radius=3, fill=(4, 38, 22), outline=(0, 190, 90), width=1)
        draw.text((X_BAR_START + int((CX_REV_UP - X_BAR_START) * 0.50), z_y1 + 2), "BUY ZONE\n(0% - 20%)", fill=(0, 230, 118), font=f_zone_box, anchor="ma", align="center")
        # Wait Zone (20-80%)
        draw.rounded_rectangle([(CX_REV_UP + 3, z_y1), (CX_REV_DN - 3, z_y2)], radius=3, fill=(38, 32, 10), outline=(190, 160, 0), width=1)
        draw.text((CX_REV_UP + int((CX_REV_DN - CX_REV_UP) * 0.50), z_y1 + 2), "WAIT ZONE\n(20% - 80%)", fill=(255, 214, 0), font=f_zone_box, anchor="ma", align="center")
        # Sell Zone (80-100%)
        draw.rounded_rectangle([(CX_REV_DN, z_y1), (X_BAR_END, z_y2)], radius=3, fill=(45, 14, 20), outline=(210, 45, 55), width=1)
        draw.text((CX_REV_DN + int((X_BAR_END - CX_REV_DN) * 0.50), z_y1 + 2), "SELL ZONE\n(80% - 100%)", fill=(255, 68, 68), font=f_zone_box, anchor="ma", align="center")

        # %SNR Live Pointer Pin & Tooltip
        pct_snr = (p_val - supp) / (res - supp) * 100.0 if res > supp else 50.0
        clamp_pct = max(0.0, min(100.0, pct_snr))
        pin_x = int(X_BAR_START + BAR_W * (clamp_pct / 100.0))

        # Tooltip badge above pin
        b_txt = f"{pct_snr:.1f}%"
        draw.rounded_rectangle([(pin_x - 19, bar_y1 - 24), (pin_x + 19, bar_y1 - 7)], radius=8, fill=(255, 204, 0))
        draw.text((pin_x, bar_y1 - 22), b_txt, fill=(0, 0, 0), font=f_badge, anchor="mt")

        # Glowing Pin
        pin_mid_y = (bar_y1 + bar_y2) // 2
        draw.ellipse([(pin_x - 7, pin_mid_y - 7), (pin_x + 7, pin_mid_y + 7)], fill=(0, 160, 255), outline=(255, 255, 255), width=2)
        draw.ellipse([(pin_x - 4, pin_mid_y - 4), (pin_x + 4, pin_mid_y + 4)], fill=(255, 255, 255))

        # E. TICK VOLUME (BUY / SELL BARS)
        b_vol = item.get("buy_tick", 1200)
        s_vol = item.get("sell_tick", 1000)
        draw.text((CX_VOL - 18, r_mid - 24), f"{b_vol:,}", fill=(255, 255, 255), font=f_vol_num, anchor="ma")
        draw.text((CX_VOL + 22, r_mid - 24), f"{s_vol:,}", fill=(255, 100, 100), font=f_vol_num, anchor="ma")
        draw.rounded_rectangle([(CX_VOL - 28, r_mid - 8), (CX_VOL - 8, r_mid + 24)], radius=3, fill=(0, 230, 118))
        draw.rounded_rectangle([(CX_VOL + 12, r_mid - 8), (CX_VOL + 32, r_mid + 24)], radius=3, fill=(235, 50, 50))

        # F. VOLUME RATIO DONUT
        tot_vol = max(1, b_vol + s_vol)
        b_pct = round(b_vol / tot_vol * 100)
        draw_donut_ratio(draw, CX_RATIO, r_mid + 2, 20, b_pct, f_donut)

        # G. DELTA
        delta = b_vol - s_vol
        delta_pct = round((delta / tot_vol) * 100)
        d_sgn = "+" if delta >= 0 else ""
        d_col = (0, 230, 118) if delta >= 0 else (255, 68, 68)
        draw.text((CX_DELTA, r_mid - 14), f"{d_sgn}{delta:,}", fill=d_col, font=f_delta, anchor="ma")
        draw.text((CX_DELTA, r_mid + 6), f"({d_sgn}{delta_pct}%)", fill=d_col, font=f_delta_sub, anchor="ma")

        # H. TREND (Custom vector arrow + text)
        trend = item.get("trend", "UP").upper()
        if "UP" in trend:
            tr_col = (0, 230, 118)
            tr_dir = "UP"
        elif "DOWN" in trend:
            tr_col = (255, 68, 68)
            tr_dir = "DOWN"
        else:
            tr_col = (255, 204, 0)
            tr_dir = "SIDE"
        draw_vector_arrow(draw, CX_TREND, r_mid - 8, tr_dir, tr_col)
        draw.text((CX_TREND, r_mid + 8), tr_dir, fill=tr_col, font=f_trend, anchor="ma")

        # I. STATUS PILL & SUBTITLE
        status = item.get("status", "WAIT").upper()
        status_sub = item.get("status_sub", "Tunggu konfirmasi")
        
        if "BUY" in status:
            st_col = (0, 230, 118)
        elif "REVERSAL" in status:
            st_col = (255, 140, 0)
        elif "SELL" in status or "BREAKDOWN" in status:
            st_col = (255, 68, 68)
        else:
            st_col = (255, 204, 0)

        # Status box (wide container)
        draw.rounded_rectangle([(X_STATUS, r_mid - 24), (X_STATUS + STATUS_W, r_mid + 24)], radius=9, fill=(4, 18, 44), outline=st_col, width=2)
        # Orb indicator
        draw_sphere(draw, X_STATUS + 16, r_mid - 8, 8, st_col)
        # Status text
        draw.text((X_STATUS + 32, r_mid - 16), status, fill=(255, 255, 255), font=f_status)
        # Status subtitle explanation (fits full width)
        draw.text((X_STATUS + 10, r_mid + 5), status_sub[:34], fill=(130, 165, 205), font=f_status_sub)

    # 3. BOTTOM INFORMATION PANEL (Y: 538 to 665)
    draw.line([(14, 536), (W - 14, 536)], fill=(12, 38, 78), width=1)
    
    Y_BTM = 542
    H_BTM = 120

    # Card 1: ZONA %SNR (LOKASI HARGA) [w: 290]
    draw.rounded_rectangle([(16, Y_BTM), (305, Y_BTM + H_BTM)], radius=6, fill=(4, 16, 38), outline=(14, 45, 90), width=1)
    draw.text((24, Y_BTM + 6), "ZONA %SNR (LOKASI HARGA)", fill=(120, 160, 210), font=get_font(9, bold=True))
    # Green Box
    draw.rounded_rectangle([(24, Y_BTM + 24), (105, Y_BTM + 108)], radius=4, fill=(0, 200, 100))
    draw.text((64, Y_BTM + 32), "BUY ZONE\n0% - 20%\nDekat Support", fill=(0, 0, 0), font=get_font(9, bold=True), anchor="ma", align="center")
    # Yellow Box
    draw.rounded_rectangle([(112, Y_BTM + 24), (205, Y_BTM + 108)], radius=4, fill=(255, 204, 0))
    draw.text((158, Y_BTM + 32), "WAIT ZONE\n20% - 80%\nTunggu konfirmasi", fill=(0, 0, 0), font=get_font(9, bold=True), anchor="ma", align="center")
    # Red Box
    draw.rounded_rectangle([(212, Y_BTM + 24), (297, Y_BTM + 108)], radius=4, fill=(235, 50, 50))
    draw.text((254, Y_BTM + 32), "SELL ZONE\n80% - 100%\nDekat Resist", fill=(255, 255, 255), font=get_font(9, bold=True), anchor="ma", align="center")

    # Card 2: LOGIC STATUS (LOKASI + VOLUME) [w: 360]
    draw.rounded_rectangle([(315, Y_BTM), (675, Y_BTM + H_BTM)], radius=6, fill=(4, 16, 38), outline=(14, 45, 90), width=1)
    draw.text((325, Y_BTM + 6), "LOGIC STATUS (LOKASI + VOLUME)", fill=(120, 160, 210), font=get_font(9, bold=True))
    draw.text((330, Y_BTM + 24), "ZONA", fill=(100, 140, 185), font=get_font(8, bold=True))
    draw.text((410, Y_BTM + 24), "BUY > SELL", fill=(0, 200, 100), font=get_font(8, bold=True), anchor="ma")
    draw.text((515, Y_BTM + 24), "SELL > BUY", fill=(235, 50, 50), font=get_font(8, bold=True), anchor="ma")
    draw.text((615, Y_BTM + 24), "VOLUME BALANCED", fill=(255, 204, 0), font=get_font(8, bold=True), anchor="ma")
    
    f_tbl = get_font(8, bold=True)
    draw.text((330, Y_BTM + 44), "0% - 20%", fill=(130, 160, 195), font=f_tbl)
    draw.text((410, Y_BTM + 44), "REVERSAL WATCH", fill=(255, 140, 0), font=f_tbl, anchor="ma")
    draw.text((515, Y_BTM + 44), "SELL PRESSURE", fill=(255, 68, 68), font=f_tbl, anchor="ma")
    draw.text((615, Y_BTM + 44), "WAIT", fill=(255, 204, 0), font=f_tbl, anchor="ma")

    draw.text((330, Y_BTM + 66), "20% - 80%", fill=(130, 160, 195), font=f_tbl)
    draw.text((410, Y_BTM + 66), "UP PRESSURE", fill=(0, 230, 118), font=f_tbl, anchor="ma")
    draw.text((515, Y_BTM + 66), "DOWN PRESSURE", fill=(255, 68, 68), font=f_tbl, anchor="ma")
    draw.text((615, Y_BTM + 66), "WAIT", fill=(255, 204, 0), font=f_tbl, anchor="ma")

    draw.text((330, Y_BTM + 88), "80% - 100%", fill=(130, 160, 195), font=f_tbl)
    draw.text((410, Y_BTM + 88), "BREAKOUT WATCH", fill=(0, 230, 118), font=f_tbl, anchor="ma")
    draw.text((515, Y_BTM + 88), "REVERSAL WATCH", fill=(255, 140, 0), font=f_tbl, anchor="ma")
    draw.text((615, Y_BTM + 88), "WAIT", fill=(255, 204, 0), font=f_tbl, anchor="ma")

    # Card 3: VOLUME INFO [w: 240]
    draw.rounded_rectangle([(685, Y_BTM), (925, Y_BTM + H_BTM)], radius=6, fill=(4, 16, 38), outline=(14, 45, 90), width=1)
    draw.text((695, Y_BTM + 6), "VOLUME INFO", fill=(120, 160, 210), font=get_font(9, bold=True))
    f_info = get_font(9, bold=False)
    draw.text((695, Y_BTM + 28), "Buy Ratio   = Buy Tick / (Buy + Sell)", fill=(140, 175, 215), font=f_info)
    draw.text((695, Y_BTM + 52), "Sell Ratio   = Sell Tick / (Buy + Sell)", fill=(140, 175, 215), font=f_info)
    draw.text((695, Y_BTM + 76), "Delta          = Buy Tick - Sell Tick", fill=(140, 175, 215), font=f_info)

    # Card 4: KETERANGAN LEVEL [w: 250]
    draw.rounded_rectangle([(935, Y_BTM), (1185, Y_BTM + H_BTM)], radius=6, fill=(4, 16, 38), outline=(14, 45, 90), width=1)
    draw.text((945, Y_BTM + 6), "KETERANGAN LEVEL", fill=(120, 160, 210), font=get_font(9, bold=True))
    draw.text((945, Y_BTM + 26), "S            = Support (0%)", fill=(140, 175, 215), font=f_info)
    draw.text((945, Y_BTM + 46), "REV-UP = S + 20% (R - S)", fill=(140, 175, 215), font=f_info)
    draw.text((945, Y_BTM + 66), "REV-DN = S + 80% (R - S)", fill=(140, 175, 215), font=f_info)
    draw.text((945, Y_BTM + 86), "R            = Resistance (100%)", fill=(140, 175, 215), font=f_info)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        im.save(output_path, "PNG", quality=95)
        
    return im

def generate_sr_card_bytes(data_list: list = None, **kwargs) -> bytes:
    """
    Generates the PNG card in memory and returns raw bytes.
    Accepts either data_list (list of dicts) or fallback kwargs for backwards compatibility.
    """
    if data_list is None:
        x_p = kwargs.get("xau_price", 4015.28)
        x_s = kwargs.get("xau_support", 3855.0)
        x_r = kwargs.get("xau_resistance", 4230.0)
        x_st = kwargs.get("xau_status", "WAIT")
        
        j_p = kwargs.get("jpy_price", 158.62)
        j_s = kwargs.get("jpy_support", 156.20)
        j_r = kwargs.get("jpy_resistance", 159.40)
        j_st = kwargs.get("jpy_status", "WAIT")

        data_list = [
            {
                "name": "GOLD", "subtitle": "XAUUSD", "icon_type": "gold",
                "price": x_p, "change_val": 12.50, "change_pct": 0.31, "digits": 2,
                "support": x_s, "resistance": x_r, "buy_tick": 1240, "sell_tick": 980,
                "trend": "UP", "status": x_st, "status_sub": "Net Buy, masih tengah tunggu konfirmasi"
            },
            {
                "name": "EURUSD", "subtitle": "EUR/USD", "icon_type": "eu",
                "price": 1.1248, "change_val": 0.0021, "change_pct": 0.19, "digits": 4,
                "support": 1.1100, "resistance": 1.1320, "buy_tick": 1180, "sell_tick": 1420,
                "trend": "UP", "status": "REVERSAL WATCH", "status_sub": "Dekat resistance, Sell volume dominan"
            },
            {
                "name": "OIL", "subtitle": "WTI CRUDE", "icon_type": "oil",
                "price": 89.42, "change_val": 0.58, "change_pct": 0.65, "digits": 2,
                "support": 87.90, "resistance": 99.10, "buy_tick": 1650, "sell_tick": 1120,
                "trend": "DOWN", "status": "BUY", "status_sub": "Dekat support, Buy volume dominan"
            },
            {
                "name": "USDJPY", "subtitle": "USD/JPY", "icon_type": "japan",
                "price": j_p, "change_val": 0.35, "change_pct": 0.22, "digits": 2,
                "support": j_s, "resistance": j_r, "buy_tick": 1100, "sell_tick": 1350,
                "trend": "UP", "status": j_st, "status_sub": "Net Sell, dekat resistance tunggu konfirmasi"
            }
        ]

    im = render_bloomberg_dashboard_card(data_list)
    buf = io.BytesIO()
    im.save(buf, format="PNG", quality=95)
    return buf.getvalue()

def create_sr_card_image(*args, **kwargs) -> Image.Image:
    """Backwards compatibility alias."""
    raw = generate_sr_card_bytes(**kwargs)
    return Image.open(io.BytesIO(raw))
