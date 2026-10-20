import json, os, sys, time, datetime, urllib.request, urllib.parse

# Ensure standard output can print Devanagari Unicode cleanly on any OS
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import Image
from render import render
from quality import select_best_candidate, validate_quote

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(ROOT, f)

CAPTIONS = [
    "आज का दिन आपका है। इसे पूरी ताक़त और लगन से जिएँ। 💪",
    "जिसे आज ये हौसला सुनने की ज़रूरत हो, उसे ज़रूर भेजें। ❤️",
    "एक शब्द या एक लाइन में बताइए, आज आपका लक्ष्य क्या है? 👇",
    "इसे सेव कर लें, जब भी हिम्मत टूटने लगे तब इसे पढ़ना। 🔖",
    "छोटा क़दम भी क़दम होता है, मंज़िल तक पहुँचने के लिए चलते रहिए। 🌱",
    "आप कितना भी थकें हों, हार मानकर रुकना विकल्प नहीं है। 🔥",
    "आज ख़ुद से एक सच्चा वादा कीजिए और उसे हर हाल में निभाइए। ✅",
    "कौन सी पंक्ति आपके दिल को सबसे ज़्यादा छू गई? कमेंट में लिखें। 💬",
    "अपने उस सच्चे दोस्त को टैग करें जो कभी मुश्किलों से हार नहीं मानता। 🤝",
    "सब्र और अनुशासन रखिए, सच्ची मेहनत हमेशा रंग लाती है। 🌅",
]

HASH = [
    "#हिंदीशायरी", "#हिंदीमोटिवेशन", "#motivation", "#hindiquotes", "#success",
    "#lifelessons", "#selfgrowth", "#positivevibes", "#मेहनत", "#सफलता",
    "#discipline", "#dailymotivation", "#hindishayari", "#जिंदगी", "#hustle",
    "#mindset", "#consistency", "#inspiration", "#quotesdaily", "#growth"
]

def load(f, d):
    try:
        with open(P(f), "r", encoding="utf-8") as fp:
            return json.load(fp)
    except FileNotFoundError:
        return d
    except Exception as e:
        print(f"::warning::Error loading {f}: {e}")
        return d

def save(f, o):
    with open(P(f), "w", encoding="utf-8") as fp:
        json.dump(o, fp, ensure_ascii=False, indent=2)

def today_ist():
    # IST is UTC + 5:30
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date().isoformat()

def prepare():
    quotes = load("quotes.json", [])
    hist = load("history.json", [])
    today = today_ist()

    # 1. Check if already successfully published today
    if any(h.get("date") == today and h.get("status") == "published" for h in hist):
        print(f"Already published today ({today}). Skipping duplicate post.")
        save("today.json", {"skip": True, "date": today, "reason": "Already published today"})
        return

    # 2. Select highest quality candidate automatically
    best_quote, score, remaining_count = select_best_candidate(quotes, hist)
    print(f"Candidate quotes remaining in queue: {remaining_count}")
    
    if remaining_count < 7:
        print("::warning::Fewer than 7 quotes left in queue. Please append new quotes to quotes.json soon.")
    
    if not best_quote:
        print("::error::Quote bank is empty or no valid candidates found.")
        sys.exit(1)

    print(f"Selected Candidate ID: {best_quote['id']} | Tag: {best_quote['tag']} | Quality Score: {score}/100")

    # 3. Render Instagram image
    os.makedirs(P("images"), exist_ok=True)
    img_rel_path = f"images/{today}.jpg"
    img_abs_path = P(img_rel_path)
    render(best_quote["id"], best_quote["tag"], best_quote["lines"], img_abs_path)

    # 4. Verify rendered image
    if not os.path.exists(img_abs_path):
        print(f"::error::Rendered image file was not created: {img_abs_path}")
        sys.exit(1)

    with Image.open(img_abs_path) as im:
        width, height = im.size
        if (width, height) != (1080, 1350):
            print(f"::error::Invalid image dimensions: {width}x{height}, expected 1080x1350")
            sys.exit(1)
        file_size_kb = os.path.getsize(img_abs_path) / 1024
        print(f"Image verified: {width}x{height} (4:5 portrait), Size: {file_size_kb:.1f} KB")

    # 5. Generate matching caption & relevant hashtags
    n = len([h for h in hist if h.get("status") == "published"])
    hook = CAPTIONS[n % len(CAPTIONS)]
    tag_clean = f"#{best_quote['tag'].replace(' ', '')}"
    
    selected_tags = ["#हिंदीशायरी", "#hindishayari", tag_clean]
    for i in range(5):
        selected_tags.append(HASH[(n * 3 + i) % len(HASH)])
    # Deduplicate while preserving order
    selected_tags = list(dict.fromkeys(selected_tags))

    caption = (
        f"{hook}\n\n"
        f"✍️ Original shayari | @sabir_usmani_077\n\n"
        + " ".join(selected_tags)
    )

    assert len(caption) < 2200, "Caption exceeds Instagram length limit"
    assert len(selected_tags) <= 30, "Hashtag count exceeds Instagram limit of 30"

    save("today.json", {
        "date": today,
        "id": best_quote["id"],
        "tag": best_quote["tag"],
        "score": score,
        "image": img_rel_path,
        "caption": caption
    })
    print(f"Prepared successfully: {img_rel_path}")
    print("--- PREPARED CAPTION ---")
    print(caption)
    print("------------------------")

def call(method, url, params):
    data = urllib.parse.urlencode(params)
    full_url = url + ("?" + data if method == "GET" else "")
    req = urllib.request.Request(
        full_url,
        data=None if method == "GET" else data.encode("utf-8"),
        method=method,
        headers={"User-Agent": "InstaAutoPoster/2.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw_err = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(raw_err)
            err_obj = err_json.get("error", {})
            msg = err_obj.get("message", raw_err)
            err_type = err_obj.get("type", "Error")
            code = err_obj.get("code", "N/A")
            subcode = err_obj.get("error_subcode", "")
            print(f"::error::Meta API Error [{code}/{subcode}] ({err_type}): {msg}")
            if code == 190:
                print("::error::The IG_ACCESS_TOKEN is invalid or expired. Please refresh the token.")
            elif code == 10:
                print("::error::Permission missing: Ensure 'instagram_business_content_publish' is granted to the token.")
            elif code == 24:
                print("::error::User ID mismatch: Verify that IG_USER_ID matches your Instagram Creator/Business account.")
        except Exception:
            print("::error::API HTTP Error:", raw_err)
        sys.exit(1)
    except Exception as e:
        print(f"::error::Network error while calling {url}: {e}")
        sys.exit(1)

def publish():
    t = load("today.json", {})
    if t.get("skip"):
        print(f"Skipping publish: {t.get('reason', 'skip set to true')}")
        return

    hist = load("history.json", [])
    if any(h.get("date") == t.get("date") and h.get("status") == "published" for h in hist):
        print("Duplicate blocked: Post for today is already recorded as published.")
        return

    tok = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    uid = os.environ.get("IG_USER_ID", "").strip()

    if not tok:
        print("::error::IG_ACCESS_TOKEN secret is not set in repository secrets.")
        sys.exit(1)
    if not uid:
        print("::error::IG_USER_ID secret is not set in repository secrets.")
        sys.exit(1)

    repo = os.environ.get("GITHUB_REPOSITORY", "Sabirusmani077/insta-autoposter")
    commit_sha = os.environ.get("GITHUB_SHA")

    if commit_sha:
        url = f"https://raw.githubusercontent.com/{repo}/{commit_sha}/{t['image']}"
    else:
        url = f"https://raw.githubusercontent.com/{repo}/main/{t['image']}"

    print(f"Checking image reachability at: {url}")
    reachable = False
    for attempt in range(8):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    reachable = True
                    print(f"Image is reachable (HTTP 200). Ready for Meta container creation.")
                    break
        except Exception:
            print(f"Waiting for raw image CDN propagation (attempt {attempt+1}/8)...")
            time.sleep(10)

    if not reachable:
        print("::warning::CDN reachability check timed out, attempting container creation anyway...")

    base = "https://graph.instagram.com/v21.0"
    print("Step 1: Creating Instagram media container...")
    c_res = call("POST", f"{base}/{uid}/media", {
        "image_url": url,
        "caption": t["caption"],
        "access_token": tok
    })
    container_id = c_res.get("id")
    if not container_id:
        print("::error::Container creation did not return an ID:", c_res)
        sys.exit(1)
    print(f"Container created successfully. ID: {container_id}")

    print("Step 2: Checking container status...")
    finished = False
    for attempt in range(15):
        st_res = call("GET", f"{base}/{container_id}", {
            "fields": "status_code,status",
            "access_token": tok
        })
        st = st_res.get("status_code")
        print(f"Container status check ({attempt+1}/15): {st}")
        if st == "FINISHED":
            finished = True
            break
        if st == "ERROR":
            err_msg = st_res.get("status", "Unknown container processing error")
            print(f"::error::Instagram container processing failed: {err_msg}")
            sys.exit(1)
        time.sleep(5)

    if not finished:
        print("::error::Container processing timed out without reaching FINISHED status.")
        sys.exit(1)

    print("Step 3: Publishing media container to Instagram...")
    pub_res = call("POST", f"{base}/{uid}/media_publish", {
        "creation_id": container_id,
        "access_token": tok
    })
    post_id = pub_res.get("id")
    if not post_id:
        print("::error::Media publishing did not return a post ID:", pub_res)
        sys.exit(1)

    hist.append({
        "date": t["date"],
        "id": t["id"],
        "tag": t.get("tag", ""),
        "status": "published",
        "post_id": post_id,
        "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "caption": t["caption"]
    })
    save("history.json", hist)
    print(f"SUCCESS: Post published to Instagram! Media ID: {post_id}")

def dryrun():
    print("=== STARTING FULL DRY RUN ===")
    prepare()
    t = load("today.json", {})
    if t.get("skip"):
        print(f"Dry run complete: Day already marked as published ({t.get('reason')}).")
        return
    print("Dry run: Validating container requirements...")
    print(f"Date: {t.get('date')}")
    print(f"Quote ID: {t.get('id')}")
    print(f"Tag: {t.get('tag')}")
    print(f"Image: {t.get('image')}")
    print(f"Caption Length: {len(t.get('caption', ''))} characters")
    print("Dry run completed successfully. (Publishing explicitly disabled in dry run mode).")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "dryrun"
    actions = {
        "prepare": prepare,
        "publish": publish,
        "dryrun": dryrun
    }
    if action in actions:
        actions[action]()
    else:
        print(f"Unknown action: {action}. Available: {list(actions.keys())}")
        sys.exit(1)
