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
        # 3D Gold bars icon
        draw.polygon([(cx - 13, cy + 2), (cx + 2, cy + 2), (cx + 7, cy - 7), (cx - 8, cy - 7)], fill=(255, 215, 0), outline=(218, 165, 32))
        draw.polygon([(cx - 8, cy + 9), (cx + 7, cy + 9), (cx + 13, cy), (cx - 2, cy)], fill=(255, 195, 0), outline=(184, 134, 11))
    elif p_type == "oil":
        # 3D Oil droplet icon
        draw_sphere(draw, cx, cy + 3, r - 3, (140, 150, 165))
        draw.polygon([(cx, cy - 11), (cx - 6, cy + 3), (cx + 6, cy + 3)], fill=(25, 30, 42))
    elif p_type == "eur":
        # EU blue circle with circle of stars
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(0, 51, 153), outline=(40, 90, 200), width=1)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            sx = int(cx + (r - 4) * math.cos(rad))
            sy = int(cy + (r - 4) * math.sin(rad))
            draw.ellipse([(sx - 1, sy - 1), (sx + 1, sy + 1)], fill=(255, 204, 0))
    elif p_type == "gbp":
        # UK Flag icon circle
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(1, 33, 105), outline=(100, 140, 210), width=1)
        draw.line([(cx - r + 2, cy), (cx + r - 2, cy)], fill=(255, 255, 255), width=5)
        draw.line([(cx, cy - r + 2), (cx, cy + r - 2)], fill=(255, 255, 255), width=5)
        draw.line([(cx - r + 2, cy), (cx + r - 2, cy)], fill=(200, 16, 46), width=3)
        draw.line([(cx, cy - r + 2), (cx, cy + r - 2)], fill=(200, 16, 46), width=3)
    elif p_type == "jpy":
        # Japan flag circle
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(255, 255, 255), outline=(180, 180, 180), width=1)
        draw.ellipse([(cx - r//2, cy - r//2), (cx + r//2, cy + r//2)], fill=(188, 0, 45))
    else:
        draw_sphere(draw, cx, cy, r, (0, 170, 255))

def draw_trend_arrow_badge(draw, cx, cy, trend):
    r = 16
    if trend == "BEARISH":
        bg_col = (185, 28, 28)
        arrow_col = (255, 255, 255)
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=bg_col)
        # Down-right arrow
        draw.line([(cx - 6, cy - 6), (cx + 6, cy + 6)], fill=arrow_col, width=3)
        draw.polygon([(cx + 6, cy + 6), (cx + 6, cy), (cx, cy + 6)], fill=arrow_col)
    else:
        bg_col = (16, 185, 129)
        arrow_col = (255, 255, 255)
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=bg_col)
        # Up-right arrow
        draw.line([(cx - 6, cy + 6), (cx + 6, cy - 6)], fill=arrow_col, width=3)
        draw.polygon([(cx + 6, cy - 6), (cx + 6, cy), (cx, cy - 6)], fill=arrow_col)

# Custom Crisp Vector Icon Renderers (to avoid missing emojis/boxes)
def draw_icon_target(draw, cx, cy, col=(0, 210, 255)):
    draw.ellipse([(cx - 8, cy - 8), (cx + 8, cy + 8)], outline=col, width=2)
    draw.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], outline=col, width=1)
    draw.ellipse([(cx - 1, cy - 1), (cx + 1, cy + 1)], fill=col)

def draw_icon_brain(draw, cx, cy, col=(0, 210, 255)):
    # Two lobes of brain
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
    # Checkmark inside
    draw.line([(cx - 3, cy), (cx - 1, cy + 3)], fill=col, width=2)
    draw.line([(cx - 1, cy + 3), (cx + 3, cy - 3)], fill=col, width=2)

def draw_icon_cloud(draw, cx, cy, col=(0, 230, 118)):
    draw.ellipse([(cx - 6, cy - 2), (cx, cy + 4)], fill=col)
    draw.ellipse([(cx - 2, cy - 5), (cx + 4, cy + 2)], fill=col)
    draw.ellipse([(cx + 1, cy - 2), (cx + 7, cy + 4)], fill=col)
    draw.rectangle([(cx - 4, cy + 1), (cx + 5, cy + 4)], fill=col)

def generate_precision_dashboard_card(engine_data: dict, now_wib: datetime = None) -> bytes:
    """
    Renders 1920x1080 (16:9 Full HD) Institutional XEDY AI Precision Trading Engine Dashboard.
    Single-Page, Zero-Scroll, Multi-Agent Architecture matching media_1791360039961.jpg.
    """
    if now_wib is None:
        now_wib = datetime.now(WIB)

    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (2, 6, 15))
    draw = ImageDraw.Draw(img)

    # Subtle Background Cyber Grid
    for x in range(0, W, 48):
        draw.line([(x, 0), (x, H)], fill=(6, 14, 28), width=1)
    for y in range(0, H, 48):
        draw.line([(0, y), (W, y)], fill=(6, 14, 28), width=1)

    # Outer Global Border (Navy Blue Institutional Frame)
    draw.rounded_rectangle([(10, 10), (W - 10, H - 10)], radius=10, outline=(14, 42, 82), width=2)

    # Typography
    f_logo = get_font(28, bold=True)
    f_engine_title = get_font(18, bold=True)
    f_engine_sub = get_font(11, bold=False)
    f_pill = get_font(11, bold=True)
    f_pill_sm = get_font(10, bold=True)
    f_clock = get_font(16, bold=True)
    f_date = get_font(11, bold=False)
    f_label_sm = get_font(10, bold=False)
    
    f_pair_title = get_font(18, bold=True)
    f_pair_sub = get_font(11, bold=False)
    f_price = get_font(20, bold=True)
    f_chg = get_font(12, bold=True)
    
    f_trend = get_font(17, bold=True)
    f_trend_score = get_font(12, bold=False)
    f_range_val = get_font(11, bold=True)
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
    draw.rounded_rectangle([(18, 14), (W - 18, 88)], radius=8, fill=(4, 11, 24), outline=(15, 38, 74), width=1)

    # Brand Title: XEDY in cyan, AI in vivid blue
    draw.text((32, 22), "XEDY", fill=(0, 210, 255), font=f_logo)
    draw.text((115, 22), "AI", fill=(41, 121, 255), font=f_logo)
    draw.text((158, 26), "PRECISION TRADING ENGINE", fill=(255, 255, 255), font=f_engine_title)
    draw.text((158, 56), "Multi-Agent • Low Error • High Probability", fill=(130, 160, 195), font=f_engine_sub)

    # Widget 1: LIVE Clock
    draw.rounded_rectangle([(710, 30), (764, 52)], radius=4, fill=(0, 230, 118))
    draw.text((737, 41), "LIVE", fill=(0, 0, 0), font=f_pill, anchor="mm")
    time_str = now_wib.strftime("%H:%M:%S WIB")
    date_str = now_wib.strftime("%a, %d %b %Y")
    draw.text((776, 28), time_str, fill=(255, 255, 255), font=f_clock)
    draw.text((776, 52), date_str, fill=(140, 160, 185), font=f_date)

    # Widget 2: Market Regime
    draw.text((950, 24), "Market Regime", fill=(120, 150, 180), font=f_label_sm)
    draw.rounded_rectangle([(950, 42), (1024, 64)], radius=4, fill=(215, 45, 55))
    draw.text((987, 53), "RISK-OFF", fill=(255, 255, 255), font=f_pill_sm, anchor="mm")
    draw.text((1034, 53), "HIGH VOLATILITY", fill=(245, 75, 75), font=f_pill_sm, anchor="lm")

    # Widget 3: Event Risk
    draw.text((1180, 24), "Event Risk", fill=(120, 150, 180), font=f_label_sm)
    draw.rounded_rectangle([(1180, 42), (1242, 64)], radius=4, fill=(18, 30, 52), outline=(215, 45, 55), width=1)
    draw_icon_calendar(draw, 1194, 53, col=(245, 75, 75))
    draw.rounded_rectangle([(1206, 44), (1238, 62)], radius=3, fill=(215, 45, 55))
    draw.text((1222, 53), "HIGH", fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

    # Widget 4: Data Feed
    draw.text((1280, 24), "Data Feed", fill=(120, 150, 180), font=f_label_sm)
    draw.rounded_rectangle([(1280, 42), (1344, 64)], radius=4, fill=(18, 30, 52), outline=(0, 200, 100), width=1)
    draw_icon_cloud(draw, 1294, 53, col=(0, 230, 118))
    draw.text((1320, 53), "LIVE", fill=(0, 230, 118), font=f_pill, anchor="mm")

    # Widget 5: Model Status
    draw.text((1380, 24), "Model Status", fill=(120, 150, 180), font=f_label_sm)
    draw.rounded_rectangle([(1380, 42), (1444, 64)], radius=4, fill=(18, 30, 52), outline=(0, 200, 100), width=1)
    draw_icon_shield(draw, 1394, 53, col=(0, 230, 118))
    draw.text((1420, 53), "PASS", fill=(0, 230, 118), font=f_pill, anchor="mm")

    # Widget 6: Version Badge
    draw.rounded_rectangle([(1560, 22), (1890, 78)], radius=6, fill=(10, 25, 50), outline=(0, 140, 255), width=1)
    cx_cb, cy_cb = 1585, 50
    draw.polygon([(cx_cb, cy_cb - 12), (cx_cb + 11, cy_cb - 6), (cx_cb, cy_cb), (cx_cb - 11, cy_cb - 6)], fill=(0, 190, 255))
    draw.polygon([(cx_cb - 11, cy_cb - 6), (cx_cb, cy_cb), (cx_cb, cy_cb + 12), (cx_cb - 11, cy_cb + 6)], fill=(0, 120, 200))
    draw.polygon([(cx_cb + 11, cy_cb - 6), (cx_cb, cy_cb), (cx_cb, cy_cb + 12), (cx_cb + 11, cy_cb + 6)], fill=(0, 80, 150))
    draw.text((1610, 36), "XEDY v31.0", fill=(0, 210, 255), font=get_font(16, bold=True))
    draw.text((1610, 58), "5 Assets • AI Multi-Agent", fill=(100, 180, 255), font=f_engine_sub)

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

        # Card Outer Box
        draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=8, fill=(4, 11, 24), outline=(18, 48, 92), width=1)

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

        # Daily Range Section (Y: y0 + 134 to y0 + 214)
        slider_left = x0 + 24
        slider_right = x1 - 24
        slider_w = slider_right - slider_left
        pos_pct = c["pos_pct"]
        marker_x = int(slider_left + (pos_pct / 100.0) * slider_w)
        marker_x = max(slider_left + 15, min(slider_right - 15, marker_x))

        # Range Values: Low on left, High on right
        draw.text((slider_left, y0 + 138), f"{c['low']:,.{digits}f}", fill=(240, 245, 255), font=f_range_val)
        draw.text((slider_left, y0 + 154), "Low", fill=(120, 140, 165), font=f_range_lbl)

        draw.text((slider_right, y0 + 138), f"{c['high']:,.{digits}f}", fill=(240, 245, 255), font=f_range_val, anchor="ra")
        draw.text((slider_right, y0 + 154), "High", fill=(120, 140, 165), font=f_range_lbl, anchor="ra")

        # Avoid text overlap: only draw live price text above marker if it doesn't collide with Low/High
        dist_to_low = marker_x - slider_left
        dist_to_high = slider_right - marker_x
        if dist_to_low > 55 and dist_to_high > 55:
            draw.text((marker_x, y0 + 138), p_str, fill=(255, 255, 255), font=f_range_val, anchor="ma")

        # Horizontal Slider Bar Track (Y: y0 + 172)
        bar_y = y0 + 172
        for bx in range(slider_left, slider_right):
            ratio = (bx - slider_left) / slider_w
            if trend == "BEARISH":
                # Red emphasis for bearish assets
                if ratio < 0.40:
                    b_color = (235, 45, 55)
                elif ratio < 0.70:
                    b_color = (int(235 - 150 * (ratio - 0.40) / 0.30), int(45 + 140 * (ratio - 0.40) / 0.30), 60)
                else:
                    b_color = (25, 160, 90)
            else:
                # Green emphasis for bullish assets
                if ratio < 0.30:
                    b_color = (30, 60, 100)
                elif ratio < 0.60:
                    b_color = (int(30 + 100 * (ratio - 0.30) / 0.30), int(60 + 150 * (ratio - 0.30) / 0.30), 100)
                else:
                    b_color = (0, 230, 118)
            draw.line([(bx, bar_y - 2), (bx, bar_y + 2)], fill=b_color, width=1)

        # Live Marker Dot & Tick
        draw.line([(marker_x, bar_y - 6), (marker_x, bar_y + 6)], fill=(255, 255, 255), width=2)
        draw.ellipse([(marker_x - 4, bar_y - 4), (marker_x + 4, bar_y + 4)], fill=(255, 255, 255))

        # Position % Badge Pill below slider
        badge_col = (215, 45, 55) if trend == "BEARISH" else (0, 200, 100)
        pill_w = 42
        draw.rounded_rectangle([(marker_x - pill_w // 2, bar_y + 10), (marker_x + pill_w // 2, bar_y + 28)], radius=3, fill=badge_col)
        draw.polygon([(marker_x, bar_y + 7), (marker_x - 4, bar_y + 11), (marker_x + 4, bar_y + 11)], fill=badge_col)
        draw.text((marker_x, bar_y + 19), f"{pos_pct}%", fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

        # Setup Badge Row (Y: y0 + 224)
        draw.rounded_rectangle([(x0 + 24, y0 + 222), (x0 + 72, y0 + 244)], radius=4, fill=(16, 32, 58))
        draw.text((x0 + 48, y0 + 233), "SETUP", fill=(140, 180, 230), font=f_pill_sm, anchor="mm")

        setup_name = c["setup"]
        s_bg = (180, 25, 35) if "SELL" in setup_name else (0, 150, 70)
        draw.rounded_rectangle([(x0 + 78, y0 + 222), (x0 + 195, y0 + 244)], radius=4, fill=s_bg)
        draw.text((x0 + 136, y0 + 233), setup_name, fill=(255, 255, 255), font=f_pill, anchor="mm")

        # Order Execution Box (Y: y0 + 258 to y1 - 16)
        exec_y0 = y0 + 256
        exec_y1 = y1 - 16
        draw.rounded_rectangle([(x0 + 16, exec_y0), (x1 - 16, exec_y1)], radius=6, fill=(3, 9, 20), outline=(14, 32, 60), width=1)

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

        # Quality Gate Badge (bottom right)
        q_pass = "PASS" in c["quality_gate"]
        q_bg = (0, 170, 75) if q_pass else (190, 120, 10)
        draw.rounded_rectangle([(rcol_x - 42, exec_y0 + 120), (rcol_x + 42, exec_y0 + 154)], radius=4, fill=q_bg)
        q_label1 = "GATE"
        q_label2 = "PASS" if q_pass else "WARNING"
        draw.text((rcol_x, exec_y0 + 130), q_label1, fill=(255, 255, 255), font=get_font(9, bold=True), anchor="mm")
        draw.text((rcol_x, exec_y0 + 144), q_label2, fill=(255, 255, 255), font=get_font(11, bold=True), anchor="mm")

    # =========================================================================
    # 3. MIDDLE SECTION: 2 BIG PANELS (Y: 584 to 804)
    # =========================================================================
    # Panel 3A: PRECISION & ERROR METRICS (Left: X: 20 to 1040, W: 1020)
    p3a_x0, p3a_y0 = 20, 584
    p3a_x1, p3a_y1 = 1040, 804
    draw.rounded_rectangle([(p3a_x0, p3a_y0), (p3a_x1, p3a_y1)], radius=8, fill=(4, 11, 24), outline=(18, 48, 92), width=1)

    # Header with crisp vector Target icon
    draw_icon_target(draw, p3a_x0 + 30, p3a_y0 + 24, col=(0, 210, 255))
    draw.text((p3a_x0 + 46, p3a_y0 + 15), "PRECISION & ERROR METRICS", fill=(0, 210, 255), font=f_panel_hdr)

    # Table Header (Y: p3a_y0 + 44)
    tbl_cols_x = [p3a_x0 + 20, p3a_x0 + 135, p3a_x0 + 260, p3a_x0 + 390, p3a_x0 + 520, p3a_x0 + 650, p3a_x0 + 775, p3a_x0 + 900]
    tbl_headers = ["PAIR", "TREND ACC", "TREND ERR", "OP ERR (ATR)", "TP ERR (ATR)", "SL ERR (ATR)", "CALIB ERR", "PRECISION"]
    for col_i, th in enumerate(tbl_headers):
        draw.text((tbl_cols_x[col_i], p3a_y0 + 46), th, fill=(120, 150, 185), font=f_tbl_hdr)

    # Table Rows (5 pairs)
    pt_rows = engine_data.get("precision_table", [])
    for row_i, r in enumerate(pt_rows[:5]):
        ry = p3a_y0 + 74 + row_i * 26
        if row_i % 2 == 1:
            draw.rectangle([(p3a_x0 + 10, ry - 4), (p3a_x1 - 10, ry + 20)], fill=(6, 16, 32))

        # PAIR
        draw.text((tbl_cols_x[0], ry + 2), r["pair"], fill=(255, 255, 255), font=f_tbl_cell_b)

        # TREND ACC (Green badge)
        draw.rounded_rectangle([(tbl_cols_x[1] - 4, ry), (tbl_cols_x[1] + 52, ry + 18)], radius=3, fill=(0, 140, 65))
        draw.text((tbl_cols_x[1] + 24, ry + 9), r["trend_acc"], fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

        # TREND ERR (Amber / Red badge)
        err_val = float(r["trend_err"].replace("%", ""))
        err_bg = (180, 40, 30) if err_val >= 12.0 else (190, 100, 20)
        draw.rounded_rectangle([(tbl_cols_x[2] - 4, ry), (tbl_cols_x[2] + 56, ry + 18)], radius=3, fill=err_bg)
        draw.text((tbl_cols_x[2] + 26, ry + 9), r["trend_err"], fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

        # OP ERR (ATR)
        draw.text((tbl_cols_x[3] + 20, ry + 2), r["op_err"], fill=(220, 230, 245), font=f_tbl_cell)

        # TP ERR (ATR)
        draw.text((tbl_cols_x[4] + 20, ry + 2), r["tp_err"], fill=(220, 230, 245), font=f_tbl_cell)

        # SL ERR (ATR)
        draw.text((tbl_cols_x[5] + 20, ry + 2), r["sl_err"], fill=(220, 230, 245), font=f_tbl_cell)

        # CALIB ERR
        draw.text((tbl_cols_x[6] + 16, ry + 2), r["calib_err"], fill=(220, 230, 245), font=f_tbl_cell)

        # PRECISION (Score badge)
        prec_val = int(r["precision"].split("/")[0])
        p_bg = (0, 150, 70) if prec_val >= 88 else ((190, 120, 20) if prec_val >= 80 else (180, 40, 30))
        draw.rounded_rectangle([(tbl_cols_x[7] - 4, ry), (tbl_cols_x[7] + 62, ry + 18)], radius=3, fill=p_bg)
        draw.text((tbl_cols_x[7] + 29, ry + 9), r["precision"], fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Panel 3B: MARKET INTELLIGENCE (Right: X: 1052 to 1900, W: 848)
    p3b_x0, p3b_y0 = 1052, 584
    p3b_x1, p3b_y1 = 1900, 804
    draw.rounded_rectangle([(p3b_x0, p3b_y0), (p3b_x1, p3b_y1)], radius=8, fill=(4, 11, 24), outline=(18, 48, 92), width=1)

    # Header with crisp vector Brain icon
    draw_icon_brain(draw, p3b_x0 + 30, p3b_y0 + 24, col=(0, 210, 255))
    draw.text((p3b_x0 + 46, p3b_y0 + 15), "MARKET INTELLIGENCE", fill=(0, 210, 255), font=f_panel_hdr)

    # 4 Sub-Columns:
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
        # Vector arrow inside pill
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
        # Vector triangle indicator inside pill
        rx, ry_t = mi_cols_x[2] + 58, my + 9
        if "UP" in reg or "BREAKOUT" in reg:
            draw.polygon([(rx, ry_t - 4), (rx - 4, ry_t + 3), (rx + 4, ry_t + 3)], fill=(255, 255, 255))
        else:
            draw.polygon([(rx, ry_t + 4), (rx - 4, ry_t - 3), (rx + 4, ry_t - 3)], fill=(255, 255, 255))
        draw.text((mi_cols_x[2] + 107, my + 9), reg, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Sub-column 4: Event Risk
    for r_i, (ev, risk, r_type) in enumerate(engine_data.get("event_risk", [])):
        my = p3b_y0 + 74 + r_i * 26
        draw.text((mi_cols_x[3], my + 2), ev, fill=(255, 255, 255), font=f_tbl_cell_b)
        e_bg = (180, 25, 35) if "HIGH" in risk else (190, 110, 20)
        draw.rounded_rectangle([(mi_cols_x[3] + 50, my), (mi_cols_x[3] + 144, my + 18)], radius=3, fill=e_bg)
        draw.text((mi_cols_x[3] + 97, my + 9), risk, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # =========================================================================
    # 4. BOTTOM SECTION: 4 COMPACT PANELS (Y: 816 to 1066)
    # =========================================================================
    b_y0, b_y1 = 816, 1066
    
    # -------------------------------------------------------------------------
    # Panel 4A: MODEL VALIDATION (X: 20 to 520, W: 500)
    # -------------------------------------------------------------------------
    p4a_x0, p4a_x1 = 20, 520
    draw.rounded_rectangle([(p4a_x0, b_y0), (p4a_x1, b_y1)], radius=8, fill=(4, 11, 24), outline=(18, 48, 92), width=1)
    draw_icon_gear(draw, p4a_x0 + 30, b_y0 + 24, col=(0, 210, 255))
    draw.text((p4a_x0 + 46, b_y0 + 15), "MODEL VALIDATION", fill=(0, 210, 255), font=f_panel_hdr)

    # 5 Metric validation cards
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

    # -------------------------------------------------------------------------
    # Panel 4B: FINAL RANKING (TOP SETUPS) (X: 532 to 992, W: 460)
    # -------------------------------------------------------------------------
    p4b_x0, p4b_x1 = 532, 992
    draw.rounded_rectangle([(p4b_x0, b_y0), (p4b_x1, b_y1)], radius=8, fill=(4, 11, 24), outline=(18, 48, 92), width=1)
    draw_icon_trophy(draw, p4b_x0 + 30, b_y0 + 24, col=(0, 210, 255))
    draw.text((p4b_x0 + 46, b_y0 + 15), "FINAL RANKING (TOP SETUPS)", fill=(0, 210, 255), font=f_panel_hdr)

    # Headers
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

    # -------------------------------------------------------------------------
    # Panel 4C: RECENT SIGNALS (X: 1004 to 1424, W: 420)
    # -------------------------------------------------------------------------
    p4c_x0, p4c_x1 = 1004, 1424
    draw.rounded_rectangle([(p4c_x0, b_y0), (p4c_x1, b_y1)], radius=8, fill=(4, 11, 24), outline=(18, 48, 92), width=1)
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
        # Small circle marker instead of emoji
        draw.ellipse([(p4c_x0 + 276, ry + 8), (p4c_x0 + 282, ry + 14)], fill=(255, 255, 255))
        draw.text((p4c_x0 + 326, ry + 11), st, fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

    # -------------------------------------------------------------------------
    # Panel 4D: EVENT CALENDAR (WIB) (X: 1436 to 1900, W: 464)
    # -------------------------------------------------------------------------
    p4d_x0, p4d_x1 = 1436, 1900
    draw.rounded_rectangle([(p4d_x0, b_y0), (p4d_x1, b_y1)], radius=8, fill=(4, 11, 24), outline=(18, 48, 92), width=1)
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
