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
        # Linux / Container fallback
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_sphere(draw, cx: int, cy: int, radius: int, base_color: tuple):
    """Draws a smooth 3D-styled sphere orb with realistic lighting gradient."""
    r, g, b = base_color
    for i in range(radius, 0, -1):
        factor = 1.0 - (i / radius) * 0.65
        ox = cx - int((radius - i) * 0.38)
        oy = cy - int((radius - i) * 0.38)
        cr = min(255, int(r + (255 - r) * factor * 0.85))
        cg = min(255, int(g + (255 - g) * factor * 0.85))
        cb = min(255, int(b + (255 - b) * factor * 0.85))
        draw.ellipse([(ox - i, oy - i), (ox + i, oy + i)], fill=(cr, cg, cb))

def draw_gradient_bar(draw, x1: int, y1: int, x2: int, y2: int):
    """Draws a horizontal smooth gradient bar from Green -> Yellow -> Red."""
    width = x2 - x1
    for x in range(width):
        t = x / max(1, width - 1)
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
        
    # Vertical end caps
    draw.line([(x1, y1 - 4), (x1, y2 + 4)], fill=(0, 230, 118), width=2)
    draw.line([(x2, y1 - 4), (x2, y2 + 4)], fill=(255, 68, 68), width=2)

def generate_multi_pair_sr_card(data_list: list, output_path: str = None) -> Image.Image:
    """
    Renders 4-pair SNR Card exactly matching the user's provided blueprint.
    """
    WIDTH, HEIGHT = 980, 520
    im = Image.new("RGB", (WIDTH, HEIGHT), (2, 14, 38)) # Deep rich navy background
    draw = ImageDraw.Draw(im)

    # Outer border: glowing cyan/blue border
    draw.rounded_rectangle([(8, 8), (WIDTH - 8, HEIGHT - 8)], radius=20, outline=(0, 85, 204), width=3)
    # Subtle inner border glow
    draw.rounded_rectangle([(11, 11), (WIDTH - 11, HEIGHT - 11)], radius=18, outline=(0, 45, 120), width=1)

    # Fonts
    font_header = get_font(15, bold=True)
    font_pair = get_font(18, bold=True)
    font_sub = get_font(11, bold=True)
    font_price = get_font(23, bold=True)
    font_change = get_font(12, bold=True)
    font_sr_num = get_font(14, bold=True)
    font_sr_sub = get_font(12, bold=True)
    font_badge = get_font(12, bold=True)
    font_status = get_font(14, bold=True)

    # Column X coordinates
    X_PAIR = 35
    X_PRICE = 205
    X_BAR_START = 380
    X_BAR_END = 770
    X_STATUS = 810
    STATUS_W = 145

    # 1. HEADER ROW
    Y_HDR = 26
    # PAIR
    draw.text((X_PAIR + 30, Y_HDR), "PAIR", fill=(140, 180, 225), font=font_header)
    
    # LIVE PRICE
    draw.text((X_PRICE, Y_HDR - 5), "LIVE\nPRICE", fill=(140, 180, 225), font=get_font(13, bold=True))
    
    # SUPPORT (with green dot)
    draw.ellipse([(X_BAR_START - 20, Y_HDR + 2), (X_BAR_START - 8, Y_HDR + 14)], fill=(0, 230, 118))
    draw.text((X_BAR_START - 3, Y_HDR), "SUPPORT", fill=(140, 180, 225), font=font_header)
    
    # %SNR
    draw.text((int((X_BAR_START + X_BAR_END)/2) - 25, Y_HDR), "%SNR", fill=(140, 180, 225), font=font_header)
    
    # RESISTANCE (with red dot)
    draw.ellipse([(X_BAR_END - 115, Y_HDR + 2), (X_BAR_END - 103, Y_HDR + 14)], fill=(255, 68, 68))
    draw.text((X_BAR_END - 98, Y_HDR), "RESISTANCE", fill=(140, 180, 225), font=font_header)
    
    # STATUS
    draw.text((X_STATUS + 40, Y_HDR), "STATUS", fill=(140, 180, 225), font=font_header)

    # Horizontal divider under header
    draw.line([(20, 68), (WIDTH - 20, 68)], fill=(12, 38, 80), width=2)

    # 2. ROWS
    ROW_HEIGHT = 108
    Y_START = 72

    for i, item in enumerate(data_list):
        row_y = Y_START + i * ROW_HEIGHT
        
        # Horizontal divider between rows
        if i > 0:
            draw.line([(20, row_y), (WIDTH - 20, row_y)], fill=(12, 38, 80), width=1)

        center_y = row_y + 54

        # A. PAIR (Sphere Orb + Name + Subtitle)
        orb_x, orb_y = X_PAIR + 12, center_y - 2
        draw_sphere(draw, orb_x, orb_y, 16, item.get("orb_color", (255, 200, 0)))
        
        name_x = X_PAIR + 38
        pair_color = (255, 204, 0) if item["name"] == "GOLD" else (255, 255, 255)
        draw.text((name_x, center_y - 18), item["name"], fill=pair_color, font=font_pair)
        draw.text((name_x, center_y + 6), item["subtitle"], fill=(100, 140, 190), font=font_sub)

        # B. LIVE PRICE & CHANGE
        price = item["price"]
        digits = item.get("digits", 2)
        price_str = f"{price:,.{digits}f}"
        draw.text((X_PRICE, center_y - 20), price_str, fill=(255, 255, 255), font=font_price)
        
        c_val = item.get("change_val", 0.0)
        c_pct = item.get("change_pct", 0.0)
        c_sign = "+" if c_val >= 0 else ""
        c_color = (0, 230, 118) if c_val >= 0 else (255, 68, 68)
        change_str = f"{c_sign}{c_val:.{digits}f} ({c_sign}{c_pct:.2f}%)"
        draw.text((X_PRICE, center_y + 8), change_str, fill=c_color, font=font_change)

        # C. SUPPORT, GAUGE BAR, RESISTANCE
        supp = item["support"]
        res = item["resistance"]
        bar_y1 = center_y + 1
        bar_y2 = center_y + 11

        # Format S & R numbers
        s_str = f"{int(supp):,}" if digits == 0 or (supp == int(supp) and supp >= 100) else f"{supp:,.{digits}f}"
        r_str = f"{int(res):,}" if digits == 0 or (res == int(res) and res >= 100) else f"{res:,.{digits}f}"

        # Top S & R labels
        draw.text((X_BAR_START, bar_y1 - 24), s_str, fill=(0, 230, 118), font=font_sr_num)
        
        # Right aligned R label
        r_bbox = draw.textbbox((0, 0), r_str, font=font_sr_num)
        r_w = r_bbox[2] - r_bbox[0]
        draw.text((X_BAR_END - r_w, bar_y1 - 24), r_str, fill=(255, 68, 68), font=font_sr_num)

        # Draw the Gradient Bar
        draw_gradient_bar(draw, X_BAR_START, bar_y1, X_BAR_END, bar_y2)

        # Bottom S & R sub-labels
        draw.text((X_BAR_START - 2, bar_y2 + 6), f"S  {s_str}", fill=(110, 145, 185), font=font_sr_sub)
        draw.text((X_BAR_END - r_w - 14, bar_y2 + 6), f"R  {r_str}", fill=(110, 145, 185), font=font_sr_sub)

        # Calculate %SNR
        if res > supp:
            pct_snr = (price - supp) / (res - supp) * 100.0
        else:
            pct_snr = 50.0
        clamped_pct = max(0.0, min(100.0, pct_snr))
        pin_x = int(X_BAR_START + (X_BAR_END - X_BAR_START) * (clamped_pct / 100.0))
        pin_y = int((bar_y1 + bar_y2) / 2)

        # Tooltip Badge (%SNR) above the Pin
        badge_text = f"{pct_snr:.1f}%"
        b_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
        b_w = b_bbox[2] - b_bbox[0] + 16
        b_h = 22
        b_x1 = max(X_BAR_START, min(X_BAR_END - b_w, pin_x - b_w // 2))
        b_x2 = b_x1 + b_w
        b_y1 = bar_y1 - 28
        b_y2 = b_y1 + b_h

        # Badge background: yellow/amber pill
        draw.rounded_rectangle([(b_x1, b_y1), (b_x2, b_y2)], radius=11, fill=(255, 204, 0))
        # Draw badge text (black)
        draw.text((b_x1 + 8, b_y1 + 3), badge_text, fill=(0, 0, 0), font=font_badge)

        # Slider Pin: Glowing white-cyan circle
        draw.ellipse([(pin_x - 9, pin_y - 9), (pin_x + 9, pin_y + 9)], fill=(0, 160, 255), outline=(255, 255, 255), width=2)
        draw.ellipse([(pin_x - 5, pin_y - 5), (pin_x + 5, pin_y + 5)], fill=(255, 255, 255))

        # D. STATUS PILL
        status = item.get("status", "WAIT").upper()
        if status in ["BUY", "NEAR SUPPORT", "TOUCH S", "TOUCH SUPPORT"]:
            st_color = (0, 230, 118) # green
            st_label = "BUY"
        elif status in ["REVERSAL", "NEAR RESISTANCE", "TOUCH R", "TOUCH RESISTANCE"]:
            st_color = (255, 140, 0) # orange
            st_label = "REVERSAL"
        elif status in ["SELL", "BREAKDOWN"]:
            st_color = (255, 68, 68) # red
            st_label = "SELL" if status == "SELL" else "BREAKDOWN"
        elif status in ["BREAKOUT"]:
            st_color = (255, 68, 68) # red
            st_label = "BREAKOUT"
        else: # WAIT / NORMAL
            st_color = (255, 204, 0) # yellow
            st_label = "WAIT"

        pill_x1 = X_STATUS
        pill_y1 = center_y - 19
        pill_x2 = X_STATUS + STATUS_W
        pill_y2 = center_y + 19
        
        # Dark pill container with colored border
        draw.rounded_rectangle([(pill_x1, pill_y1), (pill_x2, pill_y2)], radius=12, fill=(8, 22, 50), outline=st_color, width=2)
        
        # Orb indicator in pill
        draw_sphere(draw, pill_x1 + 22, center_y, 10, st_color)
        
        # Text in pill
        t_bbox = draw.textbbox((0, 0), st_label, font=font_status)
        t_w = t_bbox[2] - t_bbox[0]
        draw.text((pill_x1 + 42 + (STATUS_W - 42 - t_w)//2, center_y - 9), st_label, fill=(255, 255, 255), font=font_status)

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
        x_p = kwargs.get("xau_price", 4160.0)
        x_s = kwargs.get("xau_support", 3855.0)
        x_r = kwargs.get("xau_resistance", 4230.0)
        x_st = kwargs.get("xau_status", "WAIT")
        
        j_p = kwargs.get("jpy_price", 157.80)
        j_s = kwargs.get("jpy_support", 156.20)
        j_r = kwargs.get("jpy_resistance", 159.40)
        j_st = kwargs.get("jpy_status", "WAIT")

        data_list = [
            {
                "name": "GOLD", "subtitle": "XAUUSD", "orb_color": (255, 195, 0),
                "price": x_p, "change_val": 12.50, "change_pct": 0.31, "digits": 2,
                "support": x_s, "resistance": x_r, "status": x_st
            },
            {
                "name": "EURUSD", "subtitle": "EUR/USD", "orb_color": (0, 140, 255),
                "price": 1.1248, "change_val": 0.0021, "change_pct": 0.19, "digits": 4,
                "support": 1.1100, "resistance": 1.1320, "status": "WAIT"
            },
            {
                "name": "OIL", "subtitle": "WTI CRUDE", "orb_color": (60, 65, 75),
                "price": 89.42, "change_val": 0.58, "change_pct": 0.65, "digits": 2,
                "support": 87.90, "resistance": 99.10, "status": "BUY"
            },
            {
                "name": "USDJPY", "subtitle": "USD/JPY", "orb_color": (160, 50, 255),
                "price": j_p, "change_val": 0.35, "change_pct": 0.22, "digits": 2,
                "support": j_s, "resistance": j_r, "status": j_st
            }
        ]

    im = generate_multi_pair_sr_card(data_list)
    buf = io.BytesIO()
    im.save(buf, format="PNG", quality=95)
    return buf.getvalue()

def create_sr_card_image(*args, **kwargs) -> Image.Image:
    """Backwards compatibility alias."""
    raw = generate_sr_card_bytes(**kwargs)
    return Image.open(io.BytesIO(raw))
