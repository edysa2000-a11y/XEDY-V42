import os
import io
import math
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

WIB = timezone(timedelta(hours=7))

def get_font(size: int, bold: bool = False):
    font_candidates = [
        # Windows
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        # Linux / Ubuntu (GitHub Actions)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_dashed_line(draw, x1, y, x2, color, dash_len=8, gap_len=6, width=2):
    curr_x = x1
    while curr_x < x2:
        end_x = min(curr_x + dash_len, x2)
        draw.line([(curr_x, y), (end_x, y)], fill=color, width=width)
        curr_x += dash_len + gap_len

def draw_vector_lock(draw, center_x, center_y, color=(255, 255, 255)):
    w, h = 14, 11
    x1, y1 = center_x - w // 2, center_y - 1
    x2, y2 = x1 + w, y1 + h
    draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=2, fill=color)
    sw = 8
    sx1 = center_x - sw // 2
    sx2 = sx1 + sw
    sy1 = y1 - 7
    draw.arc([(sx1, sy1), (sx2, sy1 + 9)], start=180, end=0, fill=color, width=2)
    draw.line([(sx1, sy1 + 5), (sx1, y1)], fill=color, width=2)
    draw.line([(sx2, sy1 + 5), (sx2, y1)], fill=color, width=2)

def draw_arrow_up(draw, x, y, size=7, color=(239, 68, 68)):
    points = [(x, y - size), (x + size, y + size), (x - size, y + size)]
    draw.polygon(points, fill=color)

def draw_arrow_down(draw, x, y, size=7, color=(34, 197, 94)):
    points = [(x, y + size), (x + size, y - size), (x - size, y - size)]
    draw.polygon(points, fill=color)

def draw_calendar_icon(draw, x, y, color=(255, 204, 51)):
    draw.rounded_rectangle([(x, y), (x + 18, y + 16)], radius=3, outline=color, width=2)
    draw.line([(x, y + 5), (x + 18, y + 5)], fill=color, width=2)
    draw.line([(x + 4, y - 2), (x + 4, y + 2)], fill=color, width=2)
    draw.line([(x + 14, y - 2), (x + 14, y + 2)], fill=color, width=2)

def draw_clock_icon(draw, x, y, color=(200, 215, 230)):
    r = 8
    draw.ellipse([(x, y), (x + r*2, y + r*2)], outline=color, width=2)
    draw.line([(x + r, y + 3), (x + r, y + r)], fill=color, width=2)
    draw.line([(x + r, y + r), (x + r + 4, y + r)], fill=color, width=2)

def create_sr_card_image(
    xau_price: float = 4285.00,
    xau_support: float = 4220.00,
    xau_resistance: float = 4580.00,
    xau_status: str = "NORMAL",
    jpy_price: float = 157.29,
    jpy_support: float = 152.80,
    jpy_resistance: float = 158.30,
    jpy_status: str = "NORMAL",
    now_wib: datetime = None,
    period_str: str = "27 Sep – 4 Oct 2026",
    is_market_closed: bool = None,
    orientation: str = "vertical"  # "vertical" (Mobile Portrait) or "horizontal" (Desktop Landscape)
) -> Image.Image:
    """
    Renders high-definition Weekly S/R Monitor graphic card.
    Defaults to 'vertical' stack (760x1280) for optimal mobile Telegram viewing.
    """
    if now_wib is None:
        now_wib = datetime.now(WIB)
    
    if is_market_closed is None:
        is_market_closed = now_wib.weekday() in [5, 6]

    if orientation == "horizontal":
        WIDTH, HEIGHT = 1280, 720
    else:
        WIDTH, HEIGHT = 760, 1280

    im = Image.new("RGBA", (WIDTH, HEIGHT), (8, 12, 22, 255))
    draw = ImageDraw.Draw(im)

    # Global background border
    draw.rounded_rectangle([(10, 10), (WIDTH - 10, HEIGHT - 10)], radius=24, outline=(28, 42, 65, 255), width=2)

    # ----------------- TOP HEADER BAR -----------------
    if orientation == "vertical":
        # Row 1: Title & Period Pill
        draw_calendar_icon(draw, 26, 28, (255, 204, 51))
        font_title = get_font(21, bold=True)
        draw.text((52, 24), "WEEKLY S/R MONITOR", fill=(255, 204, 51), font=font_title)

        font_sub = get_font(13, bold=True)
        draw.rounded_rectangle([(WIDTH - 235, 22), (WIDTH - 24, 54)], radius=14, fill=(16, 25, 42), outline=(42, 60, 88), width=1)
        draw.text((WIDTH - 220, 28), period_str, fill=(230, 240, 255), font=font_sub)

        # Row 2: Update Time & Market Status
        update_w = 330
        draw.rounded_rectangle([(24, 62), (24 + update_w, 96)], radius=14, fill=(16, 25, 42), outline=(42, 60, 88), width=1)
        draw_clock_icon(draw, 36, 71, (180, 205, 230))
        update_str = f"UPDATE : {now_wib.strftime('%d %b %Y %H:%M WIB')}"
        draw.text((60, 69), update_str, fill=(200, 220, 240), font=get_font(12, bold=False))

        # Market Status Pill
        status_x1 = 24 + update_w + 12
        status_x2 = WIDTH - 24
        draw.rounded_rectangle([(status_x1, 62), (status_x2, 96)], radius=14, fill=(16, 28, 38) if is_market_closed else (16, 38, 28), outline=(38, 55, 75) if is_market_closed else (38, 75, 55), width=1)
        st_dot_color = (34, 197, 94)
        draw.ellipse([(status_x1 + 14, 74), (status_x1 + 24, 84)], fill=st_dot_color)
        if is_market_closed:
            draw.text((status_x1 + 32, 67), "MARKET CLOSED", fill=(34, 197, 94), font=get_font(11, bold=True))
            draw.text((status_x1 + 32, 80), "Next: 28 Sep 07:00 WIB", fill=(140, 160, 180), font=get_font(9, bold=False))
        else:
            draw.text((status_x1 + 32, 72), "MARKET OPEN (LIVE 1M)", fill=(34, 220, 94), font=get_font(11, bold=True))

    else:
        # Horizontal Layout Header
        draw_calendar_icon(draw, 34, 30, (255, 204, 51))
        font_title = get_font(23, bold=True)
        draw.text((62, 24), "WEEKLY S/R MONITOR", fill=(255, 204, 51), font=font_title)

        font_sub = get_font(14, bold=True)
        draw.rounded_rectangle([(370, 24), (560, 56)], radius=16, fill=(16, 25, 42), outline=(42, 60, 88), width=1)
        draw.text((395, 30), period_str, fill=(230, 240, 255), font=font_sub)

        draw.rounded_rectangle([(580, 24), (840, 56)], radius=16, fill=(16, 25, 42), outline=(42, 60, 88), width=1)
        draw_clock_icon(draw, 596, 32, (180, 205, 230))
        update_str = f"UPDATE : {now_wib.strftime('%d %b %Y %H:%M WIB')}"
        draw.text((622, 30), update_str, fill=(200, 220, 240), font=get_font(13, bold=False))

        if is_market_closed:
            draw.rounded_rectangle([(860, 22), (1244, 58)], radius=18, fill=(16, 28, 38), outline=(38, 55, 75), width=1)
            draw.ellipse([(878, 35), (888, 45)], fill=(34, 197, 94))
            draw.text((898, 26), "MARKET CLOSED", fill=(34, 197, 94), font=get_font(12, bold=True))
            draw.text((898, 41), "Next Update: 28 Sep 2026 07:00 WIB", fill=(140, 160, 180), font=get_font(10, bold=False))
        else:
            draw.rounded_rectangle([(960, 22), (1244, 58)], radius=18, fill=(16, 38, 28), outline=(38, 75, 55), width=1)
            draw.ellipse([(978, 35), (988, 45)], fill=(34, 220, 94))
            draw.text((998, 31), "MARKET OPEN (LIVE 1M)", fill=(34, 220, 94), font=get_font(13, bold=True))

    # ----------------- PANEL RENDER FUNCTION -----------------
    def render_panel(
        box_left, box_top, box_right, box_bottom,
        symbol, title_sub, price, supp, res, status, digits,
        theme_color, border_color, is_gold=False, near_pct=0.003
    ):
        draw.rounded_rectangle([(box_left, box_top), (box_right, box_bottom)], radius=20, fill=(13, 20, 32), outline=border_color, width=2)
        
        card_w = box_right - box_left
        center_x = box_left + card_w // 2

        # Header: Symbol & Subtitle (Centered)
        font_sym = get_font(32, bold=True)
        sym_bbox = font_sym.getbbox(symbol)
        sym_w = sym_bbox[2] - sym_bbox[0]
        draw.text((center_x - sym_w // 2, box_top + 16), symbol, fill=theme_color, font=font_sym)

        font_desc = get_font(12, bold=True)
        desc_bbox = font_desc.getbbox(title_sub)
        desc_w = desc_bbox[2] - desc_bbox[0]
        draw.text((center_x - desc_w // 2, box_top + 54), title_sub, fill=(155, 175, 195), font=font_desc)

        # Badge Top Right (Weekly S/R)
        draw.rounded_rectangle([(box_right - 185, box_top + 18), (box_right - 20, box_top + 56)], radius=10, fill=(20, 28, 44), outline=(45, 60, 85), width=1)
        draw.text((box_right - 170, box_top + 22), "WEEKLY S/R", fill=(255, 204, 51), font=get_font(11, bold=True))
        draw.text((box_right - 170, box_top + 38), period_str, fill=(160, 180, 200), font=get_font(9, bold=False))

        # 1. RESISTANCE PILL
        pill_w = min(card_w - 60, 360)
        pill_h = 44
        pill_rx1 = center_x - pill_w // 2
        pill_ry1 = box_top + 88
        pill_rx2 = pill_rx1 + pill_w
        pill_ry2 = pill_ry1 + pill_h
        draw.rounded_rectangle([(pill_rx1, pill_ry1), (pill_rx2, pill_ry2)], radius=12, fill=(185, 28, 28), outline=(239, 68, 68), width=1)
        draw.text((pill_rx1 + 22, pill_ry1 + 12), "RESISTANCE", fill=(254, 226, 226), font=get_font(15, bold=True))
        res_str = f"{res:.{digits}f}"
        draw.text((pill_rx2 - 145, pill_ry1 + 9), res_str, fill=(255, 255, 255), font=get_font(21, bold=True))
        draw_vector_lock(draw, pill_rx2 - 25, pill_ry1 + 22, (255, 255, 255))

        # Dashed Resistance line
        draw_dashed_line(draw, box_left + 25, pill_ry2 + 10, box_right - 25, (220, 38, 38), dash_len=8, gap_len=6, width=2)

        # Distance to Resistance
        dist_r = res - price
        dist_r_pct = (dist_r / res) * 100 if res > 0 else 0
        r_sign = "+" if dist_r >= 0 else ""
        dist_r_text = f"{r_sign}{dist_r:.{digits}f}  ({dist_r_pct:.2f}%)"
        draw_arrow_up(draw, center_x - 70, pill_ry2 + 28, size=6, color=(248, 113, 113))
        draw.text((center_x - 55, pill_ry2 + 20), dist_r_text, fill=(248, 113, 113), font=get_font(15, bold=True))

        # 2. CURRENT PRICE PILL (Center Prominent)
        cp_w = min(card_w - 120, 280)
        cp_h = 60
        cp_x1 = center_x - cp_w // 2
        cp_y1 = box_top + 185
        cp_x2 = cp_x1 + cp_w
        cp_y2 = cp_y1 + cp_h
        
        bg_cp = (55, 42, 10) if is_gold else (10, 42, 85)
        border_cp = (234, 179, 8) if is_gold else (59, 130, 246)
        draw.rounded_rectangle([(cp_x1, cp_y1), (cp_x2, cp_y2)], radius=14, fill=bg_cp, outline=border_cp, width=2)
        
        font_cp_lbl = get_font(11, bold=True)
        lbl_bbox = font_cp_lbl.getbbox("CURRENT PRICE")
        lbl_w = lbl_bbox[2] - lbl_bbox[0]
        draw.text((center_x - lbl_w // 2, cp_y1 + 8), "CURRENT PRICE", fill=(210, 230, 255), font=font_cp_lbl)
        
        price_str = f"{price:.{digits}f}"
        font_cp = get_font(27, bold=True)
        p_bbox = font_cp.getbbox(price_str)
        p_w = p_bbox[2] - p_bbox[0]
        draw.text((center_x - p_w // 2, cp_y1 + 24), price_str, fill=(255, 255, 255), font=font_cp)

        # Distance to Support
        dist_s = price - supp
        dist_s_pct = (dist_s / supp) * 100 if supp > 0 else 0
        s_sign = "+" if dist_s >= 0 else ""
        dist_s_text = f"{s_sign}{dist_s:.{digits}f}  ({dist_s_pct:.2f}%)"
        draw_arrow_down(draw, center_x - 70, cp_y2 + 25, size=6, color=(74, 222, 128))
        draw.text((center_x - 55, cp_y2 + 16), dist_s_text, fill=(74, 222, 128), font=get_font(15, bold=True))

        # Dashed Support line
        draw_dashed_line(draw, box_left + 25, box_top + 308, box_right - 25, (22, 163, 74), dash_len=8, gap_len=6, width=2)

        # 3. SUPPORT PILL
        pill_sy1 = box_top + 320
        pill_sy2 = pill_sy1 + pill_h
        draw.rounded_rectangle([(pill_rx1, pill_sy1), (pill_rx2, pill_sy2)], radius=12, fill=(21, 128, 61), outline=(34, 197, 94), width=1)
        draw.text((pill_rx1 + 32, pill_sy1 + 12), "SUPPORT", fill=(220, 252, 231), font=get_font(15, bold=True))
        supp_str = f"{supp:.{digits}f}"
        draw.text((pill_rx2 - 145, pill_sy1 + 9), supp_str, fill=(255, 255, 255), font=get_font(21, bold=True))
        draw_vector_lock(draw, pill_rx2 - 25, pill_sy1 + 22, (255, 255, 255))

        # 4. BOTTOM 4 METRIC BOXES
        grid_y1 = box_top + 382
        grid_y2 = grid_y1 + 72
        spacing = 8
        gw = (card_w - 50 - (spacing * 3)) // 4

        near_s_thresh = supp + (supp * near_pct)
        near_r_thresh = res - (res * near_pct)
        pct_label = f"({near_pct*100:.1f}%)"

        # Box 1: Distance to Support
        bx1 = box_left + 25
        bx2 = bx1 + gw
        draw.rounded_rectangle([(bx1, grid_y1), (bx2, grid_y2)], radius=8, fill=(17, 26, 42), outline=(35, 50, 72), width=1)
        draw.text((bx1 + 8, grid_y1 + 6), "Distance to Support", fill=(145, 165, 185), font=get_font(10, bold=False))
        draw_arrow_down(draw, bx1 + 18, grid_y1 + 35, size=5, color=(74, 222, 128))
        draw.text((bx1 + 30, grid_y1 + 25), f"{dist_s:.{digits}f}", fill=(74, 222, 128), font=get_font(16, bold=True))
        draw.text((bx1 + 30, grid_y1 + 49), f"({dist_s_pct:.2f}%)", fill=(130, 150, 170), font=get_font(11, bold=False))

        # Box 2: Distance to Resistance
        bx1 = bx2 + spacing
        bx2 = bx1 + gw
        draw.rounded_rectangle([(bx1, grid_y1), (bx2, grid_y2)], radius=8, fill=(17, 26, 42), outline=(35, 50, 72), width=1)
        draw.text((bx1 + 8, grid_y1 + 6), "Distance to Resistance", fill=(145, 165, 185), font=get_font(10, bold=False))
        draw_arrow_up(draw, bx1 + 18, grid_y1 + 35, size=5, color=(248, 113, 113))
        draw.text((bx1 + 30, grid_y1 + 25), f"{dist_r:.{digits}f}", fill=(248, 113, 113), font=get_font(16, bold=True))
        draw.text((bx1 + 30, grid_y1 + 49), f"({dist_r_pct:.2f}%)", fill=(130, 150, 170), font=get_font(11, bold=False))

        # Box 3: Status
        bx1 = bx2 + spacing
        bx2 = bx1 + gw
        draw.rounded_rectangle([(bx1, grid_y1), (bx2, grid_y2)], radius=8, fill=(17, 26, 42), outline=(35, 50, 72), width=1)
        draw.text((bx1 + 10, grid_y1 + 6), "Status", fill=(145, 165, 185), font=get_font(10, bold=False))
        st_color = (34, 197, 94) if "NORMAL" in status else ((239, 68, 68) if ("BREAK" in status) else (234, 179, 8))
        draw.ellipse([(bx1 + 10, grid_y1 + 30), (bx1 + 22, grid_y1 + 42)], fill=st_color)
        draw.text((bx1 + 28, grid_y1 + 25), status, fill=st_color, font=get_font(14, bold=True))
        draw.text((bx1 + 28, grid_y1 + 49), "No Alert", fill=(130, 150, 170), font=get_font(11, bold=False))

        # Box 4: Near Level
        bx1 = bx2 + spacing
        bx2 = bx1 + gw
        draw.rounded_rectangle([(bx1, grid_y1), (bx2, grid_y2)], radius=8, fill=(17, 26, 42), outline=(35, 50, 72), width=1)
        draw.text((bx1 + 8, grid_y1 + 6), f"Near Level {pct_label}", fill=(145, 165, 185), font=get_font(10, bold=False))
        draw.text((bx1 + 8, grid_y1 + 27), f"Near S <= {near_s_thresh:.{digits}f}", fill=(190, 210, 230), font=get_font(11, bold=False))
        draw.text((bx1 + 8, grid_y1 + 47), f"Near R >= {near_r_thresh:.{digits}f}", fill=(190, 210, 230), font=get_font(11, bold=False))

        # 5. BOTTOM POSITION GAUGE / SLIDER BAR
        bar_x1 = box_left + 35
        bar_x2 = box_right - 35
        bar_y = box_top + 476
        bar_h = 10
        bar_w = bar_x2 - bar_x1

        # Draw gradient gauge bar (Green -> Yellow -> Red)
        for i in range(bar_w):
            ratio = i / float(bar_w)
            if ratio < 0.5:
                r_col = int(34 + (234 - 34) * (ratio * 2))
                g_col = int(197 + (179 - 197) * (ratio * 2))
                b_col = int(94 + (8 - 94) * (ratio * 2))
            else:
                r_col = int(234 + (239 - 234) * ((ratio - 0.5) * 2))
                g_col = int(179 + (68 - 179) * ((ratio - 0.5) * 2))
                b_col = int(8 + (68 - 8) * ((ratio - 0.5) * 2))
            draw.line([(bar_x1 + i, bar_y), (bar_x1 + i, bar_y + bar_h)], fill=(r_col, g_col, b_col), width=1)

        # Calculate position of current price
        span = res - supp
        pos_ratio = 0.5
        if span > 0:
            pos_ratio = max(0.0, min(1.0, (price - supp) / span))
        
        diamond_x = int(bar_x1 + (bar_w * pos_ratio))
        diamond_y = bar_y + bar_h // 2
        d_size = 9

        # Draw Diamond Marker
        diamond_points = [
            (diamond_x, diamond_y - d_size),
            (diamond_x + d_size, diamond_y),
            (diamond_x, diamond_y + d_size),
            (diamond_x - d_size, diamond_y)
        ]
        draw.polygon(diamond_points, fill=(255, 255, 255), outline=(0, 0, 0))

        # Labels around gauge
        draw.text((bar_x1, bar_y + 16), f"{supp:.{digits}f}", fill=(34, 197, 94), font=get_font(13, bold=True))
        draw.text((bar_x1, bar_y + 32), "SUPPORT", fill=(130, 150, 170), font=get_font(10, bold=False))

        p_sub_str = f"{price:.{digits}f}"
        font_p_sub = get_font(13, bold=True)
        ps_bbox = font_p_sub.getbbox(p_sub_str)
        ps_w = ps_bbox[2] - ps_bbox[0]
        draw.text((diamond_x - ps_w // 2, bar_y + 16), p_sub_str, fill=(255, 255, 255), font=font_p_sub)

        draw.text((bar_x2 - 60, bar_y + 16), f"{res:.{digits}f}", fill=(239, 68, 68), font=get_font(13, bold=True))
        draw.text((bar_x2 - 70, bar_y + 32), "RESISTANCE", fill=(130, 150, 170), font=get_font(10, bold=False))

    if orientation == "vertical":
        # Panel 1 (Top): XAUUSD
        render_panel(
            box_left=24, box_top=110, box_right=WIDTH - 24, box_bottom=670,
            symbol="XAUUSD", title_sub="GOLD SPOT",
            price=xau_price, supp=xau_support, res=xau_resistance, status=xau_status, digits=2,
            theme_color=(245, 176, 65), border_color=(130, 95, 25), is_gold=True, near_pct=0.005
        )

        # Panel 2 (Bottom): USDJPY
        render_panel(
            box_left=24, box_top=695, box_right=WIDTH - 24, box_bottom=1255,
            symbol="USDJPY", title_sub="U.S. DOLLAR / JAPANESE YEN",
            price=jpy_price, supp=jpy_support, res=jpy_resistance, status=jpy_status, digits=2,
            theme_color=(235, 245, 255), border_color=(35, 90, 145), is_gold=False, near_pct=0.003
        )
    else:
        # Side-by-side
        render_panel(
            box_left=24, box_top=80, box_right=626, box_bottom=HEIGHT - 24,
            symbol="XAUUSD", title_sub="GOLD SPOT",
            price=xau_price, supp=xau_support, res=xau_resistance, status=xau_status, digits=2,
            theme_color=(245, 176, 65), border_color=(130, 95, 25), is_gold=True, near_pct=0.005
        )
        render_panel(
            box_left=654, box_top=80, box_right=WIDTH - 24, box_bottom=HEIGHT - 24,
            symbol="USDJPY", title_sub="U.S. DOLLAR / JAPANESE YEN",
            price=jpy_price, supp=jpy_support, res=jpy_resistance, status=jpy_status, digits=2,
            theme_color=(235, 245, 255), border_color=(35, 90, 145), is_gold=False, near_pct=0.003
        )

    return im

def generate_sr_card_bytes(**kwargs) -> bytes:
    """Convenience function returning PNG bytes directly"""
    img = create_sr_card_image(**kwargs)
    bio = io.BytesIO()
    img.save(bio, format="PNG", optimize=True)
    return bio.getvalue()
