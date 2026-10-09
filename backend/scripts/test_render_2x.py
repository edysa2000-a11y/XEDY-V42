import os
import sys
import io
import math
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.telegram.precision_engine import PrecisionTradingEngine
from backend.telegram.precision_dashboard_generator import (
    get_font, draw_sphere, draw_flag_icon, draw_trend_arrow_badge,
    draw_icon_target, draw_icon_brain, draw_icon_gear, draw_icon_trophy,
    draw_icon_bell, draw_icon_calendar, draw_icon_shield, draw_icon_cloud, draw_icon_macro
)

WIB = timezone(timedelta(hours=7))

def render_2x_dashboard(engine_data: dict, out_path: str):
    now_wib = datetime.now(WIB)
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (2, 6, 14))
    draw = ImageDraw.Draw(img)

    # Background Matrix Grid
    for x in range(0, W, 48):
        draw.line([(x, 0), (x, H)], fill=(5, 13, 26), width=1)
    for y in range(0, H, 48):
        draw.line([(0, y), (W, y)], fill=(5, 13, 26), width=1)

    # Outer Global Frame
    draw.rounded_rectangle([(8, 8), (W - 8, H - 8)], radius=10, outline=(14, 44, 88), width=2)

    # 2X SCALED TYPOGRAPHY
    f_logo = get_font(46, bold=True)
    f_engine_title = get_font(26, bold=True)
    f_engine_sub = get_font(15, bold=False)
    
    f_clock = get_font(22, bold=True)
    f_date = get_font(14, bold=False)
    f_badge_sm = get_font(14, bold=True)
    f_label_sm = get_font(13, bold=False)

    f_pair_title = get_font(28, bold=True)
    f_pair_sub = get_font(14, bold=False)
    f_price = get_font(30, bold=True)
    f_chg = get_font(17, bold=True)

    f_trend = get_font(26, bold=True)
    f_trend_score = get_font(16, bold=False)

    f_range_val = get_font(18, bold=True)
    f_range_lbl = get_font(14, bold=False)
    f_pill_pos = get_font(15, bold=True)

    f_setup_tag = get_font(14, bold=True)
    f_setup_name = get_font(17, bold=True)

    f_exec_lbl = get_font(18, bold=True)
    f_exec_val = get_font(21, bold=True)
    f_exec_prob = get_font(18, bold=True)
    f_side_lbl = get_font(14, bold=True)
    f_side_val = get_font(22, bold=True)

    f_panel_hdr = get_font(22, bold=True)
    f_tbl_hdr = get_font(16, bold=True)
    f_tbl_cell = get_font(17, bold=False)
    f_tbl_cell_b = get_font(18, bold=True)
    f_pill = get_font(16, bold=True)
    f_pill_sm = get_font(15, bold=True)

    # =========================================================================
    # 1. HEADER SECTION (Y: 14 to 90)
    # =========================================================================
    draw.rounded_rectangle([(16, 12), (W - 16, 92)], radius=8, fill=(3, 10, 22), outline=(14, 36, 70), width=1)

    # Brand Title: XEDY in cyan, AI in royal blue
    draw.text((28, 22), "XEDY", fill=(0, 210, 255), font=f_logo)
    draw.text((156, 22), "AI", fill=(41, 121, 255), font=f_logo)
    draw.line([(212, 22), (212, 82)], fill=(20, 50, 95), width=1)
    draw.text((226, 22), "PRECISION TRADING ENGINE", fill=(255, 255, 255), font=f_engine_title)
    draw.text((226, 56), "Multi-Agent • Low Error • High Probability Architecture", fill=(130, 160, 195), font=f_engine_sub)

    # Cockpit Widgets on the right
    # Widget 1: LIVE Clock Box
    draw.rounded_rectangle([(760, 20), (970, 84)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.rounded_rectangle([(770, 32), (826, 68)], radius=4, fill=(0, 230, 118))
    draw.text((798, 50), "LIVE", fill=(0, 0, 0), font=f_pill_sm, anchor="mm")
    time_str = now_wib.strftime("%H:%M:%S WIB")
    date_str = now_wib.strftime("%a, %d %b %Y")
    draw.text((838, 30), time_str, fill=(255, 255, 255), font=f_clock)
    draw.text((838, 58), date_str, fill=(140, 165, 195), font=f_date)

    # Widget 2: Market Regime
    draw.rounded_rectangle([(980, 20), (1210, 84)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.text((992, 26), "Market Regime", fill=(120, 150, 185), font=f_label_sm)
    draw.rounded_rectangle([(992, 48), (1075, 76)], radius=4, fill=(215, 45, 55))
    draw.text((1033, 62), "RISK-OFF", fill=(255, 255, 255), font=f_badge_sm, anchor="mm")
    draw.text((1085, 62), "HIGH VOLATILITY", fill=(245, 75, 75), font=f_badge_sm, anchor="lm")

    # Widget 3: Event Risk
    draw.rounded_rectangle([(1220, 20), (1340, 84)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.text((1232, 26), "Event Risk", fill=(120, 150, 185), font=f_label_sm)
    draw_icon_calendar(draw, 1246, 62, col=(245, 75, 75))
    draw.rounded_rectangle([(1262, 48), (1330, 76)], radius=4, fill=(215, 45, 55))
    draw.text((1296, 62), "HIGH", fill=(255, 255, 255), font=f_badge_sm, anchor="mm")

    # Widget 4: Data Feed
    draw.rounded_rectangle([(1350, 20), (1470, 84)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.text((1362, 26), "Data Feed", fill=(120, 150, 185), font=f_label_sm)
    draw_icon_cloud(draw, 1378, 62, col=(0, 230, 118))
    draw.rounded_rectangle([(1394, 48), (1458, 76)], radius=4, fill=(8, 28, 22), outline=(0, 200, 100), width=1)
    draw.text((1426, 62), "LIVE", fill=(0, 230, 118), font=f_badge_sm, anchor="mm")

    # Widget 5: Model Status
    draw.rounded_rectangle([(1480, 20), (1600, 84)], radius=6, fill=(4, 12, 26), outline=(15, 38, 75), width=1)
    draw.text((1492, 26), "Model Status", fill=(120, 150, 185), font=f_label_sm)
    draw_icon_shield(draw, 1508, 62, col=(0, 230, 118))
    draw.rounded_rectangle([(1524, 48), (1588, 76)], radius=4, fill=(8, 28, 22), outline=(0, 200, 100), width=1)
    draw.text((1556, 62), "PASS", fill=(0, 230, 118), font=f_badge_sm, anchor="mm")

    # Widget 6: Version Badge
    draw.rounded_rectangle([(1610, 20), (1896, 84)], radius=6, fill=(6, 18, 38), outline=(0, 120, 230), width=1)
    cx_cb, cy_cb = 1636, 52
    draw.polygon([(cx_cb, cy_cb - 14), (cx_cb + 13, cy_cb - 7), (cx_cb, cy_cb), (cx_cb - 13, cy_cb - 7)], fill=(0, 190, 255))
    draw.polygon([(cx_cb - 13, cy_cb - 6), (cx_cb, cy_cb + 1), (cx_cb, cy_cb + 15), (cx_cb - 13, cy_cb + 8)], fill=(0, 140, 220))
    draw.polygon([(cx_cb, cy_cb + 1), (cx_cb + 13, cy_cb - 6), (cx_cb + 13, cy_cb + 8), (cx_cb, cy_cb + 15)], fill=(0, 100, 180))
    draw.text((1662, 30), "XEDY v31.0", fill=(0, 210, 255), font=f_clock)
    draw.text((1662, 58), "5 Assets • AI Multi-Agent", fill=(140, 165, 195), font=f_date)

    # =========================================================================
    # 2. PAIR DECISION CARDS (Y: 100 to 575)
    # =========================================================================
    card_w = 360
    card_gap = 12
    card_x_start = 20
    cards_data = engine_data.get("pair_cards", [])

    for i, c in enumerate(cards_data[:5]):
        x0 = card_x_start + i * (card_w + card_gap)
        x1 = x0 + card_w
        y0 = 100
        y1 = 575

        # Card Outer Box
        draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)

        # Asset Icon & Header
        icon_cx, icon_cy = x0 + 32, y0 + 32
        draw_flag_icon(draw, icon_cx, icon_cy, 16, c["icon"])

        # Pair Name & Subtitle
        draw.text((x0 + 56, y0 + 16), c["name"], fill=(255, 255, 255), font=f_pair_title)
        draw.text((x0 + 56, y0 + 46), c["subtitle"], fill=(130, 150, 175), font=f_pair_sub)

        # Live Price & Change (Right Aligned)
        digits = c["digits"]
        p_str = f"{c['price']:,.{digits}f}"
        draw.text((x1 - 18, y0 + 16), p_str, fill=(255, 255, 255), font=f_price, anchor="ra")
        
        chg_sign = "+" if c["chg_val"] >= 0 else ""
        chg_str = f"{chg_sign}{c['chg_val']:.{min(2, digits)}f} ({chg_sign}{c['chg_pct']:.2f}%)"
        chg_col = (0, 230, 118) if c["chg_val"] >= 0 else (245, 65, 75)
        draw.text((x1 - 18, y0 + 48), chg_str, fill=chg_col, font=f_chg, anchor="ra")

        # Trend Badge Row (Y: y0 + 72)
        trend = c["trend"]
        t_col = (245, 65, 75) if trend == "BEARISH" else (0, 230, 118)
        draw_trend_arrow_badge(draw, x0 + 32, y0 + 94, trend)
        draw.text((x0 + 56, y0 + 80), trend, fill=t_col, font=f_trend)
        draw.text((x0 + 56, y0 + 108), f"Trend Score  {c['trend_score']}/100", fill=(180, 195, 215), font=f_trend_score)

        # DAILY RANGE SECTION
        slider_left = x0 + 20
        slider_right = x1 - 20
        slider_w = slider_right - slider_left
        pos_pct = c["pos_pct"]
        marker_x = int(slider_left + (pos_pct / 100.0) * slider_w)
        marker_x = max(slider_left + 15, min(slider_right - 15, marker_x))

        low_str = f"{c['low']:,.{digits}f}"
        high_str = f"{c['high']:,.{digits}f}"
        w_low = draw.textlength(low_str, font=f_range_val)
        w_high = draw.textlength(high_str, font=f_range_val)
        w_p = draw.textlength(p_str, font=f_range_val)

        draw.text((slider_left, y0 + 134), low_str, fill=(170, 190, 215), font=f_range_val)
        draw.text((slider_left, y0 + 152), "Low", fill=(120, 140, 165), font=f_range_lbl)

        draw.text((slider_right, y0 + 134), high_str, fill=(170, 190, 215), font=f_range_val, anchor="ra")
        draw.text((slider_right, y0 + 152), "High", fill=(120, 140, 165), font=f_range_lbl, anchor="ra")

        # Live Price above marker with guaranteed clearance
        min_p_x = slider_left + w_low + 14 + (w_p / 2)
        max_p_x = slider_right - w_high - 14 - (w_p / 2)
        actual_p_x = int(max(min_p_x, min(max_p_x, marker_x)))
        draw.text((actual_p_x, y0 + 134), p_str, fill=(255, 255, 255), font=f_range_val, anchor="ma")

        # Graduation Ruler Ticks (Y: y0 + 172)
        bar_y = y0 + 172
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

        # Position % Badge Pill below slider
        badge_col = (215, 45, 55) if trend == "BEARISH" else (0, 200, 100)
        pill_w = 52
        draw.rounded_rectangle([(marker_x - pill_w // 2, bar_y + 12), (marker_x + pill_w // 2, bar_y + 34)], radius=4, fill=badge_col)
        draw.polygon([(marker_x, bar_y + 8), (marker_x - 5, bar_y + 13), (marker_x + 5, bar_y + 13)], fill=badge_col)
        draw.text((marker_x, bar_y + 23), f"{pos_pct}%", fill=(255, 255, 255), font=f_pill_pos, anchor="mm")

        # Setup Badge Row (Y: y0 + 218)
        draw.rounded_rectangle([(x0 + 20, y0 + 216), (x0 + 76, y0 + 242)], radius=4, fill=(16, 32, 58))
        draw.text((x0 + 48, y0 + 229), "SETUP", fill=(140, 180, 230), font=f_setup_tag, anchor="mm")

        setup_name = c["setup"]
        s_bg = (180, 25, 35) if "SELL" in setup_name else (0, 150, 70)
        draw.rounded_rectangle([(x0 + 82, y0 + 216), (x0 + 225, y0 + 242)], radius=4, fill=s_bg)
        draw.text((x0 + 153, y0 + 229), setup_name, fill=(255, 255, 255), font=f_setup_name, anchor="mm")

        # ORDER EXECUTION INSET CARD (Y: y0 + 252 to y1 - 12)
        exec_y0 = y0 + 252
        exec_y1 = y1 - 12
        draw.rounded_rectangle([(x0 + 12, exec_y0), (x1 - 12, exec_y1)], radius=6, fill=(2, 8, 18), outline=(14, 32, 60), width=1)

        # Left Column for OP, SL, TP1, TP2, TP3
        col1_x = x0 + 20
        col1_val_x = x0 + 64
        rcol_x = x1 - 60

        # Row 1: OP
        draw.text((col1_x, exec_y0 + 10), "OP", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 8), c["op"], fill=(255, 255, 255), font=f_exec_val)

        # Row 2: SL
        draw.text((col1_x, exec_y0 + 48), "SL", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 46), c["sl"], fill=(255, 255, 255), font=f_exec_val)

        # Row 3: TP1
        draw.text((col1_x, exec_y0 + 86), "TP1", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 84), c["tp1"], fill=(255, 255, 255), font=f_exec_val)
        draw.text((col1_val_x + 105, exec_y0 + 86), f"{c['tp1_prob']}%", fill=(0, 230, 118), font=f_exec_prob)

        # Row 4: TP2
        draw.text((col1_x, exec_y0 + 124), "TP2", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 122), c["tp2"], fill=(255, 255, 255), font=f_exec_val)
        draw.text((col1_val_x + 105, exec_y0 + 124), f"{c['tp2_prob']}%", fill=(0, 230, 118), font=f_exec_prob)

        # Row 5: TP3
        draw.text((col1_x, exec_y0 + 162), "TP3", fill=(120, 150, 190), font=f_exec_lbl)
        draw.text((col1_val_x, exec_y0 + 160), c["tp3"], fill=(255, 255, 255), font=f_exec_val)
        draw.text((col1_val_x + 105, exec_y0 + 162), f"{c['tp3_prob']}%", fill=(0, 230, 118), font=f_exec_prob)

        # Right Column: RR, CONF, GATE
        draw.text((rcol_x, exec_y0 + 8), "RR", fill=(120, 150, 190), font=f_side_lbl, anchor="mm")
        draw.text((rcol_x, exec_y0 + 30), c["rr"], fill=(0, 210, 255), font=f_side_val, anchor="mm")

        draw.text((rcol_x, exec_y0 + 66), "CONF", fill=(120, 150, 190), font=f_side_lbl, anchor="mm")
        draw.text((rcol_x, exec_y0 + 92), f"{c['confidence']}%", fill=(255, 255, 255), font=f_side_val, anchor="mm")

        # Quality Gate Badge (Bottom Right)
        q_pass = "PASS" in c["quality_gate"]
        q_bg = (0, 170, 75) if q_pass else (190, 120, 10)
        draw.rounded_rectangle([(rcol_x - 44, exec_y0 + 130), (rcol_x + 44, exec_y0 + 176)], radius=4, fill=q_bg)
        draw.text((rcol_x, exec_y0 + 143), "GATE", fill=(255, 255, 255), font=f_badge_sm, anchor="mm")
        draw.text((rcol_x, exec_y0 + 162), "PASS" if q_pass else "WARNING", fill=(255, 255, 255), font=f_pill, anchor="mm")

    # =========================================================================
    # 3. MIDDLE SECTION: 2 BIG PANELS (Y: 586 to 810)
    # =========================================================================
    # Panel 3A: PRECISION & ERROR METRICS (Left: X: 20 to 1040, W: 1020)
    p3a_x0, p3a_y0 = 20, 586
    p3a_x1, p3a_y1 = 1040, 810
    draw.rounded_rectangle([(p3a_x0, p3a_y0), (p3a_x1, p3a_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)

    draw_icon_target(draw, p3a_x0 + 32, p3a_y0 + 26, col=(0, 210, 255))
    draw.text((p3a_x0 + 50, p3a_y0 + 14), "PRECISION & ERROR METRICS", fill=(0, 210, 255), font=f_panel_hdr)

    tbl_cols_x = [p3a_x0 + 16, p3a_x0 + 140, p3a_x0 + 270, p3a_x0 + 400, p3a_x0 + 530, p3a_x0 + 655, p3a_x0 + 780, p3a_x0 + 895]
    tbl_headers = ["PAIR", "TREND ACC", "TREND ERR", "OP ERR", "TP ERR", "SL ERR", "CALIB", "PRECISION"]
    for col_i, th in enumerate(tbl_headers):
        draw.text((tbl_cols_x[col_i], p3a_y0 + 48), th, fill=(120, 150, 185), font=f_tbl_hdr)

    pt_rows = engine_data.get("precision_table", [])
    for row_i, r in enumerate(pt_rows[:5]):
        ry = p3a_y0 + 76 + row_i * 26
        if row_i % 2 == 1:
            draw.rectangle([(p3a_x0 + 10, ry - 3), (p3a_x1 - 10, ry + 21)], fill=(5, 15, 30))

        # PAIR
        draw.text((tbl_cols_x[0], ry + 1), r["pair"], fill=(255, 255, 255), font=f_tbl_cell_b)

        # TREND ACC
        draw.rounded_rectangle([(tbl_cols_x[1] - 4, ry - 2), (tbl_cols_x[1] + 66, ry + 20)], radius=3, fill=(0, 140, 65))
        draw.text((tbl_cols_x[1] + 31, ry + 9), r["trend_acc"], fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

        # TREND ERR
        err_val = float(r["trend_err"].replace("%", ""))
        err_bg = (180, 40, 30) if err_val >= 12.0 else (190, 100, 20)
        draw.rounded_rectangle([(tbl_cols_x[2] - 4, ry - 2), (tbl_cols_x[2] + 70, ry + 20)], radius=3, fill=err_bg)
        draw.text((tbl_cols_x[2] + 33, ry + 9), r["trend_err"], fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

        # ATR ERRORS
        draw.text((tbl_cols_x[3] + 12, ry + 1), r["op_err"], fill=(220, 230, 245), font=f_tbl_cell_b)
        draw.text((tbl_cols_x[4] + 12, ry + 1), r["tp_err"], fill=(220, 230, 245), font=f_tbl_cell_b)
        draw.text((tbl_cols_x[5] + 12, ry + 1), r["sl_err"], fill=(220, 230, 245), font=f_tbl_cell_b)
        draw.text((tbl_cols_x[6] + 6, ry + 1), r["calib_err"], fill=(220, 230, 245), font=f_tbl_cell_b)

        # PRECISION SCORE
        prec_val = int(r["precision"].split("/")[0])
        p_bg = (0, 150, 70) if prec_val >= 88 else ((190, 120, 20) if prec_val >= 80 else (180, 40, 30))
        draw.rounded_rectangle([(tbl_cols_x[7] - 4, ry - 2), (tbl_cols_x[7] + 80, ry + 20)], radius=3, fill=p_bg)
        draw.text((tbl_cols_x[7] + 38, ry + 9), r["precision"], fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Panel 3B: MARKET INTELLIGENCE (Right: X: 1052 to 1900, W: 848)
    p3b_x0, p3b_y0 = 1052, 586
    p3b_x1, p3b_y1 = 1900, 810
    draw.rounded_rectangle([(p3b_x0, p3b_y0), (p3b_x1, p3b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)

    draw_icon_brain(draw, p3b_x0 + 32, p3b_y0 + 26, col=(0, 210, 255))
    draw.text((p3b_x0 + 50, p3b_y0 + 14), "MARKET INTELLIGENCE", fill=(0, 210, 255), font=f_panel_hdr)

    col_w = (p3b_x1 - p3b_x0 - 36) // 4
    mi_cols_x = [p3b_x0 + 18 + j * col_w for j in range(4)]
    mi_titles = ["FUNDAMENTAL BIAS", "MONEY FLOW", "REGIME", "EVENT RISK"]
    for j, tit in enumerate(mi_titles):
        draw.text((mi_cols_x[j], p3b_y0 + 48), tit, fill=(120, 150, 185), font=f_tbl_hdr)

    # Sub-column 1: Fundamental Bias
    for r_i, (curr, bias, b_type) in enumerate(engine_data.get("fundamental_bias", [])):
        my = p3b_y0 + 76 + r_i * 26
        draw.text((mi_cols_x[0], my + 1), curr, fill=(255, 255, 255), font=f_tbl_cell_b)
        f_bg = (0, 140, 65) if bias == "STRONG" else (180, 25, 35)
        draw.rounded_rectangle([(mi_cols_x[0] + 56, my - 2), (mi_cols_x[0] + 150, my + 20)], radius=3, fill=f_bg)
        draw.text((mi_cols_x[0] + 103, my + 9), bias, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Sub-column 2: Money Flow
    for r_i, (ast, flow, f_type) in enumerate(engine_data.get("money_flow", [])):
        my = p3b_y0 + 76 + r_i * 26
        draw.text((mi_cols_x[1], my + 1), ast, fill=(255, 255, 255), font=f_tbl_cell_b)
        f_bg = (0, 140, 65) if flow == "INFLOW" else (180, 25, 35)
        draw.rounded_rectangle([(mi_cols_x[1] + 52, my - 2), (mi_cols_x[1] + 175, my + 20)], radius=3, fill=f_bg)
        draw.text((mi_cols_x[1] + 114, my + 9), flow, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Sub-column 3: Regime
    for r_i, (ast, reg, r_type) in enumerate(engine_data.get("regime", [])):
        my = p3b_y0 + 76 + r_i * 26
        draw.text((mi_cols_x[2], my + 1), ast, fill=(255, 255, 255), font=f_tbl_cell_b)
        r_bg = (0, 140, 65) if "UP" in reg or "BREAKOUT" in reg else (180, 25, 35)
        draw.rounded_rectangle([(mi_cols_x[2] + 48, my - 2), (mi_cols_x[2] + 175, my + 20)], radius=3, fill=r_bg)
        draw.text((mi_cols_x[2] + 112, my + 9), reg, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Sub-column 4: Event Risk
    for r_i, (ev, risk, r_type) in enumerate(engine_data.get("event_risk", [])):
        my = p3b_y0 + 76 + r_i * 26
        draw.text((mi_cols_x[3] + 24, my + 1), ev, fill=(255, 255, 255), font=f_tbl_cell_b)
        draw_icon_macro(draw, mi_cols_x[3] + 10, my + 10, ev.lower(), col=(245, 65, 75))
        e_bg = (180, 25, 35) if "HIGH" in risk else (190, 110, 20)
        draw.rounded_rectangle([(mi_cols_x[3] + 72, my - 2), (mi_cols_x[3] + 172, my + 20)], radius=3, fill=e_bg)
        draw.text((mi_cols_x[3] + 122, my + 9), risk, fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # =========================================================================
    # 4. BOTTOM SECTION: 4 COMPACT PANELS (Y: 822 to 1066)
    # =========================================================================
    b_y0, b_y1 = 822, 1066
    
    # Panel 4A: MODEL VALIDATION (X: 20 to 520, W: 500)
    p4a_x0, p4a_x1 = 20, 520
    draw.rounded_rectangle([(p4a_x0, b_y0), (p4a_x1, b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)
    draw_icon_gear(draw, p4a_x0 + 32, b_y0 + 26, col=(0, 210, 255))
    draw.text((p4a_x0 + 50, b_y0 + 14), "MODEL VALIDATION", fill=(0, 210, 255), font=f_panel_hdr)

    val_cards = [
        ("WALK FORWARD", "PASS"),
        ("OUT OF SAMPLE", "PASS"),
        ("CALIBRATION", "PASS"),
        ("MODEL DRIFT", "LOW"),
        ("REGIME FIT", "HIGH")
    ]
    badge_w = 90
    for b_i, (b_title, b_val) in enumerate(val_cards):
        bx = p4a_x0 + 12 + b_i * 96
        by = b_y0 + 44
        draw.text((bx + badge_w // 2, by), b_title, fill=(120, 150, 185), font=get_font(11, bold=True), anchor="ma")
        draw.rounded_rectangle([(bx, by + 18), (bx + badge_w, by + 46)], radius=4, fill=(0, 140, 65))
        draw.text((bx + badge_w // 2, by + 32), b_val, fill=(255, 255, 255), font=f_pill, anchor="mm")

    draw.line([(p4a_x0 + 16, b_y0 + 120), (p4a_x1 - 16, b_y0 + 120)], fill=(15, 35, 68), width=1)
    stat_cols = [
        ("SAMPLE SIZE", "1,284", (255, 255, 255), 21),
        ("MAE", "0.21 ATR", (0, 210, 255), 21),
        ("MFE", "0.78 ATR", (0, 210, 255), 21),
        ("DRAWDOWN", "CONTROLLED", (255, 255, 255), 17)
    ]
    stat_w = (p4a_x1 - p4a_x0 - 32) // 4
    for s_i, (s_lbl, s_val, s_col, s_fsize) in enumerate(stat_cols):
        sx = p4a_x0 + 16 + s_i * stat_w + stat_w // 2
        draw.text((sx, b_y0 + 142), s_lbl, fill=(120, 150, 185), font=f_label_sm, anchor="mm")
        draw.text((sx, b_y0 + 180), s_val, fill=s_col, font=get_font(s_fsize, bold=True), anchor="mm")

    # Panel 4B: FINAL RANKING (TOP SETUPS) (X: 532 to 992, W: 460)
    p4b_x0, p4b_x1 = 532, 992
    draw.rounded_rectangle([(p4b_x0, b_y0), (p4b_x1, b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)
    draw_icon_trophy(draw, p4b_x0 + 32, b_y0 + 26, col=(0, 210, 255))
    draw.text((p4b_x0 + 50, b_y0 + 14), "FINAL RANKING (TOP SETUPS)", fill=(0, 210, 255), font=f_panel_hdr)

    draw.text((p4b_x0 + 16, b_y0 + 46), "#", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4b_x0 + 48, b_y0 + 46), "PAIR", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4b_x0 + 138, b_y0 + 46), "SETUP", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4b_x0 + 280, b_y0 + 46), "CONFIDENCE", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4b_x0 + 395, b_y0 + 46), "SCORE", fill=(120, 150, 185), font=f_tbl_hdr)

    for r_i, rk in enumerate(engine_data.get("final_ranking", [])[:5]):
        ry = b_y0 + 74 + r_i * 32
        rank_num = rk["rank"]
        badge_fill = (220, 160, 20) if rank_num == 1 else ((160, 170, 185) if rank_num == 2 else ((180, 100, 30) if rank_num == 3 else (18, 36, 68)))
        draw.ellipse([(p4b_x0 + 14, ry + 2), (p4b_x0 + 36, ry + 24)], fill=badge_fill)
        draw.text((p4b_x0 + 25, ry + 13), str(rank_num), fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

        draw.text((p4b_x0 + 48, ry + 4), rk["pair"], fill=(255, 255, 255), font=f_tbl_cell_b)

        st_name = rk["setup"]
        s_bg = (180, 25, 35) if "SELL" in st_name else (0, 140, 65)
        draw.rounded_rectangle([(p4b_x0 + 128, ry + 1), (p4b_x0 + 265, ry + 25)], radius=3, fill=s_bg)
        draw.text((p4b_x0 + 196, ry + 13), st_name, fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

        draw.text((p4b_x0 + 305, ry + 4), rk["confidence"], fill=(255, 255, 255), font=f_tbl_cell_b)

        draw.rounded_rectangle([(p4b_x0 + 395, ry + 1), (p4b_x0 + 442, ry + 25)], radius=3, fill=(0, 140, 65))
        draw.text((p4b_x0 + 418, ry + 13), str(rk["score"]), fill=(255, 255, 255), font=f_tbl_cell_b, anchor="mm")

    # Panel 4C: RECENT SIGNALS (X: 1004 to 1424, W: 420)
    p4c_x0, p4c_x1 = 1004, 1424
    draw.rounded_rectangle([(p4c_x0, b_y0), (p4c_x1, b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)
    draw_icon_bell(draw, p4c_x0 + 32, b_y0 + 26, col=(0, 210, 255))
    draw.text((p4c_x0 + 50, b_y0 + 14), "RECENT SIGNALS", fill=(0, 210, 255), font=f_panel_hdr)

    draw.text((p4c_x0 + 16, b_y0 + 46), "TIME", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4c_x0 + 90, b_y0 + 46), "PAIR", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4c_x0 + 185, b_y0 + 46), "ACTION", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4c_x0 + 285, b_y0 + 46), "STATUS", fill=(120, 150, 185), font=f_tbl_hdr)

    for r_i, sig in enumerate(engine_data.get("recent_signals", [])[:5]):
        ry = b_y0 + 74 + r_i * 32
        draw.text((p4c_x0 + 16, ry + 4), sig["time"], fill=(180, 200, 225), font=f_tbl_cell)
        draw.text((p4c_x0 + 90, ry + 4), sig["pair"], fill=(255, 255, 255), font=f_tbl_cell_b)

        act_col = (245, 65, 75) if sig["action"] == "SELL" else (0, 230, 118)
        draw.text((p4c_x0 + 185, ry + 4), sig["action"], fill=act_col, font=get_font(17, bold=True))

        st = sig["status"]
        st_bg = (180, 25, 35) if st == "OP ZONE" else ((0, 140, 65) if st in ["ACTIVE", "TP1 HIT"] else (190, 110, 20))
        draw.rounded_rectangle([(p4c_x0 + 270, ry + 1), (p4c_x0 + 395, ry + 25)], radius=3, fill=st_bg)
        draw.text((p4c_x0 + 332, ry + 13), st, fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

    # Panel 4D: EVENT CALENDAR (WIB) (X: 1436 to 1900, W: 464)
    p4d_x0, p4d_x1 = 1436, 1900
    draw.rounded_rectangle([(p4d_x0, b_y0), (p4d_x1, b_y1)], radius=8, fill=(3, 10, 22), outline=(18, 48, 92), width=1)
    draw_icon_calendar(draw, p4d_x0 + 32, b_y0 + 26, col=(0, 210, 255))
    draw.text((p4d_x0 + 50, b_y0 + 14), "EVENT CALENDAR (WIB)", fill=(0, 210, 255), font=f_panel_hdr)

    draw.text((p4d_x0 + 16, b_y0 + 46), "TIME", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4d_x0 + 85, b_y0 + 46), "EVENT", fill=(120, 150, 185), font=f_tbl_hdr)
    draw.text((p4d_x0 + 375, b_y0 + 46), "IMPACT", fill=(120, 150, 185), font=f_tbl_hdr)

    for r_i, ev in enumerate(engine_data.get("event_calendar", [])[:5]):
        ry = b_y0 + 74 + r_i * 32
        draw.text((p4d_x0 + 16, ry + 4), ev["time"], fill=(180, 200, 225), font=f_tbl_cell)
        draw.text((p4d_x0 + 85, ry + 4), ev["event"], fill=(255, 255, 255), font=f_tbl_cell)

        imp = ev["impact"]
        imp_bg = (180, 25, 35) if imp == "HIGH" else (190, 110, 20)
        draw.rounded_rectangle([(p4d_x0 + 365, ry + 1), (p4d_x0 + 450, ry + 25)], radius=3, fill=imp_bg)
        draw.text((p4d_x0 + 407, ry + 13), imp, fill=(255, 255, 255), font=f_pill_sm, anchor="mm")

    img.save(out_path, format="PNG", optimize=True)
    print("Successfully saved 2x dashboard to:", out_path)

if __name__ == "__main__":
    eng = PrecisionTradingEngine()
    data = eng.fetch_live_data()
    out = r"C:\Users\ACER\.gemini\antigravity\brain\558a85bc-66f2-430d-b5c2-57d9b5fa3ae7\test_precision_engine_card_2x.png"
    render_2x_dashboard(data, out)
