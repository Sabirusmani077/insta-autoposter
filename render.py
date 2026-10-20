from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
import random, math, os
ROOT = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350
FONTS_DIR = os.path.join(ROOT, "fonts")
FB_CANDIDATES = [
    os.path.join(FONTS_DIR, "NotoSansDevanagari-Bold.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "C:/Windows/Fonts/NirmalaB.ttf",
    "C:/Windows/Fonts/arialbd.ttf"
]
FR_CANDIDATES = [
    os.path.join(FONTS_DIR, "NotoSansDevanagari-Regular.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "C:/Windows/Fonts/Nirmala.ttf",
    "C:/Windows/Fonts/arial.ttf"
]

def resolve_font_path(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

FB = resolve_font_path(FB_CANDIDATES)
FR = resolve_font_path(FR_CANDIDATES)
WATERMARK = "@sabir_usmani_077"

def font(p, s):
    try:
        return ImageFont.truetype(p, s, layout_engine=ImageFont.Layout.RAQM)
    except Exception:
        return ImageFont.truetype(p, s)

def grad(stops):
    img = Image.new("RGB", (W, H)); d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        for i in range(len(stops) - 1):
            a, ca = stops[i]; b, cb = stops[i + 1]
            if a <= t <= b:
                k = (t - a) / (b - a)
                c = tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(3)); break
        d.line((0, y, W, y), fill=c)
    return img

def ridge(img, base, amp, color, seed):
    random.seed(seed); d = ImageDraw.Draw(img)
    ph = [random.uniform(0, 6) for _ in range(4)]
    pts = [(x, base - sum(amp / (i + 1) * math.sin(x / (140 / (i + 1)) + ph[i]) for i in range(4))) for x in range(0, W + 8, 8)]
    d.polygon(pts + [(W, H), (0, H)], fill=color)

def glow(img, cx, cy, r, color):
    g = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(g).ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    return ImageChops.add(img, g.filter(ImageFilter.GaussianBlur(r / 1.6)))

STYLES = [
 dict(g=[(0,(28,24,64)),(.45,(150,60,90)),(.75,(245,150,80)),(1,(255,205,120))], glow=(540,980,340,(255,170,70)), sun=(540,980,95,(255,230,170)), ridges=[(1010,60,(70,40,80)),(1100,70,(40,26,58)),(1200,60,(18,14,32))], accent=(255,205,140), ty=300),
 dict(g=[(0,(6,10,30)),(.6,(18,34,78)),(1,(40,60,110))], stars=True, glow=(840,230,150,(120,140,200)), sun=(840,230,55,(240,240,225)), ridges=[(1130,50,(14,22,48)),(1220,50,(6,10,26))], accent=(160,185,240), ty=380),
 dict(g=[(0,(8,52,60)),(.7,(14,92,98)),(1,(10,40,48))], glow=(540,1030,260,(40,160,150)), rings=(540,1030,[250,190,130,70]), sun=(540,1030,14,(240,215,140)), ridges=[], accent=(240,215,140), ty=320),
 dict(g=[(0,(60,10,30)),(.6,(120,30,40)),(1,(200,120,50))], glow=(540,1000,320,(255,150,60)), sun=(540,1000,80,(255,220,150)), ridges=[(1080,60,(70,18,30)),(1190,60,(36,8,18))], accent=(255,215,150), ty=320),
 dict(g=[(0,(10,30,40)),(.6,(30,90,80)),(1,(200,170,90))], glow=(300,1020,300,(255,200,100)), sun=(300,1020,70,(255,235,170)), ridges=[(1070,60,(20,70,60)),(1170,60,(10,40,36)),(1260,40,(6,22,20))], accent=(255,225,150), ty=340),
 dict(g=[(0,(20,10,50)),(.6,(70,40,120)),(1,(150,80,140))], stars=True, glow=(540,300,260,(150,110,220)), ridges=[(1150,60,(40,20,80)),(1230,50,(18,8,40))], accent=(215,190,255), ty=380),
]

def render(qid, tag, lines, out_path):
    s = STYLES[qid % len(STYLES)]
    img = grad(s["g"])
    if s.get("stars"):
        random.seed(qid); d = ImageDraw.Draw(img)
        for _ in range(180):
            x, y = random.randint(0, W), random.randint(0, 900); r = random.choice([1, 1, 2]); a = random.randint(150, 255)
            if s["ty"] - 120 < y < s["ty"] + 520: continue
            d.ellipse((x - r, y - r, x + r, y + r), fill=(a, a, a))
    if "glow" in s: img = glow(img, *s["glow"])
    d = ImageDraw.Draw(img)
    if "rings" in s:
        cx, cy, rs = s["rings"]
        for rr in rs: d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(120, 210, 195), width=2)
    if "sun" in s:
        cx, cy, r, c = s["sun"]; d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    for i, (b, a, c) in enumerate(s["ridges"]): ridge(img, b, a, c, qid * 10 + i)
    d = ImageDraw.Draw(img); acc = s["accent"]; y0 = s["ty"]
    ft = font(FR, 38); tw = d.textlength(tag, font=ft)
    d.text(((W - tw) / 2, y0 - 110), tag, font=ft, fill=acc)
    d.line(((W - 120) / 2, y0 - 45, (W + 120) / 2, y0 - 45), fill=acc, width=3)
    size = 70
    while size > 40 and max(d.textlength(l, font=font(FB, size)) for l in lines) > 920: size -= 2
    fm = font(FB, size); y = y0
    for ln in lines:
        w = d.textlength(ln, font=fm)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text(((W - w) / 2 + 3, y + 4), ln, font=fm, fill=(0, 0, 0, 140))
        sh = sh.filter(ImageFilter.GaussianBlur(5)); img.paste(sh, (0, 0), sh)
        ImageDraw.Draw(img).text(((W - w) / 2, y), ln, font=fm, fill=(255, 255, 255)); y += int(size * 1.7)
    fw = font(FR, 30); w = d.textlength(WATERMARK, font=fw)
    wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(wm).text(((W - w) / 2, H - 80), WATERMARK, font=fw, fill=(255, 255, 255, 120))
    img.paste(wm, (0, 0), wm)
    img.convert("RGB").save(out_path, quality=92, optimize=True)
