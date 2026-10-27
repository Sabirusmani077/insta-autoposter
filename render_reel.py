import os, sys, random, math, subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
import imageio_ffmpeg

# Ensure UTF-8 printing
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920

FONTS_DIR = os.path.join(ROOT, "fonts")
FB_PATH = os.path.join(FONTS_DIR, "NotoSansDevanagari-Bold.ttf")
FR_PATH = os.path.join(FONTS_DIR, "NotoSansDevanagari-Regular.ttf")
FL_PATH = os.path.join(FONTS_DIR, "Roboto-Regular.ttf")

WATERMARK = "@sabir_usmani_077"

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    except Exception:
        return ImageFont.truetype(path, size)

def get_latin_font(size):
    if os.path.exists(FL_PATH):
        return get_font(FL_PATH, size)
    for p in ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/freefont/FreeSans.ttf"]:
        if os.path.exists(p):
            return get_font(p, size)
    return get_font(FR_PATH, size)

def create_gradient(stops):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        for i in range(len(stops) - 1):
            a, ca = stops[i]; b, cb = stops[i + 1]
            if a <= t <= b:
                k = (t - a) / (b - a)
                c = tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(3))
                break
        d.line((0, y, W, y), fill=c)
    return img

def add_glow(img, cx, cy, r, color):
    g = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(g).ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    return ImageChops.add(img, g.filter(ImageFilter.GaussianBlur(max(2, int(r / 1.6)))))

def draw_ridge(img, base_y, amp, color, seed):
    random.seed(seed)
    d = ImageDraw.Draw(img)
    phases = [random.uniform(0, 6) for _ in range(4)]
    pts = []
    for x in range(0, W + 10, 10):
        y = base_y - sum((amp / (i + 1)) * math.sin(x / (150 / (i + 1)) + phases[i]) for i in range(4))
        pts.append((x, y))
    pts.extend([(W, H), (0, H)])
    d.polygon(pts, fill=color)

def draw_stars(img, count, y_max=1200, seed=42):
    random.seed(seed)
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x = random.randint(0, W)
        y = random.randint(0, y_max)
        r = random.choice([1, 1, 1, 2])
        alpha = random.randint(120, 255)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(alpha, alpha, alpha))

# --- 16 DIVERSE PROCEDURAL THEMES ---

def bg_mountains(qid):
    stops = [(0, (8, 12, 28)), (0.45, (18, 22, 54)), (0.8, (28, 18, 48)), (1, (10, 8, 20))]
    img = create_gradient(stops)
    draw_stars(img, 140, y_max=1300, seed=qid * 7)
    # Moon in upper sky
    img = add_glow(img, 820, 340, 160, (60, 70, 120))
    d = ImageDraw.Draw(img)
    d.ellipse((820 - 45, 340 - 45, 820 + 45, 340 + 45), fill=(240, 240, 255))
    # 3 Layered Mountain Ridges
    draw_ridge(img, 1380, 70, (32, 28, 56), qid * 3 + 1)
    draw_ridge(img, 1540, 85, (20, 18, 40), qid * 3 + 2)
    draw_ridge(img, 1720, 100, (10, 9, 22), qid * 3 + 3)
    return img, (255, 215, 130), (235, 195, 110)

def bg_desert_dunes(qid):
    stops = [(0, (35, 14, 24)), (0.45, (95, 35, 36)), (0.75, (175, 80, 42)), (1, (45, 18, 14))]
    img = create_gradient(stops)
    # Radiant Golden Sun setting on horizon
    img = add_glow(img, 540, 1320, 360, (180, 80, 30))
    d = ImageDraw.Draw(img)
    d.ellipse((540 - 110, 1320 - 110, 540 + 110, 1320 + 110), fill=(255, 225, 160))
    # 3 Sweeping Dune curves
    for i, (base_y, amp, col) in enumerate([
        (1440, 50, (130, 52, 32)),
        (1580, 65, (85, 32, 20)),
        (1740, 75, (45, 16, 12))
    ]):
        random.seed(qid * 11 + i)
        ph = random.uniform(0, 6)
        pts = [(x, base_y - amp * math.sin(x / 240.0 + ph)) for x in range(0, W + 10, 10)]
        pts.extend([(W, H), (0, H)])
        d.polygon(pts, fill=col)
    return img, (255, 215, 130), (255, 185, 100)

def bg_cosmic_nebula(qid):
    stops = [(0, (6, 6, 20)), (0.4, (14, 10, 34)), (0.75, (26, 14, 46)), (1, (8, 6, 16))]
    img = create_gradient(stops)
    # Luminous colorful nebula dust clouds
    img = add_glow(img, 280, 480, 280, (45, 20, 85))
    img = add_glow(img, 820, 1350, 320, (20, 55, 95))
    img = add_glow(img, 540, 960, 300, (60, 25, 75))
    draw_stars(img, 220, y_max=1920, seed=qid * 13)
    # 6 Bright Cross-spike Stars
    d = ImageDraw.Draw(img)
    random.seed(qid * 19)
    for _ in range(6):
        sx, sy = random.randint(100, W - 100), random.randint(200, 1700)
        if 600 < sy < 1250:
            continue
        d.line((sx - 14, sy, sx + 14, sy), fill=(255, 255, 255), width=2)
        d.line((sx, sy - 14, sx, sy + 14), fill=(255, 255, 255), width=2)
        d.ellipse((sx - 3, sy - 3, sx + 3, sy + 3), fill=(255, 255, 255))
    return img, (210, 205, 255), (180, 195, 250)

def bg_synthwave_grid(qid):
    stops = [(0, (18, 8, 38)), (0.45, (60, 20, 72)), (0.7, (130, 40, 80)), (0.72, (20, 10, 35)), (1, (10, 5, 20))]
    img = create_gradient(stops)
    # Glowing Neon Sun at horizon
    img = add_glow(img, 540, 1350, 280, (220, 40, 120))
    d = ImageDraw.Draw(img)
    d.ellipse((540 - 110, 1350 - 110, 540 + 110, 1350 + 110), fill=(255, 215, 90))
    # Horizontal sun slice stripes
    for sy in range(1290, 1360, 14):
        d.line((540 - 110, sy, 540 + 110, sy), fill=(130, 40, 80), width=4)
    # Perspective Grid below horizon (Y: 1360 to 1920)
    vp_x, vp_y = 540, 1360
    # Radial perspective rays
    for angle_x in range(-500, W + 600, 120):
        d.line((vp_x, vp_y, angle_x, H), fill=(210, 50, 150), width=1)
    # Horizontal grid lines (exponential spacing)
    cur_y = 1380
    gap = 8
    while cur_y < H:
        d.line((0, cur_y, W, cur_y), fill=(0, 220, 240), width=1)
        cur_y += gap
        gap = int(gap * 1.35)
    return img, (255, 120, 190), (0, 230, 245)

def bg_misty_forest(qid):
    stops = [(0, (6, 20, 24)), (0.45, (12, 45, 48)), (0.8, (20, 70, 65)), (1, (8, 24, 26))]
    img = create_gradient(stops)
    # Misty pale moon
    img = add_glow(img, 280, 360, 150, (30, 95, 90))
    d = ImageDraw.Draw(img)
    d.ellipse((280 - 45, 360 - 45, 280 + 45, 360 + 45), fill=(215, 250, 240))
    # Draw pine tree rows
    def draw_pine_row(base_y, tree_h, col, step, seed):
        random.seed(seed)
        for tx in range(0, W + 60, step):
            th = tree_h + random.randint(-15, 20)
            # 3 overlapping triangles for each tree
            for tier in range(3):
                top_y = base_y - th + tier * int(th * 0.28)
                bot_y = base_y - int(th * 0.1) + tier * int(th * 0.28)
                half_w = int((tier + 1) * 14)
                d.polygon([(tx, top_y), (tx - half_w, bot_y), (tx + half_w, bot_y)], fill=col)
    draw_pine_row(1460, 110, (25, 75, 70), 55, qid * 5 + 1)
    # Mist bar
    img = add_glow(img, 540, 1490, 180, (20, 80, 75))
    d = ImageDraw.Draw(img)
    draw_pine_row(1620, 140, (16, 50, 48), 65, qid * 5 + 2)
    draw_pine_row(1800, 170, (8, 28, 28), 80, qid * 5 + 3)
    d.rectangle([(0, 1800), (W, H)], fill=(8, 28, 28))
    return img, (170, 245, 220), (130, 230, 200)

def bg_ocean_horizon(qid):
    stops = [(0, (26, 16, 52)), (0.4, (92, 38, 72)), (0.7, (185, 82, 65)), (1, (14, 24, 42))]
    img = create_gradient(stops)
    # Golden setting sun on waterline
    img = add_glow(img, 540, 1360, 240, (255, 140, 50))
    d = ImageDraw.Draw(img)
    d.ellipse((540 - 75, 1360 - 75, 540 + 75, 1360 + 75), fill=(255, 225, 150))
    # Ocean waterline
    d.line((0, 1360, W, 1360), fill=(255, 180, 100), width=2)
    # Shimmering horizontal reflection bars in water
    random.seed(qid * 17)
    for ry in range(1370, H, 14):
        dist = (ry - 1360) / (H - 1360)
        spread = int(120 + dist * 320)
        for _ in range(3):
            rx = 540 + random.randint(-spread, spread)
            rlen = random.randint(20, 70)
            col_a = int(220 * (1 - dist * 0.7))
            d.line((rx - rlen, ry, rx + rlen, ry), fill=(255, 210, 140), width=1)
    return img, (255, 205, 135), (255, 175, 95)

def bg_luxury_gold_deco(qid):
    stops = [(0, (14, 14, 18)), (0.45, (22, 22, 28)), (0.8, (32, 30, 36)), (1, (12, 12, 15))]
    img = create_gradient(stops)
    # Ambient warm champagne center glow
    img = add_glow(img, 540, 960, 420, (55, 45, 26))
    d = ImageDraw.Draw(img)
    # Art Deco border frame
    gold = (245, 215, 140)
    d.rectangle([(45, 45), (W - 45, H - 45)], outline=gold, width=1)
    d.rectangle([(55, 55), (W - 55, H - 55)], outline=gold, width=1)
    # Corner Deco stepped accents
    for cx, cy in [(45, 45), (W - 45, 45), (45, H - 45), (W - 45, H - 45)]:
        d.line((cx - 25, cy, cx + 25, cy), fill=gold, width=2)
        d.line((cx, cy - 25, cx, cy + 25), fill=gold, width=2)
    # Micro champagne stardust
    draw_stars(img, 100, y_max=1920, seed=qid * 23)
    return img, (245, 215, 140), (225, 190, 110)

def bg_aurora_borealis(qid):
    stops = [(0, (4, 12, 24)), (0.4, (8, 26, 42)), (0.75, (12, 40, 52)), (1, (6, 14, 22))]
    img = create_gradient(stops)
    draw_stars(img, 160, y_max=1300, seed=qid * 29)
    # Translucent wavy aurora ribbons across upper-mid sky
    aurora_layer = Image.new("RGB", (W, H), (0, 0, 0))
    ad = ImageDraw.Draw(aurora_layer)
    for wave in range(3):
        col = (40, 210, 160) if wave % 2 == 0 else (30, 180, 220)
        pts = []
        for x in range(0, W + 20, 20):
            y = 350 + wave * 90 + 70 * math.sin(x / 140.0 + wave)
            pts.append((x, y))
        for x, y in pts:
            ad.line((x, y - 90, x, y + 90), fill=col, width=18)
    aurora_layer = aurora_layer.filter(ImageFilter.GaussianBlur(40))
    img = ImageChops.add(img, aurora_layer)
    # Snowy mountain silhouettes at base
    draw_ridge(img, 1550, 75, (16, 32, 44), qid * 4 + 1)
    draw_ridge(img, 1720, 90, (8, 16, 24), qid * 4 + 2)
    return img, (160, 250, 210), (120, 230, 190)

def bg_volcanic_embers(qid):
    stops = [(0, (20, 8, 12)), (0.45, (55, 16, 20)), (0.8, (105, 34, 25)), (1, (24, 10, 10))]
    img = create_gradient(stops)
    # Jagged dark volcanic peaks at bottom
    draw_ridge(img, 1540, 85, (55, 18, 16), qid * 6 + 1)
    draw_ridge(img, 1720, 100, (20, 8, 8), qid * 6 + 2)
    # Molten glow behind peaks
    img = add_glow(img, 540, 1560, 240, (160, 48, 15))
    # Floating glowing embers drifting upward
    d = ImageDraw.Draw(img)
    random.seed(qid * 31)
    for _ in range(70):
        ex = random.randint(40, W - 40)
        ey = random.randint(700, 1880)
        er = random.choice([2, 3, 4])
        ecol = random.choice([(255, 210, 110), (255, 150, 60), (255, 80, 40)])
        d.ellipse((ex - er, ey - er, ex + er, ey + er), fill=ecol)
    return img, (255, 185, 100), (255, 140, 70)

def bg_dreamy_bokeh(qid):
    stops = [(0, (22, 10, 32)), (0.45, (48, 20, 58)), (0.8, (80, 32, 85)), (1, (18, 8, 24))]
    img = create_gradient(stops)
    # 35 Translucent soft bokeh orbs
    b_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(b_layer)
    random.seed(qid * 37)
    for _ in range(35):
        bx = random.randint(50, W - 50)
        by = random.randint(100, H - 100)
        br = random.randint(25, 95)
        bcol = random.choice([
            (255, 200, 220, 45),
            (220, 180, 255, 40),
            (255, 220, 170, 50),
            (180, 210, 255, 35)
        ])
        bd.ellipse((bx - br, by - br, bx + br, by + br), fill=bcol)
    b_layer = b_layer.filter(ImageFilter.GaussianBlur(15))
    img.paste(b_layer, (0, 0), b_layer)
    return img, (250, 200, 220), (225, 175, 200)

def bg_planetary_rings(qid):
    stops = [(0, (8, 10, 26)), (0.45, (16, 20, 45)), (0.8, (28, 22, 52)), (1, (10, 8, 20))]
    img = create_gradient(stops)
    draw_stars(img, 180, y_max=1920, seed=qid * 41)
    # Giant Planet in upper right corner
    px, py, pr = 880, 360, 200
    img = add_glow(img, px, py, 260, (50, 70, 140))
    d = ImageDraw.Draw(img)
    d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(35, 45, 80))
    # Tilted planetary rings sweeping across
    for rr in [250, 290, 330, 370]:
        d.arc((px - rr, py - int(rr * 0.35), px + rr, py + int(rr * 0.35)), start=190, end=350, fill=(160, 190, 240), width=3)
    return img, (185, 220, 255), (150, 195, 245)

def bg_sacred_starburst(qid):
    stops = [(0, (8, 14, 34)), (0.45, (16, 32, 70)), (0.8, (24, 48, 98)), (1, (10, 14, 30))]
    img = create_gradient(stops)
    img = add_glow(img, 540, 960, 420, (30, 70, 140))
    d = ImageDraw.Draw(img)
    # Sacred geometry compass/mandala rings
    cx, cy = 540, 960
    gold = (210, 185, 120)
    for cr in [200, 340, 480]:
        d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), outline=gold, width=1)
    # 8 Radial Spokes
    for deg in range(0, 360, 45):
        rad = math.radians(deg)
        x2 = cx + int(520 * math.cos(rad))
        y2 = cy + int(520 * math.sin(rad))
        d.line((cx, cy, x2, y2), fill=gold, width=1)
    return img, (245, 215, 135), (210, 185, 115)

def bg_autumn_twilight(qid):
    stops = [(0, (28, 14, 12)), (0.45, (72, 34, 24)), (0.8, (120, 60, 32)), (1, (24, 12, 10))]
    img = create_gradient(stops)
    # Warm amber horizon sun
    img = add_glow(img, 540, 1300, 280, (240, 120, 40))
    d = ImageDraw.Draw(img)
    d.ellipse((540 - 85, 1300 - 85, 540 + 85, 1300 + 85), fill=(255, 215, 140))
    # Silhouette tree branches at top corners
    d.line((0, 80, 220, 190), fill=(20, 10, 8), width=8)
    d.line((180, 170, 290, 140), fill=(20, 10, 8), width=5)
    d.line((W, 90, W - 240, 210), fill=(20, 10, 8), width=8)
    d.line((W - 200, 190, W - 310, 160), fill=(20, 10, 8), width=5)
    # Silhouette hill at bottom
    draw_ridge(img, 1620, 60, (30, 14, 10), qid * 8 + 1)
    draw_ridge(img, 1760, 75, (16, 8, 6), qid * 8 + 2)
    return img, (255, 195, 120), (235, 160, 95)

def bg_glacier_crystals(qid):
    stops = [(0, (6, 18, 32)), (0.45, (14, 40, 64)), (0.8, (24, 70, 100)), (1, (8, 18, 30))]
    img = create_gradient(stops)
    img = add_glow(img, 540, 960, 360, (20, 90, 130))
    d = ImageDraw.Draw(img)
    # Geometric crystal shards at bottom corners
    cyan = (130, 230, 255)
    # Left crystal shard cluster
    d.polygon([(0, 1550), (140, 1420), (220, 1620), (120, 1850), (0, 1850)], outline=cyan, fill=(12, 35, 55))
    d.polygon([(0, 1680), (190, 1580), (260, 1850), (0, 1850)], outline=cyan, fill=(8, 25, 42))
    # Right crystal shard cluster
    d.polygon([(W, 1540), (W - 150, 1410), (W - 230, 1630), (W, 1850)], outline=cyan, fill=(12, 35, 55))
    draw_stars(img, 110, y_max=1400, seed=qid * 43)
    return img, (145, 235, 255), (110, 210, 245)

def bg_zen_bamboo(qid):
    stops = [(0, (10, 22, 18)), (0.45, (18, 50, 40)), (0.8, (28, 76, 56)), (1, (10, 22, 16))]
    img = create_gradient(stops)
    # Serene full moon in upper center
    img = add_glow(img, 540, 380, 200, (40, 120, 90))
    d = ImageDraw.Draw(img)
    d.ellipse((540 - 80, 380 - 80, 540 + 80, 380 + 80), fill=(245, 245, 230))
    # Bamboo stalks on left and right margins
    for bx in [50, 110, W - 120, W - 60]:
        d.line((bx, 0, bx, H), fill=(10, 25, 20), width=10)
        # Bamboo segment nodes
        for by in range(120, H, 220):
            d.line((bx - 12, by, bx + 12, by), fill=(18, 45, 35), width=4)
    # Calm mist at base
    img = add_glow(img, 540, 1680, 260, (20, 65, 50))
    return img, (235, 225, 160), (195, 210, 140)

def bg_sunset_god_rays(qid):
    stops = [(0, (26, 12, 42)), (0.45, (78, 28, 64)), (0.75, (150, 65, 58)), (1, (30, 14, 25))]
    img = create_gradient(stops)
    # God rays layer radiating from horizon (540, 1280)
    ray_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ray_layer)
    for deg in range(200, 340, 15):
        rad = math.radians(deg)
        rx = 540 + int(1100 * math.cos(rad))
        ry = 1280 + int(1100 * math.sin(rad))
        rd.polygon([(540, 1280), (rx - 40, ry), (rx + 40, ry)], fill=(255, 210, 150, 30))
    ray_layer = ray_layer.filter(ImageFilter.GaussianBlur(25))
    img.paste(ray_layer, (0, 0), ray_layer)
    # Silhouette clouds at horizon
    draw_ridge(img, 1580, 55, (45, 18, 30), qid * 9 + 1)
    draw_ridge(img, 1740, 70, (22, 10, 18), qid * 9 + 2)
    return img, (255, 205, 155), (255, 170, 125)

THEME_GENERATORS = [
    bg_mountains,          # 0: Midnight Mountain Silhouette & Moon
    bg_desert_dunes,       # 1: Desert Dunes & Golden Setting Sun
    bg_cosmic_nebula,      # 2: Cosmic Nebula & Twinkling Cross Stars
    bg_synthwave_grid,     # 3: Synthwave Neon Horizon Grid
    bg_misty_forest,       # 4: Misty Pine Forest & Crescent Moon
    bg_ocean_horizon,      # 5: Sunset Ocean Water & Shimmering Reflection
    bg_luxury_gold_deco,   # 6: Luxury Obsidian Charcoal & Art Deco Gold
    bg_aurora_borealis,    # 7: Nordic Aurora Borealis Light Curtain
    bg_volcanic_embers,    # 8: Volcanic Twilight & Rising Fiery Embers
    bg_dreamy_bokeh,       # 9: Dreamy Translucent Bokeh Orbs
    bg_planetary_rings,    # 10: Celestial Planet & Sweeping Rings
    bg_sacred_starburst,   # 11: Sacred Geometry Starburst & Mandala
    bg_autumn_twilight,    # 12: Autumn Twilight & Silhouette Foliage
    bg_glacier_crystals,   # 13: Glacier Frost & Crystalline Geometric Shards
    bg_zen_bamboo,         # 14: Zen Bamboo Garden & Full Moon
    bg_sunset_god_rays,    # 15: Sunset God Rays & Horizon Twilight
]

def render_reel_cover(qid, tag, lines, out_path):
    # Select theme dynamically based on quote ID
    generator = THEME_GENERATORS[qid % len(THEME_GENERATORS)]
    img, accent, tag_accent = generator(qid)

    d = ImageDraw.Draw(img)

    # 1. Top Watermark (Safe Zone: Y = 230, well below status bar)
    fl_wm = get_latin_font(32)
    wm_text = WATERMARK
    w_wm = d.textlength(wm_text, font=fl_wm)
    # Dark contrast pill behind watermark for 100% legibility on any theme
    pill_pad_x, pill_pad_y = 24, 10
    pill_box = (
        (W - w_wm) / 2 - pill_pad_x, 230 - pill_pad_y,
        (W + w_wm) / 2 + pill_pad_x, 230 + 36 + pill_pad_y
    )
    sh_pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh_pill).rounded_rectangle(pill_box, radius=18, fill=(0, 0, 0, 140))
    img.paste(sh_pill, (0, 0), sh_pill)
    d = ImageDraw.Draw(img)
    d.text(((W - w_wm) / 2, 230), wm_text, font=fl_wm, fill=tag_accent)

    # 2. Tag Badge (Safe Zone: Y = 460)
    ft = get_font(FR_PATH, 36)
    tag_text = f"— {tag} —"
    tw = d.textlength(tag_text, font=ft)
    d.text(((W - tw) / 2, 460), tag_text, font=ft, fill=accent)
    d.line(((W - 140) / 2, 515, (W + 140) / 2, 515), fill=accent, width=2)

    # 3. Center Hindi Shayari Couplet
    # Dynamically scale font to fit within safe margins
    y0 = 660
    size = 58
    while size > 38 and max(d.textlength(ln, font=get_font(FB_PATH, size)) for ln in lines) > 860:
        size -= 2
    fm = get_font(FB_PATH, size)

    # Opening quotation mark
    fq = get_font(FB_PATH, 80)
    d.text(((W - 60) / 2, y0 - 95), "“", font=fq, fill=accent)

    y = y0
    for ln in lines:
        w = d.textlength(ln, font=fm)
        # Deep multi-pass drop shadow for guaranteed readability over any background
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh_draw = ImageDraw.Draw(sh)
        sh_draw.text(((W - w) / 2 + 4, y + 4), ln, font=fm, fill=(0, 0, 0, 220))
        sh_draw.text(((W - w) / 2 - 2, y - 2), ln, font=fm, fill=(0, 0, 0, 180))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        img.paste(sh, (0, 0), sh)
        # Foreground crisp white text
        ImageDraw.Draw(img).text(((W - w) / 2, y), ln, font=fm, fill=(255, 255, 255))
        y += int(size * 1.82)

    # Closing quotation mark
    d.text(((W - 60) / 2, y - 20), "”", font=fq, fill=accent)

    # 4. Bottom CTA (Safe Zone: Y = 1480, safely above Reels caption area)
    fl_sub = get_latin_font(26)
    sub_text = "Follow @sabir_usmani_077 for daily motivation"
    w_sub = d.textlength(sub_text, font=fl_sub)
    d.text(((W - w_sub) / 2, 1480), sub_text, font=fl_sub, fill=(225, 230, 245, 180))

    img.convert("RGB").save(out_path, quality=95, optimize=True)
    theme_idx = qid % len(THEME_GENERATORS)
    print(f"Rendered Reel cover frame [Theme #{theme_idx}]: {out_path} ({W}x{H})")
    return out_path

def build_reel_video(frame_img, out_mp4, duration=10):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Total duration: 10 seconds (optimal for silent Reel reading & loop completion)
    duration = max(6, min(80, duration))
    total_frames = duration * 30

    # Gentle cinematic Ken Burns zoom (1.0 to 1.05) over the duration
    vf = (
        f"zoompan=z='min(zoom+0.0004,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:s=1080x1920:fps=30"
    )

    # PURE SILENT AUDIO TRACK: Zero sound, zero voiceover, zero music.
    # Meta Graph API strictly requires an audio track for media_type=REELS;
    # injecting an explicit silent AAC stream satisfies Meta's ingestion pipeline
    # with 100% complete silence to viewers on Instagram.
    print(f"Building Reel video with 100% silent audio track (Duration: {duration}s)...")
    cmd = [
        ffmpeg_exe, "-y",
        "-loop", "1",
        "-i", frame_img,
        "-f", "lavfi",
        "-i", "anullsrc=r=48000:cl=stereo",
        "-vf", vf,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ac", "2",
        "-ar", "48000",
        "-t", str(duration),
        "-shortest",
        "-movflags", "+faststart",
        out_mp4
    ]

    subprocess.check_call(cmd)
    size_mb = os.path.getsize(out_mp4) / (1024 * 1024)
    print(f"Successfully compiled Silent Reel MP4: {out_mp4} ({size_mb:.2f} MB, {duration}s)")
    return out_mp4, duration

def render_reel(qid, tag, lines, out_video_path, out_cover_path, duration=10):
    os.makedirs(os.path.dirname(os.path.abspath(out_video_path)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_cover_path)), exist_ok=True)

    # 1. Render cover & base visual frame with daily unique procedural background
    render_reel_cover(qid, tag, lines, out_cover_path)

    # 2. Compile 100% silent Reel MP4 video with Ken Burns zoom
    build_reel_video(out_cover_path, out_video_path, duration=duration)

    return out_video_path, out_cover_path

if __name__ == "__main__":
    test_tag = "उम्मीद"
    test_lines = [
        "उम्मीद का दीया जब तक दिल में जलता है,",
        "हर घोर अंधेरा भी रास्ता छोड़ देता है,",
        "जो कभी नाउम्मीद नहीं होते जीवन में,",
        "उनका हर बंद दरवाज़ा भी खुल जाता है।"
    ]
    render_reel(39, test_tag, test_lines, "test_output.mp4", "test_output.jpg")
