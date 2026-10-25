import os, sys, random, math, asyncio, subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
import edge_tts
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

STYLES = [
    # 0: Midnight Royal Indigo & Warm Gold
    dict(
        stops=[(0, (12, 14, 32)), (0.45, (22, 28, 62)), (0.8, (36, 20, 52)), (1, (14, 10, 24))],
        accent=(255, 215, 130),
        tag_accent=(240, 200, 110),
        glow=(540, 960, 380, (40, 60, 130)),
        sun=(540, 960, 100, (255, 220, 150))
    ),
    # 1: Deep Crimson Velvet & Champagne
    dict(
        stops=[(0, (28, 12, 20)), (0.45, (68, 22, 38)), (0.8, (112, 45, 48)), (1, (24, 10, 18))],
        accent=(255, 210, 140),
        tag_accent=(255, 185, 110),
        glow=(540, 960, 360, (120, 30, 45)),
        sun=(540, 960, 90, (255, 210, 160))
    ),
    # 2: Emerald Aurora & Mint
    dict(
        stops=[(0, (8, 24, 28)), (0.45, (14, 55, 60)), (0.8, (22, 85, 80)), (1, (8, 22, 24))],
        accent=(180, 245, 220),
        tag_accent=(140, 230, 200),
        glow=(540, 960, 360, (20, 90, 85)),
        sun=(540, 960, 90, (200, 250, 235))
    ),
    # 3: Royal Purple Nebula & Lavender
    dict(
        stops=[(0, (20, 10, 38)), (0.45, (52, 24, 88)), (0.8, (95, 42, 120)), (1, (18, 8, 30))],
        accent=(230, 195, 255),
        tag_accent=(215, 175, 250),
        glow=(540, 960, 380, (90, 35, 140)),
        sun=(540, 960, 95, (245, 215, 255))
    ),
    # 4: Sunset Obsidian & Amber Ember
    dict(
        stops=[(0, (22, 14, 12)), (0.45, (55, 28, 20)), (0.8, (95, 48, 25)), (1, (20, 12, 10))],
        accent=(255, 205, 130),
        tag_accent=(255, 170, 90),
        glow=(540, 960, 360, (110, 50, 20)),
        sun=(540, 960, 90, (255, 220, 150))
    ),
    # 5: Deep Sapphire & Electric Cyan
    dict(
        stops=[(0, (6, 16, 36)), (0.45, (14, 38, 78)), (0.8, (24, 65, 115)), (1, (8, 14, 28))],
        accent=(160, 220, 255),
        tag_accent=(130, 200, 255),
        glow=(540, 960, 380, (25, 75, 150)),
        sun=(540, 960, 95, (210, 240, 255))
    )
]

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
    return ImageChops.add(img, g.filter(ImageFilter.GaussianBlur(r / 1.6)))

def render_reel_cover(qid, tag, lines, out_path):
    s = STYLES[qid % len(STYLES)]
    img = create_gradient(s["stops"])

    # Ambient stardust particles
    random.seed(qid * 31 + 42)
    d = ImageDraw.Draw(img)
    for _ in range(120):
        x = random.randint(0, W)
        y = random.randint(0, H)
        r = random.choice([1, 1, 2])
        alpha = random.randint(90, 210)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(alpha, alpha, alpha))

    # Center ambient glow
    if "glow" in s:
        img = add_glow(img, *s["glow"])
    d = ImageDraw.Draw(img)

    # Decorative concentric rings in background
    cx, cy = 540, 960
    for ring_r in [420, 320, 220]:
        ring_color = tuple(int(c * 0.4) for c in s["accent"])
        d.ellipse((cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r), outline=ring_color, width=1)

    # 1. Top Watermark (Safe Zone: Y = 230, well below status bar)
    fl_wm = get_latin_font(32)
    wm_text = WATERMARK
    w_wm = d.textlength(wm_text, font=fl_wm)
    # Subtle dark pill behind watermark for contrast
    pill_pad_x, pill_pad_y = 22, 10
    pill_box = (
        (W - w_wm) / 2 - pill_pad_x, 230 - pill_pad_y,
        (W + w_wm) / 2 + pill_pad_x, 230 + 36 + pill_pad_y
    )
    sh_pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh_pill).rounded_rectangle(pill_box, radius=18, fill=(0, 0, 0, 110))
    img.paste(sh_pill, (0, 0), sh_pill)
    d = ImageDraw.Draw(img)
    d.text(((W - w_wm) / 2, 230), wm_text, font=fl_wm, fill=s["tag_accent"])

    # 2. Tag Badge (Safe Zone: Y = 460)
    ft = get_font(FR_PATH, 36)
    tag_text = f"— {tag} —"
    tw = d.textlength(tag_text, font=ft)
    d.text(((W - tw) / 2, 460), tag_text, font=ft, fill=s["accent"])
    d.line(((W - 140) / 2, 515, (W + 140) / 2, 515), fill=s["accent"], width=2)

    # 3. Center Hindi Shayari Couplet
    # Dynamically scale font to fit within safe margins
    y0 = 660
    size = 58
    while size > 38 and max(d.textlength(ln, font=get_font(FB_PATH, size)) for ln in lines) > 860:
        size -= 2
    fm = get_font(FB_PATH, size)

    # Opening quotation mark
    fq = get_font(FB_PATH, 80)
    d.text(((W - 60) / 2, y0 - 95), "“", font=fq, fill=s["accent"])

    y = y0
    for ln in lines:
        w = d.textlength(ln, font=fm)
        # Drop shadow for readability
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text(((W - w) / 2 + 3, y + 4), ln, font=fm, fill=(0, 0, 0, 175))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        img.paste(sh, (0, 0), sh)
        # Foreground text
        ImageDraw.Draw(img).text(((W - w) / 2, y), ln, font=fm, fill=(255, 255, 255))
        y += int(size * 1.82)

    # Closing quotation mark
    d.text(((W - 60) / 2, y - 20), "”", font=fq, fill=s["accent"])

    # 4. Bottom CTA (Safe Zone: Y = 1480, safely above Reels caption area)
    fl_sub = get_latin_font(26)
    sub_text = "Follow @sabir_usmani_077 for daily motivation"
    w_sub = d.textlength(sub_text, font=fl_sub)
    d.text(((W - w_sub) / 2, 1480), sub_text, font=fl_sub, fill=(210, 220, 240, 170))

    img.convert("RGB").save(out_path, quality=95, optimize=True)
    print(f"Rendered Reel cover frame: {out_path} ({W}x{H})")
    return out_path

async def generate_speech_async(text, out_mp3):
    comm = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="-4%")
    await comm.save(out_mp3)

def generate_audio(tag, lines, out_mp3):
    text = f"{tag}। " + " ".join(lines)
    try:
        print("Synthesizing Hindi speech via edge-tts (hi-IN-MadhurNeural)...")
        asyncio.run(generate_speech_async(text, out_mp3))
        if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 1000:
            print(f"Speech audio generated: {out_mp3} ({os.path.getsize(out_mp3)} bytes)")
            return out_mp3
    except Exception as e:
        print(f"::warning::edge-tts synthesis failed ({e}). Falling back to synthesized ambient tone.")

    # Fallback: Synthesize a soothing warm ambient chime with ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "sine=f=220:r=44100",
        "-af", "volume=0.15,lowpass=f=380,afade=t=in:ss=0:d=2,afade=t=out:st=12:d=2",
        "-t", "14",
        "-c:a", "aac",
        out_mp3
    ]
    subprocess.check_call(cmd)
    print(f"Generated fallback ambient audio: {out_mp3}")
    return out_mp3

def build_reel_video(frame_img, audio_path, out_mp4):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Determine audio duration
    p = subprocess.run([ffmpeg_exe, "-i", audio_path, "-f", "null", "-"], stderr=subprocess.PIPE, text=True)
    dur = 14.0
    for line in p.stderr.splitlines():
        if "Duration" in line:
            try:
                parts = line.split("Duration:")[1].split(",")[0].strip().split(":")
                dur = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            except Exception:
                pass
            break

    total_dur = math.ceil(dur + 1.5)
    # Reels must be at least 5 seconds, max 90 seconds
    total_dur = max(6, min(80, total_dur))
    print(f"Audio duration: {dur:.1f}s | Target Reel duration: {total_dur}s")

    # Gentle cinematic Ken Burns zoom (1.0 to 1.05)
    vf = (
        f"zoompan=z='min(zoom+0.0004,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_dur * 30}:s=1080x1920:fps=30"
    )

    cmd = [
        ffmpeg_exe, "-y",
        "-loop", "1",
        "-i", frame_img,
        "-i", audio_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", str(total_dur),
        "-movflags", "+faststart",
        out_mp4
    ]

    subprocess.check_call(cmd)
    size_mb = os.path.getsize(out_mp4) / (1024 * 1024)
    print(f"Successfully compiled Reel MP4: {out_mp4} ({size_mb:.2f} MB)")
    return out_mp4, total_dur

def render_reel(qid, tag, lines, out_video_path, out_cover_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_video_path)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_cover_path)), exist_ok=True)

    temp_audio = os.path.join(ROOT, "temp_reel_audio.mp3")

    # 1. Render cover & base visual frame
    render_reel_cover(qid, tag, lines, out_cover_path)

    # 2. Synthesize audio
    generate_audio(tag, lines, temp_audio)

    # 3. Compile MP4 video
    build_reel_video(out_cover_path, temp_audio, out_video_path)

    # 4. Cleanup temporary audio file
    if os.path.exists(temp_audio):
        try:
            os.remove(temp_audio)
        except Exception:
            pass

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
