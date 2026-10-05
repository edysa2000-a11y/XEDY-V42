import os
import io
import math
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

def get_font(size, bold=True):
    font_names = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahomabd.ttf" if bold else "C:/Windows/Fonts/tahoma.ttf",
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
    draw.ellipse([(cx - h_r, cy - h_r), (cx, cy)], fill=(255, 255, 255, 200))

def draw_flag_icon(draw, cx, cy, r, p_type):
    if p_type == "gold":
        draw_sphere(draw, cx, cy, r, (255, 214, 0))
    elif p_type == "oil":
        draw_sphere(draw, cx, cy, r, (140, 150, 165))
        draw.polygon([(cx, cy - 8), (cx - 5, cy + 4), (cx + 5, cy + 4)], fill=(20, 25, 35))
    elif p_type == "eur":
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(0, 51, 153), outline=(40, 90, 200), width=1)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            sx = int(cx + (r - 5) * math.cos(rad))
            sy = int(cy + (r - 5) * math.sin(rad))
            draw.ellipse([(sx - 1, sy - 1), (sx + 1, sy + 1)], fill=(255, 204, 0))
    elif p_type == "jpy":
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

def draw_donut_ratio(draw, cx, cy, radius, buy_pct, font_inner):
    bbox = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    buy_ang = int(buy_pct * 3.6)
    draw.pieslice(bbox, start=-90, end=-90 + buy_ang, fill=(0, 240, 120))
    draw.pieslice(bbox, start=-90 + buy_ang, end=270, fill=(240, 55, 55))
    inner_r = radius - 6
    draw.ellipse([(cx - inner_r, cy - inner_r), (cx + inner_r, cy + inner_r)], fill=(3, 14, 34))
    draw.text((cx, cy - 5), f"{buy_pct}%", fill=(0, 255, 136), font=font_inner, anchor="mm")
    draw.text((cx, cy + 6), f"{100 - buy_pct}%", fill=(255, 90, 90), font=font_inner, anchor="mm")

def draw_vector_arrow(draw, cx, cy, direction):
    if direction == "UP":
        col = (0, 255, 136)
        draw.line([(cx - 7, cy + 7), (cx + 7, cy - 7)], fill=col, width=3)
        draw.line([(cx - 1, cy - 7), (cx + 7, cy - 7)], fill=col, width=3)
        draw.line([(cx + 7, cy - 7), (cx + 7, cy + 1)], fill=col, width=3)
    elif direction == "DOWN":
        col = (255, 75, 75)
        draw.line([(cx - 7, cy - 7), (cx + 7, cy + 7)], fill=col, width=3)
        draw.line([(cx - 1, cy + 7), (cx + 7, cy + 7)], fill=col, width=3)
        draw.line([(cx + 7, cy + 7), (cx + 7, cy - 1)], fill=col, width=3)
    else:
        col = (255, 214, 0)
        draw.line([(cx - 7, cy), (cx + 7, cy)], fill=col, width=3)
        draw.line([(cx + 2, cy - 5), (cx + 7, cy)], fill=col, width=3)
        draw.line([(cx + 2, cy + 5), (cx + 7, cy)], fill=col, width=3)

def render_bloomberg_dashboard_card(data_list: list, output_path: str = None) -> Image.Image:
    W, H = 1200, 675
    img = Image.new("RGBA", (W, H), (2, 9, 22, 255))
    draw = ImageDraw.Draw(img)

    # Subtle grid lines
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill=(5, 18, 42), width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=(5, 18, 42), width=1)

    # Outer border
    draw.rounded_rectangle([(8, 8), (W - 8, H - 8)], radius=8, outline=(0, 100, 210), width=2)

    # Fonts
    f_hdr = get_font(11, bold=True)
    f_pair = get_font(14, bold=True)
    f_sub = get_font(9, bold=False)
    f_price = get_font(21, bold=True)
    f_chg = get_font(12, bold=True)
    f_chg_pct = get_font(11, bold=False)
    f_lvl_num = get_font(12, bold=True)
    f_snr_tick = get_font(10, bold=True)
    f_zone_box = get_font(9, bold=True)
    f_badge = get_font(11, bold=True)
    f_vol_num = get_font(11, bold=True)
    f_donut = get_font(9, bold=True)
    f_delta = get_font(12, bold=True)
    f_delta_sub = get_font(10, bold=False)
    f_trend = get_font(11, bold=True)
    f_status = get_font(14, bold=True)
    f_status_sub = get_font(9, bold=False)

    # Precise Column Layout Anchors
    X_PAIR = 24
    CX_PRICE = 158
    CX_CHG = 226
    
    # SNR Track (Width = 360px)
    X_BAR_START = 295
    BAR_W = 360
    X_BAR_END = X_BAR_START + BAR_W  # 655
    CX_SUPP = X_BAR_START            # 295 (0%)
    CX_REV_UP = X_BAR_START + 72     # 367 (20%)
    CX_BAR_MID = X_BAR_START + 180   # 475 (50%)
    CX_REV_DN = X_BAR_START + 288    # 583 (80%)
    CX_RES = X_BAR_END               # 655 (100%)

    # Right side stats
    CX_VOL = 724
    CX_RATIO = 804
    CX_DELTA = 874
    CX_TREND = 934
    X_STATUS = 972
    STATUS_W = 212

    # 1. HEADER ROW (Y: 12 to 50)
    HDR_COLOR = (215, 235, 255)
    Y_HDR = 16
    draw.text((X_PAIR + 18, Y_HDR + 4), "PAIR", fill=HDR_COLOR, font=f_hdr)
    draw.text((CX_PRICE, Y_HDR - 5), "LIVE\nPRICE", fill=HDR_COLOR, font=f_hdr, anchor="ma")
    draw.text((CX_CHG, Y_HDR - 5), "CHANGE\n(%)", fill=HDR_COLOR, font=f_hdr, anchor="ma")
    
    draw.text((CX_SUPP, Y_HDR - 5), "SUPPORT\n(S)", fill=(0, 255, 136), font=f_hdr, anchor="ma")
    draw.text((CX_REV_UP, Y_HDR - 5), "REV-UP\n(20%)", fill=(0, 255, 136), font=f_hdr, anchor="ma")
    draw.text((CX_BAR_MID, Y_HDR - 5), "POSITION\n%SNR", fill=(255, 220, 0), font=f_hdr, anchor="ma")
    draw.text((CX_REV_DN, Y_HDR - 5), "REV-DOWN\n(80%)", fill=(255, 80, 80), font=f_hdr, anchor="ma")
    draw.text((CX_RES, Y_HDR - 5), "RESISTANCE\n(R)", fill=(255, 80, 80), font=f_hdr, anchor="ma")
    
    draw.text((CX_VOL, Y_HDR - 5), "TICK VOL\n(BUY / SELL)", fill=HDR_COLOR, font=f_hdr, anchor="ma")
    draw.text((CX_RATIO, Y_HDR - 5), "VOL RATIO\n(B% / S%)", fill=HDR_COLOR, font=f_hdr, anchor="ma")
    draw.text((CX_DELTA, Y_HDR - 5), "DELTA\n(B - S)", fill=HDR_COLOR, font=f_hdr, anchor="ma")
    draw.text((CX_TREND, Y_HDR + 4), "TREND", fill=HDR_COLOR, font=f_hdr, anchor="ma")
    draw.text((X_STATUS + STATUS_W // 2, Y_HDR + 4), "STATUS", fill=HDR_COLOR, font=f_hdr, anchor="ma")

    # Header horizontal line
    draw.line([(14, 52), (W - 14, 52)], fill=(15, 45, 95), width=2)

    # 2. INSTRUMENT ROWS (4 rows)
    ROW_H = 120
    Y_START = 54

    for i, item in enumerate(data_list):
        r_top = Y_START + i * ROW_H
        r_mid = r_top + 60
        
        # Row divider
        if i > 0:
            draw.line([(14, r_top), (W - 14, r_top)], fill=(12, 38, 78), width=1)

        # A. PAIR (Icon + Name + Subtitle)
        draw_flag_icon(draw, X_PAIR + 14, r_mid - 2, 17, item.get("icon_type", "gold"))
        p_name = item["name"]
        p_col = (255, 214, 0) if p_name == "GOLD" else (255, 255, 255)
        draw.text((X_PAIR + 38, r_mid - 19), p_name, fill=p_col, font=f_pair)
        draw.text((X_PAIR + 38, r_mid + 4), item["subtitle"], fill=(150, 195, 250), font=f_sub)

        # B. LIVE PRICE & CHANGE
        p_val = item["price"]
        digits = item.get("digits", 2)
        draw.text((CX_PRICE - 35, r_mid - 19), f"{p_val:,.{digits}f}", fill=(255, 255, 255), font=f_price)
        
        chg = item.get("change_val", item.get("change", 0.0))
        chg_pct = item.get("change_pct", 0.0)
        chg_sgn = "+" if chg >= 0 else ""
        chg_col = (0, 255, 136) if chg >= 0 else (255, 75, 75)
        draw.text((CX_CHG, r_mid - 15), f"{chg_sgn}{chg:.{digits}f}", fill=chg_col, font=f_chg, anchor="ma")
        draw.text((CX_CHG, r_mid + 6), f"({chg_sgn}{chg_pct:.2f}%)", fill=chg_col, font=f_chg_pct, anchor="ma")

        # C. SNR LEVELS & SLIDER BAR
        supp = item["support"]
        res = item["resistance"]
        rev_up = supp + 0.20 * (res - supp)
        rev_dn = supp + 0.80 * (res - supp)

        fmt_s = f"{supp:,.{digits}f}"
        fmt_rup = f"{rev_up:,.{digits}f}"
        fmt_rdn = f"{rev_dn:,.{digits}f}"
        fmt_r = f"{res:,.{digits}f}"

        # Level Prices (At r_top + 10, clear of any floating badge)
        draw.text((CX_SUPP, r_top + 10), fmt_s, fill=(0, 255, 136), font=f_lvl_num, anchor="ma")
        draw.text((CX_REV_UP, r_top + 10), fmt_rup, fill=(0, 255, 136), font=f_lvl_num, anchor="ma")
        draw.text((CX_REV_DN, r_top + 10), fmt_rdn, fill=(255, 75, 75), font=f_lvl_num, anchor="ma")
        draw.text((CX_RES, r_top + 10), fmt_r, fill=(255, 75, 75), font=f_lvl_num, anchor="ma")

        # Track bar Y
        bar_y1 = r_top + 50
        bar_y2 = r_top + 58
        draw_gradient_bar(draw, X_BAR_START, bar_y1, X_BAR_END, bar_y2)

        # Vertical connector tick lines from levels to bar
        draw.line([(CX_SUPP, r_top + 27), (CX_SUPP, bar_y1)], fill=(0, 255, 136), width=1)
        draw.line([(CX_REV_UP, r_top + 27), (CX_REV_UP, bar_y1)], fill=(0, 255, 136), width=1)
        draw.line([(CX_REV_DN, r_top + 27), (CX_REV_DN, bar_y1)], fill=(255, 75, 75), width=1)
        draw.line([(CX_RES, r_top + 27), (CX_RES, bar_y1)], fill=(255, 75, 75), width=1)

        # %SNR Live Pointer Pin & Tooltip
        pct_snr = (p_val - supp) / (res - supp) * 100.0 if res > supp else 50.0
        clamp_pct = max(0.0, min(100.0, pct_snr))
        pin_x = int(X_BAR_START + BAR_W * (clamp_pct / 100.0))

        # Floating %SNR Tooltip badge (Y: r_top + 26 to r_top + 45)
        # Sits in dedicated Y slice between level prices (r_top + 10) and bar (r_top + 50)
        b_txt = f"{pct_snr:.1f}%"
        draw.rounded_rectangle([(pin_x - 22, r_top + 26), (pin_x + 22, r_top + 45)], radius=7, fill=(255, 214, 0))
        draw.text((pin_x, r_top + 28), b_txt, fill=(0, 0, 0), font=f_badge, anchor="mt")

        # Glowing Pin cursor on track
        pin_mid_y = (bar_y1 + bar_y2) // 2
        # Vertical cursor line connecting tooltip to pin
        draw.line([(pin_x, r_top + 45), (pin_x, pin_mid_y)], fill=(255, 214, 0), width=2)
        draw.ellipse([(pin_x - 7, pin_mid_y - 7), (pin_x + 7, pin_mid_y + 7)], fill=(0, 160, 255), outline=(255, 255, 255), width=2)
        draw.ellipse([(pin_x - 4, pin_mid_y - 4), (pin_x + 4, pin_mid_y + 4)], fill=(255, 255, 255))

        # 0%, 20%, 50%, 80%, 100% percentage tick labels below bar
        TICK_COL = (175, 215, 255)
        draw.text((CX_SUPP, bar_y2 + 3), "0%", fill=TICK_COL, font=f_snr_tick, anchor="mt")
        draw.text((CX_REV_UP, bar_y2 + 3), "20%", fill=TICK_COL, font=f_snr_tick, anchor="mt")
        draw.text((CX_BAR_MID, bar_y2 + 3), "50%", fill=TICK_COL, font=f_snr_tick, anchor="mt")
        draw.text((CX_REV_DN, bar_y2 + 3), "80%", fill=TICK_COL, font=f_snr_tick, anchor="mt")
        draw.text((CX_RES, bar_y2 + 3), "100%", fill=TICK_COL, font=f_snr_tick, anchor="mt")

        # Three Zone Boxes below ticks (Bright bold text)
        z_y1 = bar_y2 + 16
        z_y2 = z_y1 + 17
        # Buy Zone (0-20%)
        draw.rounded_rectangle([(X_BAR_START, z_y1), (CX_REV_UP, z_y2)], radius=3, fill=(4, 45, 25), outline=(0, 220, 110), width=1)
        draw.text((X_BAR_START + int((CX_REV_UP - X_BAR_START) * 0.50), z_y1 + 2), "BUY ZONE\n(0% - 20%)", fill=(0, 255, 136), font=f_zone_box, anchor="ma", align="center")
        # Wait Zone (20-80%)
        draw.rounded_rectangle([(CX_REV_UP + 3, z_y1), (CX_REV_DN - 3, z_y2)], radius=3, fill=(45, 38, 12), outline=(220, 180, 0), width=1)
        draw.text((CX_REV_UP + int((CX_REV_DN - CX_REV_UP) * 0.50), z_y1 + 2), "WAIT ZONE\n(20% - 80%)", fill=(255, 225, 0), font=f_zone_box, anchor="ma", align="center")
        # Sell Zone (80-100%)
        draw.rounded_rectangle([(CX_REV_DN, z_y1), (X_BAR_END, z_y2)], radius=3, fill=(55, 16, 24), outline=(240, 50, 60), width=1)
        draw.text((CX_REV_DN + int((X_BAR_END - CX_REV_DN) * 0.50), z_y1 + 2), "SELL ZONE\n(80% - 100%)", fill=(255, 80, 80), font=f_zone_box, anchor="ma", align="center")

        # D. TICK VOLUME (BUY / SELL BARS)
        b_vol = item.get("buy_tick", 1200)
        s_vol = item.get("sell_tick", 1000)
        draw.text((CX_VOL - 16, r_mid - 24), f"{b_vol:,}", fill=(255, 255, 255), font=f_vol_num, anchor="ma")
        draw.text((CX_VOL + 16, r_mid - 24), f"{s_vol:,}", fill=(255, 120, 120), font=f_vol_num, anchor="ma")
        draw.rounded_rectangle([(CX_VOL - 26, r_mid - 8), (CX_VOL - 6, r_mid + 24)], radius=3, fill=(0, 240, 120))
        draw.rounded_rectangle([(CX_VOL + 6, r_mid - 8), (CX_VOL + 26, r_mid + 24)], radius=3, fill=(240, 50, 50))

        # E. VOLUME RATIO DONUT
        tot_vol = max(1, b_vol + s_vol)
        b_pct = round(b_vol / tot_vol * 100)
        draw_donut_ratio(draw, CX_RATIO, r_mid + 2, 21, b_pct, f_donut)

        # F. DELTA
        delta = b_vol - s_vol
        delta_pct = round((delta / tot_vol) * 100)
        d_sgn = "+" if delta >= 0 else ""
        d_col = (0, 255, 136) if delta >= 0 else (255, 75, 75)
        draw.text((CX_DELTA, r_mid - 15), f"{d_sgn}{delta:,}", fill=d_col, font=f_delta, anchor="ma")
        draw.text((CX_DELTA, r_mid + 6), f"({d_sgn}{delta_pct}%)", fill=d_col, font=f_delta_sub, anchor="ma")

        # G. TREND (Custom vector arrow + text)
        trend = item.get("trend", "UP").upper()
        if "UP" in trend:
            tr_col = (0, 255, 136)
            tr_dir = "UP"
        elif "DOWN" in trend:
            tr_col = (255, 75, 75)
            tr_dir = "DOWN"
        else:
            tr_col = (255, 214, 0)
            tr_dir = "SIDE"

        draw_vector_arrow(draw, CX_TREND, r_mid - 12, tr_dir)
        draw.text((CX_TREND, r_mid + 8), tr_dir, fill=tr_col, font=f_trend, anchor="ma")

        # H. STATUS PILL & SUBTITLE
        status = item.get("status", "WAIT").upper()
        status_sub = item.get("status_sub", "Tunggu konfirmasi")
        
        if "BUY" in status:
            st_col = (0, 255, 136)
        elif "REVERSAL" in status:
            st_col = (255, 150, 0)
        elif "SELL" in status or "BREAKDOWN" in status:
            st_col = (255, 75, 75)
        else:
            st_col = (255, 214, 0)

        # Status box (wide container)
        draw.rounded_rectangle([(X_STATUS, r_mid - 25), (X_STATUS + STATUS_W, r_mid + 25)], radius=9, fill=(5, 22, 54), outline=st_col, width=2)
        # Orb indicator
        draw_sphere(draw, X_STATUS + 16, r_mid - 8, 9, st_col)
        # Status text
        draw.text((X_STATUS + 32, r_mid - 17), status, fill=(255, 255, 255), font=f_status)
        # Status subtitle explanation (Full text)
        draw.text((X_STATUS + 10, r_mid + 6), status_sub, fill=(185, 220, 255), font=f_status_sub)

    # 3. BOTTOM INFORMATION PANEL (Y: 536 to 665)
    draw.line([(14, 536), (W - 14, 536)], fill=(15, 45, 95), width=2)
    
    Y_BTM = 542
    H_BTM = 120

    # Card 1: ZONA %SNR (LOKASI HARGA) [w: 275]
    draw.rounded_rectangle([(16, Y_BTM), (290, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(18, 55, 110), width=1)
    draw.text((24, Y_BTM + 6), "ZONA %SNR (LOKASI HARGA)", fill=(210, 235, 255), font=get_font(10, bold=True))
    # Green Box
    draw.rounded_rectangle([(24, Y_BTM + 24), (105, Y_BTM + 108)], radius=4, fill=(0, 220, 110))
    draw.text((64, Y_BTM + 32), "BUY ZONE\n0% - 20%\nDekat Support", fill=(0, 0, 0), font=get_font(10, bold=True), anchor="ma", align="center")
    # Yellow Box
    draw.rounded_rectangle([(112, Y_BTM + 24), (198, Y_BTM + 108)], radius=4, fill=(255, 214, 0))
    draw.text((155, Y_BTM + 32), "WAIT ZONE\n20% - 80%\nTunggu konfirmasi", fill=(0, 0, 0), font=get_font(10, bold=True), anchor="ma", align="center")
    # Red Box
    draw.rounded_rectangle([(205, Y_BTM + 24), (282, Y_BTM + 108)], radius=4, fill=(240, 50, 50))
    draw.text((243, Y_BTM + 32), "SELL ZONE\n80% - 100%\nDekat Resist", fill=(255, 255, 255), font=get_font(10, bold=True), anchor="ma", align="center")

    # Card 2: LOGIC STATUS (LOKASI + VOLUME) [w: 385] (Spacious & zero overlap)
    draw.rounded_rectangle([(298, Y_BTM), (682, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(18, 55, 110), width=1)
    draw.text((308, Y_BTM + 6), "LOGIC STATUS (LOKASI + VOLUME)", fill=(210, 235, 255), font=get_font(10, bold=True))
    
    # Columns in Card 2
    C2_ZONA = 308
    C2_BUY = 422
    C2_SELL = 528
    C2_WAIT = 628

    draw.text((C2_ZONA, Y_BTM + 25), "ZONA", fill=(160, 200, 245), font=get_font(9, bold=True))
    draw.text((C2_BUY, Y_BTM + 25), "BUY > SELL", fill=(0, 255, 136), font=get_font(9, bold=True), anchor="ma")
    draw.text((C2_SELL, Y_BTM + 25), "SELL > BUY", fill=(255, 75, 75), font=get_font(9, bold=True), anchor="ma")
    draw.text((C2_WAIT, Y_BTM + 25), "VOLUME BALANCED", fill=(255, 220, 0), font=get_font(9, bold=True), anchor="ma")
    
    f_tbl = get_font(9, bold=True)
    draw.text((C2_ZONA, Y_BTM + 46), "0% - 20%", fill=(175, 215, 255), font=f_tbl)
    draw.text((C2_BUY, Y_BTM + 46), "REVERSAL WATCH", fill=(255, 160, 0), font=f_tbl, anchor="ma")
    draw.text((C2_SELL, Y_BTM + 46), "SELL PRESSURE", fill=(255, 75, 75), font=f_tbl, anchor="ma")
    draw.text((C2_WAIT, Y_BTM + 46), "WAIT", fill=(255, 220, 0), font=f_tbl, anchor="ma")

    draw.text((C2_ZONA, Y_BTM + 68), "20% - 80%", fill=(175, 215, 255), font=f_tbl)
    draw.text((C2_BUY, Y_BTM + 68), "UP PRESSURE", fill=(0, 255, 136), font=f_tbl, anchor="ma")
    draw.text((C2_SELL, Y_BTM + 68), "DOWN PRESSURE", fill=(255, 75, 75), font=f_tbl, anchor="ma")
    draw.text((C2_WAIT, Y_BTM + 68), "WAIT", fill=(255, 220, 0), font=f_tbl, anchor="ma")

    draw.text((C2_ZONA, Y_BTM + 90), "80% - 100%", fill=(175, 215, 255), font=f_tbl)
    draw.text((C2_BUY, Y_BTM + 90), "BREAKOUT WATCH", fill=(0, 255, 136), font=f_tbl, anchor="ma")
    draw.text((C2_SELL, Y_BTM + 90), "REVERSAL WATCH", fill=(255, 160, 0), font=f_tbl, anchor="ma")
    draw.text((C2_WAIT, Y_BTM + 90), "WAIT", fill=(255, 220, 0), font=f_tbl, anchor="ma")

    # Card 3: VOLUME INFO [w: 242]
    draw.rounded_rectangle([(690, Y_BTM), (930, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(18, 55, 110), width=1)
    draw.text((700, Y_BTM + 6), "VOLUME INFO", fill=(210, 235, 255), font=get_font(10, bold=True))
    f_info = get_font(10, bold=False)
    draw.text((700, Y_BTM + 30), "Buy Ratio   = Buy Tick / (Buy + Sell)", fill=(190, 220, 255), font=f_info)
    draw.text((700, Y_BTM + 55), "Sell Ratio  = Sell Tick / (Buy + Sell)", fill=(190, 220, 255), font=f_info)
    draw.text((700, Y_BTM + 80), "Delta          = Buy Tick - Sell Tick", fill=(190, 220, 255), font=f_info)

    # Card 4: KETERANGAN LEVEL [w: 246]
    draw.rounded_rectangle([(938, Y_BTM), (1184, Y_BTM + H_BTM)], radius=6, fill=(4, 18, 44), outline=(18, 55, 110), width=1)
    draw.text((948, Y_BTM + 6), "KETERANGAN LEVEL", fill=(210, 235, 255), font=get_font(10, bold=True))
    draw.text((948, Y_BTM + 28), "S", fill=(0, 255, 136), font=get_font(10, bold=True))
    draw.text((980, Y_BTM + 28), "= Support (0%)", fill=(190, 220, 255), font=f_info)
    draw.text((948, Y_BTM + 50), "REV-UP", fill=(0, 255, 136), font=get_font(10, bold=True))
    draw.text((1010, Y_BTM + 50), "= S + 20% (R - S)", fill=(190, 220, 255), font=f_info)
    draw.text((948, Y_BTM + 72), "REV-DN", fill=(255, 80, 80), font=get_font(10, bold=True))
    draw.text((1010, Y_BTM + 72), "= S + 80% (R - S)", fill=(190, 220, 255), font=f_info)
    draw.text((948, Y_BTM + 94), "R", fill=(255, 80, 80), font=get_font(10, bold=True))
    draw.text((980, Y_BTM + 94), "= Resistance (100%)", fill=(190, 220, 255), font=f_info)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path, "PNG", optimize=True)

    return img

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
                "name": "EURUSD", "subtitle": "EUR/USD", "icon_type": "eur",
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
                "name": "USDJPY", "subtitle": "USD/JPY", "icon_type": "jpy",
                "price": j_p, "change_val": 0.35, "change_pct": 0.22, "digits": 2,
                "support": j_s, "resistance": j_r, "buy_tick": 1100, "sell_tick": 1350,
                "trend": "UP", "status": j_st, "status_sub": "Net Sell, dekat resistance tunggu konfirmasi"
            }
        ]

    im = render_bloomberg_dashboard_card(data_list)
    buf = io.BytesIO()
    if im.mode == "RGBA":
        rgb_im = Image.new("RGB", im.size, (2, 9, 22))
        rgb_im.paste(im, mask=im.split()[3])
        rgb_im.save(buf, format="PNG", optimize=True)
    else:
        im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

def create_sr_card_image(*args, **kwargs) -> Image.Image:
    """Backwards compatibility alias."""
    raw = generate_sr_card_bytes(**kwargs)
    return Image.open(io.BytesIO(raw))

if __name__ == "__main__":
    test_data = [
        {
            "name": "GOLD", "subtitle": "XAUUSD", "icon_type": "gold",
            "price": 4015.28, "change": 12.50, "change_pct": 0.31,
            "support": 3855.0, "resistance": 4230.0, "digits": 2,
            "buy_tick": 1240, "sell_tick": 980,
            "trend": "UP", "status": "WAIT",
            "status_sub": "Net Buy, masih tengah tunggu konfirmasi"
        },
        {
            "name": "EURUSD", "subtitle": "EUR/USD", "icon_type": "eur",
            "price": 1.1248, "change": 0.0021, "change_pct": 0.19,
            "support": 1.1100, "resistance": 1.1320, "digits": 4,
            "buy_tick": 1180, "sell_tick": 1420,
            "trend": "UP", "status": "REVERSAL WATCH",
            "status_sub": "Dekat resistance, Sell volume dominan"
        },
        {
            "name": "OIL", "subtitle": "WTI CRUDE", "icon_type": "oil",
            "price": 89.42, "change": 0.58, "change_pct": 0.65,
            "support": 87.90, "resistance": 99.10, "digits": 2,
            "buy_tick": 1650, "sell_tick": 1120,
            "trend": "DOWN", "status": "BUY",
            "status_sub": "Dekat support, Buy volume dominan"
        },
        {
            "name": "USDJPY", "subtitle": "USD/JPY", "icon_type": "jpy",
            "price": 158.62, "change": 0.35, "change_pct": 0.22,
            "support": 156.20, "resistance": 159.40, "digits": 2,
            "buy_tick": 1100, "sell_tick": 1350,
            "trend": "UP", "status": "WAIT",
            "status_sub": "Net Sell, dekat resistance tunggu konfirmasi"
        }
    ]

    out_p = "C:/Users/ACER/.gemini/antigravity/brain/558a85bc-66f2-430d-b5c2-57d9b5fa3ae7/test_bloomberg_flawless.png"
    render_bloomberg_dashboard_card(test_data, out_p)
    print("Rendered flawless:", out_p)
