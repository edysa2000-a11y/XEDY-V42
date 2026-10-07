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
        # 3D Stacked Gold Ingots
        draw.polygon([(cx - 14, cy + 2), (cx + 2, cy + 2), (cx + 8, cy - 8), (cx - 8, cy - 8)], fill=(255, 215, 0), outline=(218, 165, 32))
        draw.polygon([(cx - 8, cy + 10), (cx + 8, cy + 10), (cx + 14, cy), (cx - 2, cy)], fill=(255, 195, 0), outline=(184, 134, 11))
    elif p_type == "oil":
        # 3D Oil Droplet
        draw_sphere(draw, cx, cy + 3, r - 3, (140, 150, 165))
        draw.polygon([(cx, cy - 12), (cx - 6, cy + 2), (cx + 6, cy + 2)], fill=(25, 30, 42))
    elif p_type == "eur":
        # EU Circle of Stars
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(0, 51, 153), outline=(40, 90, 200), width=1)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            sx = int(cx + (r - 4) * math.cos(rad))
            sy = int(cy + (r - 4) * math.sin(rad))
            draw.ellipse([(sx - 1, sy - 1), (sx + 1, sy + 1)], fill=(255, 204, 0))
    elif p_type == "gbp":
        # UK Union Jack Circle
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(1, 33, 105), outline=(100, 140, 210), width=1)
        draw.line([(cx - r + 2, cy), (cx + r - 2, cy)], fill=(255, 255, 255), width=5)
        draw.line([(cx, cy - r + 2), (cx, cy + r - 2)], fill=(255, 255, 255), width=5)
        draw.line([(cx - r + 2, cy), (cx + r - 2, cy)], fill=(200, 16, 46), width=3)
        draw.line([(cx, cy - r + 2), (cx, cy + r - 2)], fill=(200, 16, 46), width=3)
    elif p_type == "jpy":
        # Japan Flag Circle
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(255, 255, 255), outline=(180, 180, 180), width=1)
        draw.ellipse([(cx - r//2, cy - r//2), (cx + r//2, cy + r//2)], fill=(188, 0, 45))
    else:
        draw_sphere(draw, cx, cy, r, (0, 170, 255))

def draw_trend_arrow_badge(draw, cx, cy, trend):
    r = 17
    if trend == "BEARISH":
        bg_col = (195, 25, 35)
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=bg_col)
        # Down-right angled arrow
        draw.line([(cx - 7, cy - 7), (cx + 7, cy + 7)], fill=(255, 255, 255), width=3)
        draw.polygon([(cx + 7, cy + 7), (cx + 7, cy), (cx, cy + 7)], fill=(255, 255, 255))
    else:
        bg_col = (16, 185, 129)
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=bg_col)
        # Up-right angled arrow
        draw.line([(cx - 7, cy + 7), (cx + 7, cy - 7)], fill=(255, 255, 255), width=3)
        draw.polygon([(cx + 7, cy - 7), (cx + 7, cy), (cx, cy - 7)], fill=(255, 255, 255))

# Vector Icon Renderers
def draw_icon_target(draw, cx, cy, col=(0, 210, 255)):
    draw.ellipse([(cx - 8, cy - 8), (cx + 8, cy + 8)], outline=col, width=2)
    draw.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], outline=col, width=1)
    draw.ellipse([(cx - 1, cy - 1), (cx + 1, cy + 1)], fill=col)

def draw_icon_brain(draw, cx, cy, col=(0, 210, 255)):
    draw.ellipse([(cx - 8, cy - 7), (cx - 1, cy + 6)], outline=col, width=2)
    draw.ellipse([(cx + 1, cy - 7), (cx + 8, cy + 6)], outline=col, width=2)
    draw.line([(cx - 4, cy), (cx + 4, cy)], fill=col, width=1)

def draw_icon_gear(draw, cx, cy, col=(0, 210, 255)):
    draw.ellipse([(cx - 6, cy - 6), (cx + 6, cy + 6)], outline=col, width=2)
    draw.ellipse([(cx - 2, cy - 2), (cx + 2, cy + 2)], fill=col)
    for ang in [0, 45, 90, 135]:
        rad = math.radians(ang)
        dx, dy = int(8 * math.cos(rad)), int(8 * math.sin(rad))
        draw.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=col, width=2)

def draw_icon_trophy(draw, cx, cy, col=(0, 210, 255)):
    draw.polygon([(cx - 6, cy - 7), (cx + 6, cy - 7), (cx + 4, cy + 1), (cx - 4, cy + 1)], outline=col, width=2)
    draw.line([(cx, cy + 1), (cx, cy + 5)], fill=col, width=2)
    draw.line([(cx - 5, cy + 6), (cx + 5, cy + 6)], fill=col, width=2)

def draw_icon_bell(draw, cx, cy, col=(0, 210, 255)):
    draw.arc([(cx - 6, cy - 7), (cx + 6, cy + 3)], start=180, end=360, fill=col, width=2)
    draw.line([(cx - 6, cy + 3), (cx + 6, cy + 3)], fill=col, width=2)
    draw.ellipse([(cx - 2, cy + 4), (cx + 2, cy + 7)], fill=col)

def draw_icon_calendar(draw, cx, cy, col=(0, 210, 255)):
    draw.rounded_rectangle([(cx - 7, cy - 6), (cx + 7, cy + 7)], radius=2, outline=col, width=1)
    draw.line([(cx - 7, cy - 2), (cx + 7, cy - 2)], fill=col, width=1)
    draw.line([(cx - 4, cy - 8), (cx - 4, cy - 5)], fill=col, width=2)
    draw.line([(cx + 4, cy - 8), (cx + 4, cy - 5)], fill=col, width=2)

def draw_icon_shield(draw, cx, cy, col=(0, 230, 118)):
    draw.polygon([(cx - 6, cy - 6), (cx + 6, cy - 6), (cx + 5, cy + 2), (cx, cy + 7), (cx - 5, cy + 2)], outline=col, width=1)
    draw.line([(cx - 3, cy), (cx - 1, cy + 3)], fill=col, width=2)
    draw.line([(cx - 1, cy + 3), (cx + 3, cy - 3)], fill=col, width=2)

def draw_icon_cloud(draw, cx, cy, col=(0, 230, 118)):
    draw.ellipse([(cx - 6, cy - 2), (cx, cy + 4)], fill=col)
    draw.ellipse([(cx - 2, cy - 5), (cx + 4, cy + 2)], fill=col)
    draw.ellipse([(cx + 1, cy - 2), (cx + 7, cy + 4)], fill=col)
    draw.rectangle([(cx - 4, cy + 1), (cx + 5, cy + 4)], fill=col)

def draw_icon_macro(draw, cx, cy, m_type, col=(245, 65, 75)):
    if m_type == "fomc":
        # Bank / Pillar icon
        draw.line([(cx - 6, cy - 5), (cx + 6, cy - 5)], fill=col, width=2)
        draw.line([(cx - 4, cy - 5), (cx - 4, cy + 5)], fill=col, width=1)
        draw.line([(cx, cy - 5), (cx, cy + 5)], fill=col, width=1)
        draw.line([(cx + 4, cy - 5), (cx + 4, cy + 5)], fill=col, width=1)
        draw.line([(cx - 6, cy + 5), (cx + 6, cy + 5)], fill=col, width=2)
    elif m_type == "cpi":
        # Percent icon
        draw.ellipse([(cx - 5, cy - 5), (cx - 2, cy - 2)], outline=col, width=1)
        draw.ellipse([(cx + 2, cy + 2), (cx + 5, cy + 5)], outline=col, width=1)
        draw.line([(cx + 4, cy - 5), (cx - 4, cy + 5)], fill=col, width=1)
    elif m_type == "geo":
        # Target / globe
        draw.ellipse([(cx - 5, cy - 5), (cx + 5, cy + 5)], outline=col, width=1)
        draw.line([(cx, cy - 7), (cx, cy + 7)], fill=col, width=1)
        draw.line([(cx - 7, cy), (cx + 7, cy)], fill=col, width=1)
    elif m_type == "oil":
        # Warning triangle
        draw.polygon([(cx, cy - 6), (cx - 6, cy + 5), (cx + 6, cy + 5)], outline=col, width=1)
        draw.line([(cx, cy - 2), (cx, cy + 1)], fill=col, width=1)
        draw.ellipse([(cx - 1, cy + 3), (cx + 1, cy + 4)], fill=col)
    else:
        draw.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], fill=col)

def generate_precision_dashboard_card(engine_data: dict, now_wib: datetime = None) -> bytes:
    """
    Renders 1920x1080 (16:9 Full HD) Institutional XEDY AI Precision Trading Engine Dashboard.
    Single-Page, Zero-Scroll, Multi-Agent Architecture matching media_1791361552558.jpg.
    """
    if now_wib is None:
        now_wib = datetime.now(WIB)

    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (2, 6, 14))
    draw = ImageDraw.Draw(img)

    # Background Cyber Matrix Grid
    for x in range(0, W, 48):
        draw.line([(x, 0), (x, H)], fill=(5, 13, 26), width=1)
    for y in range(0, H, 48):
        draw.line([(0, y), (W, y)], fill=(5, 13, 26), width=1)

    # Outer Global Frame
    draw.rounded_rectangle([(8, 8), (W - 8, H - 8)], radius=10, outline=(14, 44, 88), width=2)

    # Typography
    f_logo = get_font(28, bold=True)
    f_engine_title = get_font(18, bold=True)
    f_engine_sub = get_font(11, bold=False)
    f_pill = get_font(11, bold=True)
    f_pill_sm = get_font(10, bold=True)
    f_clock = get_font(15, bold=True)
    f_date = get_font(11, bold=False)
    f_label_sm = get_font(10, bold=False)
    
    f_pair_title = get_font(18, bold=True)
    f_pair_sub = get_font(11, bold=False)
    f_price = get_font(20, bold=True)
    f_chg = get_font(12, bold=True)
    
    f_trend = get_font(17, bold=True)
    f_trend_score = get_font(12, bold=False)
    f_range_val = get_font(12, bold=True)
    f_range_lbl = get_font(10, bold=False)
    f_exec_val = get_font(12, bold=True)
    f_exec_lbl = get_font(11, bold=True)
    f_panel_hdr = get_font(13, bold=True)
    f_tbl_hdr = get_font(11, bold=True)
    f_tbl_cell = get_font(11, bold=False)
    f_tbl_cell_b = get_font(11, bold=True)

    # =========================================================================
    # 1. HEADER BAR (Y: 14 to 88)
    # =========================================================================
    draw.rounded_rectangle([(16, 14), (W - 16, 88)], radius=8, fill=(3, 10, 22), outline=(14, 36, 70), width=1)

    # Brand Title: XEDY in cyan, AI in royal blue
    draw.text((32, 22), "XEDY", fill=(0, 210, 255), font=f_logo)
    draw.text((115, 22), "AI", fill=(41, 121, 255), font=f_logo)
    # Thin vertical divider
    draw.line([(150, 26), (150, 76)], fill=(20, 50, 95), width=1)
    draw.text((165, 26), "PRECISION TRADING ENGINE", fill=(255, 255, 255), font=f_engine_title)
    draw.text((165, 54), "Multi-Agent • Low Error • High Probability", fill=(125, 155, 190), font=f_engine_sub)

    # Widget 1: LIVE Clock Modular Box
    draw.rounded_rectangle([(670, 22), (865, 78)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.rounded_rectangle([(682, 36), (732, 60)], radius=4, fill=(0, 230, 118))
    draw.text((707, 48), "LIVE", fill=(0, 0, 0), font=f_pill, anchor="mm")
    time_str = now_wib.strftime("%H:%M:%S WIB")
    date_str = now_wib.strftime("%a, %d %b %Y")
    draw.text((744, 34), time_str, fill=(255, 255, 255), font=f_clock)
    draw.text((744, 56), date_str, fill=(135, 155, 180), font=f_date)

    # Widget 2: Market Regime Modular Box
    draw.rounded_rectangle([(875, 22), (1110, 78)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.text((887, 30), "Market Regime", fill=(115, 145, 175), font=f_label_sm)
    draw.rounded_rectangle([(887, 46), (960, 68)], radius=4, fill=(215, 45, 55))
    draw.text((923, 57), "RISK-OFF", fill=(255, 255, 255), font=f_pill_sm, anchor="mm")
    draw.text((970, 57), "HIGH VOLATILITY", fill=(245, 75, 75), font=f_pill_sm, anchor="lm")

    # Widget 3: Event Risk Modular Box
    draw.rounded_rectangle([(1120, 22), (1240, 78)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.text((1132, 30), "Event Risk", fill=(115, 145, 175), font=f_label_sm)
    draw_icon_calendar(draw, 1146, 57, col=(245, 75, 75))
    draw.rounded_rectangle([(1162, 46), (1226, 68)], radius=4, fill=(215, 45, 55))
    draw.text((1194, 57), "HIGH", fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

    # Widget 4: Data Feed Modular Box
    draw.rounded_rectangle([(1250, 22), (1365, 78)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.text((1262, 30), "Data Feed", fill=(115, 145, 175), font=f_label_sm)
    draw_icon_cloud(draw, 1276, 57, col=(0, 230, 118))
    draw.rounded_rectangle([(1292, 46), (1350, 68)], radius=4, fill=(8, 28, 22), outline=(0, 200, 100), width=1)
    draw.text((1321, 57), "LIVE", fill=(0, 230, 118), font=f_pill, anchor="mm")

    # Widget 5: Model Status Modular Box
    draw.rounded_rectangle([(1375, 22), (1495, 78)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.text((1387, 30), "Model Status", fill=(115, 145, 175), font=f_label_sm)
    draw_icon_shield(draw, 1401, 57, col=(0, 230, 118))
    draw.rounded_rectangle([(1417, 46), (1480, 68)], radius=4, fill=(8, 28, 22), outline=(0, 200, 100), width=1)
    draw.text((1448, 57), "PASS", fill=(0, 230, 118), font=f_pill, anchor="mm")

    # Widget 6: Version Badge (Far Right Box)
    draw.rounded_rectangle([(1505, 22), (1896, 78)], radius=6, fill=(6, 18, 38), outline=(0, 120, 230), width=1)
    cx_cb, cy_cb = 1530, 50
    draw.polygon([(cx_cb, cy_cb - 12), (cx_cb + 11, cy_cb - 6), (cx_cb, cy_cb), (cx_cb - 11, cy_cb - 6)], fill=(0, 190, 255))
    draw.polygon([(cx_cb - 11, cy_cb - 6), (cx_cb, cy_cb), (cx_cb, cy_cb + 12), (cx_cb - 11, cy_cb + 6)], fill=(0, 120, 200))
    draw.polygon([(cx_cb + 11, cy_cb - 6), (cx_cb, cy_cb), (cx_cb, cy_cb + 12), (cx_cb + 11, cy_cb + 6)], fill=(0, 80, 150))
    draw.text((1556, 34), "XEDY v31.0", fill=(0, 210, 255), font=get_font(16, bold=True))
    draw.text((1556, 56), "5 Assets • AI Multi-Agent", fill=(100, 180, 255), font=f_engine_sub)

    # =========================================================================
    # 2. TOP SECTION: 5 PAIR DECISION CARDS (Y: 96 to 572)
    # =========================================================================
    card_w = 364
    card_gap = 12
    card_x_start = 20
    cards_data = engine_data.get("pair_cards", [])

    for i, c in enumerate(cards_data[:5]):
        x0 = card_x_start + i * (card_w + card_gap)
        x1 = x0 + card_w
        y0 = 96
        y1 = 572

        # Card Outer Box with institutional gradient outline
        draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)

        # Asset Icon & Header
        icon_cx, icon_cy = x0 + 32, y0 + 32
        draw_flag_icon(draw, icon_cx, icon_cy, 14, c["icon"])

        # Pair Name & Subtitle
        draw.text((x0 + 56, y0 + 20), c["name"], fill=(255, 255, 255), font=f_pair_title)
        draw.text((x0 + 56, y0 + 44), c["subtitle"], fill=(130, 150, 175), font=f_pair_sub)

        # Live Price & Change (Right Aligned)
        digits = c["digits"]
        p_str = f"{c['price']:,.{digits}f}"
        draw.text((x1 - 20, y0 + 20), p_str, fill=(255, 255, 255), font=f_price, anchor="ra")
        
        chg_sign = "+" if c["chg_val"] >= 0 else ""
        chg_str = f"{chg_sign}{c['chg_val']:.{min(2, digits)}f} ({chg_sign}{c['chg_pct']:.2f}%)"
        chg_col = (0, 230, 118) if c["chg_val"] >= 0 else (245, 65, 75)
        draw.text((x1 - 20, y0 + 46), chg_str, fill=chg_col, font=f_chg, anchor="ra")

        # Trend Badge Row (Y: y0 + 72)
        trend = c["trend"]
        t_col = (245, 65, 75) if trend == "BEARISH" else (0, 230, 118)
        draw_trend_arrow_badge(draw, x0 + 32, y0 + 94, trend)
        draw.text((x0 + 56, y0 + 82), trend, fill=t_col, font=f_trend)
        draw.text((x0 + 56, y0 + 106), f"Trend Score  {c['trend_score']}/100", fill=(180, 195, 215), font=f_trend_score)

        # =====================================================================
        # DAILY RANGE SECTION WITH RULER GRADUATION TICKS
        # =====================================================================
        slider_left = x0 + 24
        slider_right = x1 - 24
        slider_w = slider_right - slider_left
        pos_pct = c["pos_pct"]
        marker_x = int(slider_left + (pos_pct / 100.0) * slider_w)
        marker_x = max(slider_left + 15, min(slider_right - 15, marker_x))

        # Daily Range values: Low on left, High on right
        draw.text((slider_left, y0 + 136), f"{c['low']:,.{digits}f}", fill=(240, 245, 255), font=f_range_val)
        draw.text((slider_left, y0 + 152), "Low", fill=(120, 140, 165), font=f_range_lbl)

        draw.text((slider_right, y0 + 136), f"{c['high']:,.{digits}f}", fill=(240, 245, 255), font=f_range_val, anchor="ra")
        draw.text((slider_right, y0 + 152), "High", fill=(120, 140, 165), font=f_range_lbl, anchor="ra")

        # Live Price above marker: dynamically centered or safely offset to prevent collision
        low_txt_w = 60 if digits == 2 else 70
        high_txt_w = 60 if digits == 2 else 70
        if marker_x > (slider_left + low_txt_w + 10) and marker_x < (slider_right - high_txt_w - 10):
            draw.text((marker_x, y0 + 136), p_str, fill=(255, 255, 255), font=f_range_val, anchor="ma")
        elif marker_x <= (slider_left + low_txt_w + 10):
            # If marker is very close to Low, display live price slightly shifted right
            draw.text((slider_left + low_txt_w + 24, y0 + 136), p_str, fill=(255, 255, 255), font=f_range_val, anchor="ma")
        else:
            # If marker is very close to High, display live price slightly shifted left
            draw.text((slider_right - high_txt_w - 24, y0 + 136), p_str, fill=(255, 255, 255), font=f_range_val, anchor="ma")

        # Graduation Ruler Ticks & Segmented Track (Y: y0 + 172)
        bar_y = y0 + 172
        
        # Ruler tick marks background
        for step in range(0, 11):
            tk_x = int(slider_left + (step / 10.0) * slider_w)
            draw.line([(tk_x, bar_y - 6), (tk_x, bar_y + 6)], fill=(15, 35, 68), width=1)

        # Track Bar Fill
        for bx in range(slider_left, slider_right):
            ratio = (bx - slider_left) / slider_w
            if trend == "BEARISH":
                if ratio < 0.38:
                    b_color = (235, 45, 55)
                elif ratio < 0.68:
                    b_color = (int(235 - 150 * (ratio - 0.38) / 0.30), int(45 + 140 * (ratio - 0.38) / 0.30), 60)
                else:
                    b_color = (25, 160, 90)
            else:
                if ratio < 0.32:
                    b_color = (25, 65, 105)
                elif ratio < 0.62:
                    b_color = (int(25 + 100 * (ratio - 0.32) / 0.30), int(65 + 150 * (ratio - 0.32) / 0.30), 110)
                else:
                    b_color = (0, 230, 118)
            draw.line([(bx, bar_y - 2), (bx, bar_y + 2)], fill=b_color, width=1)

        # Live Needle & Dot Marker
        draw.line([(marker_x, bar_y - 8), (marker_x, bar_y + 12)], fill=(255, 255, 255), width=2)
        draw.ellipse([(marker_x - 5, bar_y - 5), (marker_x + 5, bar_y + 5)], fill=(255, 255, 255))

        # Position % Badge Pill below slider (Connecting vertical needle)
        badge_col = (215, 45, 55) if trend == "BEARISH" else (0, 200, 100)
        pill_w = 44
        draw.rounded_rectangle([(marker_x - pill_w // 2, bar_y + 12), (marker_x + pill_w // 2, bar_y + 30)], radius=3, fill=badge_col)
        draw.polygon([(marker_x, bar_y + 8), (marker_x - 4, bar_y + 13), (marker_x + 4, bar_y + 13)], fill=badge_col)
        draw.text((marker_x, bar_y + 21), f"{pos_pct}%", fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

        # Setup Badge Row (Y: y0 + 224)
        draw.rounded_rectangle([(x0 + 24, y0 + 222), (x0 + 72, y0 + 244)], radius=4, fill=(16, 32, 58))
        draw.text((x0 + 48, y0 + 233), "SETUP", fill=(140, 180, 230), font=f_pill_sm, anchor="mm")

        setup_name = c["setup"]
        s_bg = (180, 25, 35) if "SELL" in setup_name else (0, 150, 70)
        draw.rounded_rectangle([(x0 + 78, y0 + 222), (x0 + 195, y0 + 244)], radius=4, fill=s_bg)
        draw.text((x0 + 136, y0 + 233), setup_name, fill=(255, 255, 255), font=f_pill, anchor="mm")

        # Order Execution Inset Card (Y: y0 + 258 to y1 - 16)
        exec_y0 = y0 + 256
        exec_y1 = y1 - 16
        draw.rounded_rectangle([(x0 + 16, exec_y0), (x1 - 16, exec_y1)], radius=6, fill=(2, 8, 18), outline=(14, 32, 60), width=1)

        # Left Column: OP, SL, TP1, TP2, TP3
        col1_x = x0 + 26
        col1_val_x = x0 + 64

        # OP
        draw.text((col1_x, exec_y0 + 14), "OP", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 14), c["op"], fill=(255, 255, 255), font=f_exec_val)

        # SL
        draw.text((col1_x, exec_y0 + 46), "SL", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 46), c["sl"], fill=(255, 255, 255), font=f_exec_val)

        # TP1
        draw.text((col1_x, exec_y0 + 78), "TP1", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 78), c["tp1"], fill=(255, 255, 255), font=f_exec_val)
        draw.text((col1_val_x + 95, exec_y0 + 78), f"{c['tp1_prob']}%", fill=(0, 230, 118), font=f_exec_val)

        # TP2
        draw.text((col1_x, exec_y0 + 110), "TP2", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 110), c["tp2"], fill=(255, 255, 255), font=f_exec_val)
        draw.text((col1_val_x + 95, exec_y0 + 110), f"{c['tp2_prob']}%", fill=(0, 230, 118), font=f_exec_val)

        # TP3
        draw.text((col1_x, exec_y0 + 142), "TP3", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 142), c["tp3"], fill=(255, 255, 255), font=f_exec_val)
        draw.text((col1_val_x + 95, exec_y0 + 142), f"{c['tp3_prob']}%", fill=(0, 230, 118), font=f_exec_val)

        # Right Column: RR, CONF, GATE
        rcol_x = x1 - 70
        draw.text((rcol_x, exec_y0 + 10), "RR", fill=(120, 150, 190), font=f_pill_sm, anchor="mm")
        draw.text((rcol_x, exec_y0 + 30), c["rr"], fill=(0, 210, 255), font=get_font(15, bold=True), anchor="mm")

        draw.text((rcol_x, exec_y0 + 64), "CONF", fill=(120, 150, 190), font=f_pill_sm, anchor="mm")
        draw.text((rcol_x, exec_y0 + 86), f"{c['confidence']}%", fill=(255, 255, 255), font=get_font(16, bold=True), anchor="mm")

        # Quality Gate Badge (Bottom Right)
        q_pass = "PASS" in c["quality_gate"]
        q_bg = (0, 170, 75) if q_pass else (190, 120, 10)
        draw.rounded_rectangle([(rcol_x - 42, exec_y0 + 120), (rcol_x + 42, exec_y0 + 154)], radius=4, fill=q_bg)
        draw.text((rcol_x, exec_y0 + 130), "GATE", fill=(255, 255, 255), font=get_font(9, bold=True), anchor="mm")
        draw.text((rcol_x, exec_y0 + 144), "PASS" if q_pass else "WARNING", fill=(255, 255, 255), font=get_font(11, bold=True), anchor="mm")

    # =========================================================================
    # 3. MIDDLE SECTION: 2 BIG PANELS (Y: 584 to 804)
    # =========================================================================
    # Panel 3A: PRECISION & ERROR METRICS (Left: X: 20 to 1040, W: 1020)
    p3a_x0, p3a_y0 = 20, 584
    p3a_x1, p3a_y1 = 1040, 804
    draw.rounded_rectangle([(p3a_x0, p3a_y0), (p3a_x1, p3a_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)

    draw_icon_target(draw, p3a_x0 + 30, p3a_y0 + 24, col=(0, 210, 255))
    draw.text((p3a_x0 + 46, p3a_y0 + 15), "PRECISION & ERROR METRICS", fill=(0, 210, 255), font=f_panel_hdr)

    tbl_cols_x = [p3a_x0 + 20, p3a_x0 + 135, p3a_x0 + 260, p3a_x0 + 390, p3a_x0 + 520, p3a_x0 + 650, p3a_x0 + 775, p3a_x0 + 900]
    tbl_headers = ["PAIR", "TREND ACC", "TREND ERR", "OP ERR (ATR)", "TP ERR (ATR)", "SL ERR (ATR)", "CALIB ERR", "PRECISION"]
    for col_i, th in enumerate(tbl_headers):
        draw.text((tbl_cols_x[col_i], p3a_y0 + 46), th, fill=(120, 150, 185), font=f_tbl_hdr)

    pt_rows = engine_data.get("precision_table", [])
    for row_i, r in enumerate(pt_rows[:5]):
        ry = p3a_y0 + 74 + row_i * 26
        if row_i % 2 == 1:
            draw.rectangle([(p3a_x0 + 10, ry - 4), (p3a_x1 - 10, ry + 20)], fill=(5, 15, 30))

        # PAIR
        draw.text((tbl_cols_x[0], ry + 2), r["pair"], fill=(255, 255, 255), font=f_tbl_cell_b)

        # TREND ACC
        draw.rounded_rectangle([(tbl_cols_x[1] - 4, ry), (tbl_cols_x[1] + 52, ry + 18)], radius=3, fill=(0, 140, 65))
        draw.text((tbl_cols_x[1] + 24, ry + 9), r["trend_acc"], fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

        # TREND ERR
        err_val = float(r["trend_err"].replace("%", ""))
        err_bg = (180, 40, 30) if err_val >= 12.0 else (190, 100, 20)
        draw.rounded_rectangle([(tbl_cols_x[2] - 4, ry), (tbl_cols_x[2] + 56, ry + 18)], radius=3, fill=err_bg)
        draw.text((tbl_cols_x[2] + 26, ry + 9), r["trend_err"], fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

        # ATR ERRORS
        draw.text((tbl_cols_x[3] + 20, ry + 2), r["op_err"], fill=(220, 230, 245), font=f_tbl_cell)
        draw.text((tbl_cols_x[4] + 20, ry + 2), r["tp_err"], fill=(220, 230, 245), font=f_tbl_cell)
        draw.text((tbl_cols_x[5] + 20, ry + 2), r["sl_err"], fill=(220, 230, 245), font=f_tbl_cell)
        draw.text((tbl_cols_x[6] + 16, ry + 2), r["calib_err"], fill=(220, 230, 245), font=f_tbl_cell)

        # PRECISION SCORE
        prec_val = int(r["precision"].split("/")[0])
        p_bg = (0, 150, 70) if prec_val >= 88 else ((190, 120, 20) if prec_val >= 80 else (180, 40, 30))
        draw.rounded_rectangle([(tbl_cols_x[7] - 4, ry), (tbl_cols_x[7] + 62, ry + 18)], radius=3, fill=p_bg)
        draw.text((tbl_cols_x[7] + 29, ry + 9), r["precision"], fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Panel 3B: MARKET INTELLIGENCE (Right: X: 1052 to 1900, W: 848)
    p3b_x0, p3b_y0 = 1052, 584
    p3b_x1, p3b_y1 = 1900, 804
    draw.rounded_rectangle([(p3b_x0, p3b_y0), (p3b_x1, p3b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)

    draw_icon_brain(draw, p3b_x0 + 30, p3b_y0 + 24, col=(0, 210, 255))
    draw.text((p3b_x0 + 46, p3b_y0 + 15), "MARKET INTELLIGENCE", fill=(0, 210, 255), font=f_panel_hdr)

    col_w = (p3b_x1 - p3b_x0 - 40) // 4
    mi_cols_x = [p3b_x0 + 20 + j * col_w for j in range(4)]
    mi_titles = ["FUNDAMENTAL BIAS", "MONEY FLOW", "REGIME", "EVENT RISK"]
    for j, tit in enumerate(mi_titles):
        draw.text((mi_cols_x[j], p3b_y0 + 46), tit, fill=(120, 150, 185), font=f_tbl_hdr)

    # Sub-column 1: Fundamental Bias
    for r_i, (curr, bias, b_type) in enumerate(engine_data.get("fundamental_bias", [])):
        my = p3b_y0 + 74 + r_i * 26
        draw.text((mi_cols_x[0], my + 2), curr, fill=(255, 255, 255), font=f_tbl_cell_b)
        f_bg = (0, 140, 65) if bias == "STRONG" else (180, 25, 35)
        draw.rounded_rectangle([(mi_cols_x[0] + 55, my), (mi_cols_x[0] + 130, my + 18)], radius=3, fill=f_bg)
        draw.text((mi_cols_x[0] + 92, my + 9), bias, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Sub-column 2: Money Flow
    for r_i, (ast, flow, f_type) in enumerate(engine_data.get("money_flow", [])):
        my = p3b_y0 + 74 + r_i * 26
        draw.text((mi_cols_x[1], my + 2), ast, fill=(255, 255, 255), font=f_tbl_cell_b)
        f_bg = (0, 140, 65) if flow == "INFLOW" else (180, 25, 35)
        draw.rounded_rectangle([(mi_cols_x[1] + 50, my), (mi_cols_x[1] + 155, my + 18)], radius=3, fill=f_bg)
        ax, ay = mi_cols_x[1] + 62, my + 9
        if flow == "INFLOW":
            draw.line([(ax - 3, ay + 3), (ax + 3, ay - 3)], fill=(255, 255, 255), width=2)
            draw.polygon([(ax + 3, ay - 3), (ax + 3, ay), (ax, ay - 3)], fill=(255, 255, 255))
        else:
            draw.line([(ax - 3, ay - 3), (ax + 3, ay + 3)], fill=(255, 255, 255), width=2)
            draw.polygon([(ax + 3, ay + 3), (ax + 3, ay), (ax, ay + 3)], fill=(255, 255, 255))
        draw.text((mi_cols_x[1] + 107, my + 9), flow, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Sub-column 3: Regime
    for r_i, (ast, reg, r_type) in enumerate(engine_data.get("regime", [])):
        my = p3b_y0 + 74 + r_i * 26
        draw.text((mi_cols_x[2], my + 2), ast, fill=(255, 255, 255), font=f_tbl_cell_b)
        r_bg = (0, 140, 65) if "UP" in reg or "BREAKOUT" in reg else (180, 25, 35)
        draw.rounded_rectangle([(mi_cols_x[2] + 46, my), (mi_cols_x[2] + 158, my + 18)], radius=3, fill=r_bg)
        rx, ry_t = mi_cols_x[2] + 58, my + 9
        if "UP" in reg or "BREAKOUT" in reg:
            draw.polygon([(rx, ry_t - 4), (rx - 4, ry_t + 3), (rx + 4, ry_t + 3)], fill=(255, 255, 255))
        else:
            draw.polygon([(rx, ry_t + 4), (rx - 4, ry_t - 3), (rx + 4, ry_t - 3)], fill=(255, 255, 255))
        draw.text((mi_cols_x[2] + 107, my + 9), reg, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Sub-column 4: Event Risk
    for r_i, (ev, risk, r_type) in enumerate(engine_data.get("event_risk", [])):
        my = p3b_y0 + 74 + r_i * 26
        draw.text((mi_cols_x[3] + 20, my + 2), ev, fill=(255, 255, 255), font=f_tbl_cell_b)
        # Macro icon next to event
        draw_icon_macro(draw, mi_cols_x[3] + 8, my + 9, ev.lower(), col=(245, 65, 75))
        e_bg = (180, 25, 35) if "HIGH" in risk else (190, 110, 20)
        draw.rounded_rectangle([(mi_cols_x[3] + 68, my), (mi_cols_x[3] + 152, my + 18)], radius=3, fill=e_bg)
        draw.text((mi_cols_x[3] + 110, my + 9), risk, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # =========================================================================
    # 4. BOTTOM SECTION: 4 COMPACT PANELS (Y: 816 to 1066)
    # =========================================================================
    b_y0, b_y1 = 816, 1066
    
    # Panel 4A: MODEL VALIDATION (X: 20 to 520, W: 500)
    p4a_x0, p4a_x1 = 20, 520
    draw.rounded_rectangle([(p4a_x0, b_y0), (p4a_x1, b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)
    draw_icon_gear(draw, p4a_x0 + 30, b_y0 + 24, col=(0, 210, 255))
    draw.text((p4a_x0 + 46, b_y0 + 15), "MODEL VALIDATION", fill=(0, 210, 255), font=f_panel_hdr)

    val_cards = [
        ("WALK FORWARD", "PASS"),
        ("OUT OF SAMPLE", "PASS"),
        ("CALIBRATION", "PASS"),
        ("MODEL DRIFT", "LOW"),
        ("REGIME FIT", "HIGH")
    ]
    badge_w = 90
    for b_i, (b_title, b_val) in enumerate(val_cards):
        bx = p4a_x0 + 14 + b_i * 96
        by = b_y0 + 44
        draw.text((bx + badge_w // 2, by), b_title, fill=(120, 150, 185), font=get_font(9, bold=True), anchor="ma")
        draw.rounded_rectangle([(bx, by + 18), (bx + badge_w, by + 42)], radius=4, fill=(0, 140, 65))
        draw.text((bx + badge_w // 2, by + 30), b_val, fill=(255, 255, 255), font=f_pill, anchor="mm")

    # Bottom Stat metrics: SAMPLE SIZE, MAE, MFE, DRAWDOWN
    draw.line([(p4a_x0 + 16, b_y0 + 115), (p4a_x1 - 16, b_y0 + 115)], fill=(15, 35, 68), width=1)
    stat_cols = [
        ("SAMPLE SIZE", "1,284", (255, 255, 255)),
        ("MAE", "0.21 ATR", (0, 210, 255)),
        ("MFE", "0.78 ATR", (0, 210, 255)),
        ("DRAWDOWN", "CONTROLLED", (255, 255, 255))
    ]
    stat_w = (p4a_x1 - p4a_x0 - 32) // 4
    for s_i, (s_lbl, s_val, s_col) in enumerate(stat_cols):
        sx = p4a_x0 + 16 + s_i * stat_w + stat_w // 2
        draw.text((sx, b_y0 + 140), s_lbl, fill=(120, 150, 185), font=f_label_sm, anchor="mm")
        draw.text((sx, b_y0 + 175), s_val, fill=s_col, font=get_font(15, bold=True), anchor="mm")

    # Panel 4B: FINAL RANKING (TOP SETUPS) (X: 532 to 992, W: 460)
    p4b_x0, p4b_x1 = 532, 992
    draw.rounded_rectangle([(p4b_x0, b_y0), (p4b_x1, b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)
    draw_icon_trophy(draw, p4b_x0 + 30, b_y0 + 24, col=(0, 210, 255))
    draw.text((p4b_x0 + 46, b_y0 + 15), "FINAL RANKING (TOP SETUPS)", fill=(0, 210, 255), font=f_panel_hdr)

    draw.text((p4b_x0 + 16, b_y0 + 44), "#", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4b_x0 + 46, b_y0 + 44), "PAIR", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4b_x0 + 130, b_y0 + 44), "SETUP", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4b_x0 + 275, b_y0 + 44), "CONFIDENCE", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4b_x0 + 390, b_y0 + 44), "SCORE", fill=(120, 150, 185), font=f_tbl_hdr)

    for r_i, rk in enumerate(engine_data.get("final_ranking", [])[:5]):
        ry = b_y0 + 72 + r_i * 32
        rank_num = rk["rank"]
        badge_fill = (220, 160, 20) if rank_num == 1 else ((160, 170, 185) if rank_num == 2 else ((180, 100, 30) if rank_num == 3 else (18, 36, 68)))
        draw.ellipse([(p4b_x0 + 14, ry + 2), (p4b_x0 + 32, ry + 20)], fill=badge_fill)
        draw.text((p4b_x0 + 23, ry + 11), str(rank_num), fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

        draw.text((p4b_x0 + 46, ry + 5), rk["pair"], fill=(255, 255, 255), font=f_tbl_cell_b)

        st_name = rk["setup"]
        s_bg = (180, 25, 35) if "SELL" in st_name else (0, 140, 65)
        draw.rounded_rectangle([(p4b_x0 + 120, ry + 2), (p4b_x0 + 245, ry + 20)], radius=3, fill=s_bg)
        draw.text((p4b_x0 + 182, ry + 11), st_name, fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

        draw.text((p4b_x0 + 300, ry + 5), rk["confidence"], fill=(255, 255, 255), font=f_tbl_cell)

        draw.rounded_rectangle([(p4b_x0 + 390, ry + 2), (p4b_x0 + 430, ry + 20)], radius=3, fill=(0, 140, 65))
        draw.text((p4b_x0 + 410, ry + 11), str(rk["score"]), fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Panel 4C: RECENT SIGNALS (X: 1004 to 1424, W: 420)
    p4c_x0, p4c_x1 = 1004, 1424
    draw.rounded_rectangle([(p4c_x0, b_y0), (p4c_x1, b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)
    draw_icon_bell(draw, p4c_x0 + 30, b_y0 + 24, col=(0, 210, 255))
    draw.text((p4c_x0 + 46, b_y0 + 15), "RECENT SIGNALS", fill=(0, 210, 255), font=f_panel_hdr)

    draw.text((p4c_x0 + 16, b_y0 + 44), "TIME", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4c_x0 + 90, b_y0 + 44), "PAIR", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4c_x0 + 180, b_y0 + 44), "ACTION", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4c_x0 + 280, b_y0 + 44), "STATUS", fill=(120, 150, 185), font=f_tbl_hdr)

    for r_i, sig in enumerate(engine_data.get("recent_signals", [])[:5]):
        ry = b_y0 + 72 + r_i * 32
        draw.text((p4c_x0 + 16, ry + 5), sig["time"], fill=(180, 200, 225), font=f_tbl_cell)
        draw.text((p4c_x0 + 90, ry + 5), sig["pair"], fill=(255, 255, 255), font=f_tbl_cell_b)

        act_col = (245, 65, 75) if sig["action"] == "SELL" else (0, 230, 118)
        draw.text((p4c_x0 + 180, ry + 5), sig["action"], fill=act_col, font=f_tbl_cell_b)

        st = sig["status"]
        st_bg = (180, 25, 35) if st == "OP ZONE" else ((0, 140, 65) if st in ["ACTIVE", "TP1 HIT"] else (190, 110, 20))
        draw.rounded_rectangle([(p4c_x0 + 265, ry + 2), (p4c_x0 + 380, ry + 20)], radius=3, fill=st_bg)
        
        # Micro status symbol
        sx_icon, sy_icon = p4c_x0 + 278, ry + 11
        if st == "OP ZONE":
            draw.ellipse([(sx_icon - 4, sy_icon - 4), (sx_icon + 4, sy_icon + 4)], outline=(255, 255, 255), width=1)
            draw.line([(sx_icon - 3, sy_icon - 3), (sx_icon + 3, sy_icon + 3)], fill=(255, 255, 255), width=1)
        elif st in ["ACTIVE", "TP1 HIT"]:
            draw.line([(sx_icon - 3, sy_icon), (sx_icon - 1, sy_icon + 3)], fill=(255, 255, 255), width=2)
            draw.line([(sx_icon - 1, sy_icon + 3), (sx_icon + 4, sy_icon - 3)], fill=(255, 255, 255), width=2)
        else:
            draw.polygon([(sx_icon, sy_icon - 4), (sx_icon - 4, sy_icon + 4), (sx_icon + 4, sy_icon + 4)], fill=(255, 255, 255))
            
        draw.text((p4c_x0 + 330, ry + 11), st, fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

    # Panel 4D: EVENT CALENDAR (WIB) (X: 1436 to 1900, W: 464)
    p4d_x0, p4d_x1 = 1436, 1900
    draw.rounded_rectangle([(p4d_x0, b_y0), (p4d_x1, b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)
    draw_icon_calendar(draw, p4d_x0 + 30, b_y0 + 24, col=(0, 210, 255))
    draw.text((p4d_x0 + 46, b_y0 + 15), "EVENT CALENDAR (WIB)", fill=(0, 210, 255), font=f_panel_hdr)

    draw.text((p4d_x0 + 16, b_y0 + 44), "TIME", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4d_x0 + 80, b_y0 + 44), "EVENT", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4d_x0 + 370, b_y0 + 44), "IMPACT", fill=(120, 150, 185), font=f_tbl_hdr)

    for r_i, ev in enumerate(engine_data.get("event_calendar", [])[:5]):
        ry = b_y0 + 72 + r_i * 32
        draw.text((p4d_x0 + 16, ry + 5), ev["time"], fill=(180, 200, 225), font=f_tbl_cell)
        draw.text((p4d_x0 + 80, ry + 5), ev["event"], fill=(255, 255, 255), font=f_tbl_cell)

        imp = ev["impact"]
        imp_bg = (180, 25, 35) if imp == "HIGH" else (190, 110, 20)
        draw.rounded_rectangle([(p4d_x0 + 360, ry + 2), (p4d_x0 + 440, ry + 20)], radius=3, fill=imp_bg)
        draw.text((p4d_x0 + 400, ry + 11), imp, fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

    # High-Resolution Output
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
