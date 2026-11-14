import json, os, sys, time, datetime, urllib.request, urllib.parse, subprocess

# Ensure standard output can print Devanagari Unicode cleanly on any OS
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import Image
from render_reel import render_reel, get_daily_bgm
from render import render
from quality import select_best_candidate, validate_quote

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(ROOT, f)

CAPTIONS = [
    "Ghalib aur Jaun ke alfaaz seedhe rooh mein utarte hain... 🖤",
    "Kaun si line aapke dil ko sabse zyada chhoo gayi? Comment mein likhein. ✒️",
    "Shayari pasand aaye to apne azeez doston ke saath zaroor share karein. 📖",
    "Ise save kar lein, jab bhi sukoon aur tanhai mein shayari padhne ka dil kare. 🔖",
    "Ek lafz ya ek line mein batayein, ye sher aapko kaisa laga? ✍️",
    "Dilon ke haal ko bayaan karti ye lines... ❤️",
    "Jaun Elia aur Mirza Ghalib ki shayari ka jaadu hamesha zinda rehta hai. ✨",
    "Jis dost ko shayari ka shauq ho, use ye reel zaroor bhejein. 🤝",
    "Lafzon mein dard aur ehsaas ka aisa sangam sirf yahin mil sakta hai. 🥀",
    "Shayari wahi jo dil se nikle aur rooh tak asar kar jaaye. 📜",
]

REEL_HASH = [
    "#reels", "#reelsindia", "#instareels", "#reelsinstagram", "#viralreels",
    "#शायरी", "#हिंदीशायरी", "#उर्दूशायरी", "#hindishayari", "#urdushayari",
    "#jaunelia", "#mirzaghalib", "#जौनएलिया", "#मिर्ज़ाग़ालिब", "#ghalib",
    "#jauneliapoetry", "#ghalibpoetry", "#rekhta", "#sadshayari", "#shayari",
    "#poetry", "#mohabbat", "#ishq", "#twolineshayari"
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

    # 3. Render Instagram Reel (1080x1920 MP4 Video + High-Res Cover Image)
    os.makedirs(P("videos"), exist_ok=True)
    os.makedirs(P("images"), exist_ok=True)
    vid_rel_path = f"videos/{today}.mp4"
    img_rel_path = f"images/{today}.jpg"
    vid_abs_path = P(vid_rel_path)
    img_abs_path = P(img_rel_path)

    n = len([h for h in hist if h.get("status") == "published"])
    selected_bgm = get_daily_bgm(n)
    bgm_name = os.path.basename(selected_bgm) if selected_bgm else "fallback"
    print(f"Generating 1080x1920 Instagram Reel video (BGM: {bgm_name}, Track #{n % 3 + 1} of 3) and cover...")
    render_reel(best_quote["id"], best_quote["tag"], best_quote["lines"], vid_abs_path, img_abs_path, audio_file=selected_bgm)

    # 4. Verify rendered video & cover
    if not os.path.exists(vid_abs_path):
        print(f"::error::Rendered video file was not created: {vid_abs_path}")
        sys.exit(1)
    if not os.path.exists(img_abs_path):
        print(f"::error::Rendered cover image was not created: {img_abs_path}")
        sys.exit(1)

    vid_size_kb = os.path.getsize(vid_abs_path) / 1024
    if vid_size_kb < 100:
        print(f"::error::Video file is suspiciously small ({vid_size_kb:.1f} KB)")
        sys.exit(1)

    with Image.open(img_abs_path) as im:
        width, height = im.size
        if (width, height) != (1080, 1920):
            print(f"::error::Invalid cover image dimensions: {width}x{height}, expected 1080x1920")
            sys.exit(1)
        cover_size_kb = os.path.getsize(img_abs_path) / 1024
        print(f"Reel assets verified: Video {vid_size_kb:.1f} KB | Cover {width}x{height} (9:16 portrait), {cover_size_kb:.1f} KB")

    # 5. Generate matching caption & relevant Reel hashtags
    hook = CAPTIONS[n % len(CAPTIONS)]
    tag_clean = f"#{best_quote['tag'].replace(' ', '')}"

    selected_tags = ["#reels", "#reelsindia", "#शायरी", "#hindishayari", tag_clean]
    for i in range(6):
        selected_tags.append(REEL_HASH[(n * 3 + i) % len(REEL_HASH)])
    # Deduplicate while preserving order
    selected_tags = list(dict.fromkeys(selected_tags))

    caption = (
        f"{hook}\n\n"
        f"✍️ {best_quote['tag']} | @sabir_usmani_077\n\n"
        + " ".join(selected_tags)
    )

    assert len(caption) < 2200, "Caption exceeds Instagram length limit"
    assert len(selected_tags) <= 30, "Hashtag count exceeds Instagram limit of 30"

    save("today.json", {
        "date": today,
        "id": best_quote["id"],
        "tag": best_quote["tag"],
        "score": score,
        "media_type": "REELS",
        "video": vid_rel_path,
        "image": img_rel_path,
        "caption": caption
    })
    print(f"Reel prepared successfully: {vid_rel_path}")
    print("--- PREPARED REEL CAPTION ---")
    print(caption)
    print("-----------------------------")

def call(method, url, params, max_retries=4, initial_delay=6, retry_codes=(1, 2, 4, 17, 341, 9007), fatal_exit=True):
    data = urllib.parse.urlencode(params)
    full_url = url + ("?" + data if method == "GET" else "")

    for attempt in range(max_retries):
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
            except Exception:
                err_obj = {}
                msg = raw_err
                err_type = "HTTPError"
                code = e.code
                subcode = ""

            # Check if this error is transient and retryable (Meta Code 2: Please retry later, Code 1: Unknown, or HTTP 5xx)
            is_transient = (code in retry_codes) or (isinstance(code, int) and code in retry_codes) or (e.code in (500, 502, 503, 504))
            if is_transient and attempt < max_retries - 1:
                wait_time = initial_delay * (attempt + 1)
                print(f"::warning::Meta API Transient Error [{code}/{subcode}] ({err_type}): {msg}")
                print(f"Retrying request in {wait_time}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue

            if not fatal_exit:
                print(f"::warning::Meta API Call Failed [{code}/{subcode}] ({err_type}): {msg}")
                return {"error": {"code": code, "subcode": subcode, "message": msg, "type": err_type}}

            print(f"::error::Meta API Error [{code}/{subcode}] ({err_type}): {msg}")
            if code == 190:
                print("::error::The IG_ACCESS_TOKEN is invalid or expired. Please refresh the token.")
            elif code == 10:
                print("::error::Permission missing: Ensure 'instagram_business_content_publish' is granted to the token.")
            elif code == 24:
                print("::error::User ID mismatch: Verify that IG_USER_ID matches your Instagram Creator/Business account.")
            sys.exit(1)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = initial_delay * (attempt + 1)
                print(f"::warning::Network error while calling {url}: {e}. Retrying in {wait_time}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            if not fatal_exit:
                print(f"::warning::Network error while calling {url}: {e}")
                return {"error": {"message": str(e)}}
            print(f"::error::Network error while calling {url}: {e}")
            sys.exit(1)

def format_threads_caption(caption, max_len=500):
    if not caption:
        return ""
    if len(caption) <= max_len:
        return caption
    return caption[:max_len - 3].rstrip() + "..."

def publish_to_threads(media_url, caption, tok=None, uid=None, is_video=True):
    """
    Publish video or photo to Meta Threads account using Threads API v1.0 (graph.threads.net).
    This function is non-blocking: if THREADS_ACCESS_TOKEN is not configured or an error occurs,
    it logs an informational message or warning and returns None without failing the Instagram run.
    """
    tok = (tok or os.environ.get("THREADS_ACCESS_TOKEN", "")).strip()
    uid = (uid or os.environ.get("THREADS_USER_ID", "")).strip()

    if not tok:
        print("::notice::THREADS_ACCESS_TOKEN is not configured in repository secrets. Skipping Threads cross-post.")
        return None

    print("\n=== Cross-Posting to Meta Threads ===")
    threads_base = "https://graph.threads.net/v1.0"

    # Step 0: Identify account from token if UID not explicitly set
    try:
        me_info = call("GET", f"{threads_base}/me", {"fields": "id,username", "access_token": tok}, fatal_exit=False)
        if isinstance(me_info, dict) and "username" in me_info:
            print(f"Connected Threads account: @{me_info.get('username')} (ID: {me_info.get('id')})")
            if not uid or uid.lower() == "me":
                uid = me_info.get("id")
    except Exception as e:
        print(f"::warning::Could not query Threads /me endpoint: {e}")

    target_uid = uid if uid else "me"
    th_caption = format_threads_caption(caption)

    # Step 1: Create media container
    print(f"Step 1 (Threads): Creating media container for target user '{target_uid}'...")
    container_params = {
        "text": th_caption,
        "access_token": tok
    }
    if is_video:
        container_params["media_type"] = "VIDEO"
        container_params["video_url"] = media_url
    else:
        container_params["media_type"] = "IMAGE"
        container_params["image_url"] = media_url

    c_res = call("POST", f"{threads_base}/{target_uid}/threads", container_params, fatal_exit=False)
    container_id = c_res.get("id") if isinstance(c_res, dict) else None
    if not container_id:
        print(f"::warning::Threads media container creation failed: {c_res}")
        return None
    print(f"Threads media container created successfully. ID: {container_id}")

    # Step 2: Poll status until FINISHED
    print("Step 2 (Threads): Polling container transcoding / processing status...")
    finished = False
    for attempt in range(35):
        st_res = call("GET", f"{threads_base}/{container_id}", {
            "fields": "status,error_message",
            "access_token": tok
        }, fatal_exit=False)
        st = st_res.get("status") if isinstance(st_res, dict) else "UNKNOWN"
        print(f"Threads status check ({attempt+1}/35): {st}")
        if st == "FINISHED":
            finished = True
            print("Threads container status is FINISHED. Allowing 8s propagation buffer before publishing...")
            time.sleep(8)
            break
        elif st == "ERROR":
            err_msg = st_res.get("error_message", "Unknown Threads media processing error")
            print(f"::warning::Threads media processing failed: {err_msg}")
            return None
        time.sleep(5)

    if not finished:
        print("::warning::Threads container processing timed out without reaching FINISHED status.")
        return None

    # Step 3: Publish container
    print("Step 3 (Threads): Publishing container to Threads...")
    pub_res = call(
        "POST",
        f"{threads_base}/{target_uid}/threads_publish",
        {
            "creation_id": container_id,
            "access_token": tok
        },
        max_retries=5,
        initial_delay=8,
        fatal_exit=False
    )
    threads_post_id = pub_res.get("id") if isinstance(pub_res, dict) else None
    if threads_post_id:
        print(f"SUCCESS: Cross-posted to Meta Threads! Threads Post ID: {threads_post_id}")
        return threads_post_id
    else:
        print(f"::warning::Threads publish did not return an ID: {pub_res}")
        return None

def resolve_public_url(rel_path, repo):
    commit_sha = None
    try:
        out = subprocess.check_output(
            ["git", "log", "-n", "1", "--format=%H", "--", rel_path],
            text=True,
            cwd=ROOT
        ).strip()
        if out and len(out) == 40:
            commit_sha = out
            print(f"Found commit SHA for {rel_path}: {commit_sha}")
    except Exception as ex:
        print(f"Could not read git log for {rel_path}: {ex}")

    candidate_urls = []
    if commit_sha:
        candidate_urls.append(f"https://raw.githubusercontent.com/{repo}/{commit_sha}/{rel_path}")
    candidate_urls.append(f"https://raw.githubusercontent.com/{repo}/main/{rel_path}")

    print(f"Resolving reachable public URL for {rel_path}...")
    valid_url = None
    for attempt in range(12):
        for candidate in candidate_urls:
            try:
                req = urllib.request.Request(candidate, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        valid_url = candidate
                        print(f"Verified reachable (HTTP 200): {valid_url}")
                        break
            except Exception:
                continue
        if valid_url:
            break
        print(f"Waiting for CDN propagation for {rel_path} (attempt {attempt+1}/12)...")
        time.sleep(5)

    if not valid_url:
        valid_url = candidate_urls[0]
        print(f"::warning::CDN verification timed out, using fallback URL: {valid_url}")

    return valid_url

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
    base = "https://graph.instagram.com/v21.0"
    is_reel = t.get("media_type") == "REELS" or bool(t.get("video"))

    if is_reel:
        print("=== Publishing Mode: INSTAGRAM REEL ===")
        video_url = resolve_public_url(t["video"], repo)
        cover_url = resolve_public_url(t["image"], repo)

        post_id = None
        # Allow up to 2 complete container attempts in case Meta's container gets desynced
        for container_cycle in range(2):
            if container_cycle > 0:
                print("\n::warning::Re-attempting Reel creation with a fresh media container...")
                time.sleep(10)

            print(f"Step 1: Creating Instagram Reel media container (Cycle {container_cycle+1}/2)...")
            c_res = call("POST", f"{base}/{uid}/media", {
                "media_type": "REELS",
                "video_url": video_url,
                "cover_url": cover_url,
                "caption": t["caption"],
                "share_to_feed": "true",
                "access_token": tok
            })
            container_id = c_res.get("id")
            if not container_id:
                print("::error::Reel container creation did not return an ID:", c_res)
                sys.exit(1)
            print(f"Reel container created successfully. ID: {container_id}")

            print("Step 2: Checking Reel container transcoding status...")
            finished = False
            # Video transcoding on Meta servers takes 15 to 60 seconds
            for attempt in range(35):
                st_res = call("GET", f"{base}/{container_id}", {
                    "fields": "status_code,status",
                    "access_token": tok
                })
                st = st_res.get("status_code")
                print(f"Reel status check ({attempt+1}/35): {st}")
                if st == "FINISHED":
                    finished = True
                    print("Container status is FINISHED. Allowing 10s propagation buffer before media_publish...")
                    time.sleep(10)
                    break
                if st == "ERROR":
                    err_msg = st_res.get("status", "Unknown container processing error")
                    print(f"::error::Instagram Reel processing failed: {err_msg}")
                    break
                time.sleep(5)

            if not finished:
                print(f"::warning::Reel processing timed out or failed without reaching FINISHED status on cycle {container_cycle+1}.")
                continue

            print("Step 3: Publishing Reel to Instagram (with retry mechanism)...")
            pub_res = call(
                "POST",
                f"{base}/{uid}/media_publish",
                {
                    "creation_id": container_id,
                    "access_token": tok
                },
                max_retries=5,
                initial_delay=10,
                retry_codes=(1, 2, 4, 17, 341, 9007)
            )
            post_id = pub_res.get("id")
            if post_id:
                break
            else:
                print(f"::warning::Publish call did not return an ID on cycle {container_cycle+1}: {pub_res}")

        if not post_id:
            print("::error::Failed to publish Reel after multiple container cycles.")
            sys.exit(1)

        hist_entry = {
            "date": t["date"],
            "id": t["id"],
            "tag": t.get("tag", ""),
            "status": "published",
            "type": "reel",
            "post_id": post_id,
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "caption": t["caption"]
        }
        hist.append(hist_entry)
        save("history.json", hist)
        print(f"SUCCESS: Reel published to Instagram! Reel Media ID: {post_id}")

        # Cross-post to Meta Threads
        threads_post_id = publish_to_threads(video_url, t["caption"], is_video=True)
        if threads_post_id:
            hist_entry["threads_post_id"] = threads_post_id
            save("history.json", hist)

    else:
        print("=== Publishing Mode: STATIC PHOTO (Fallback) ===")
        img_url = resolve_public_url(t["image"], repo)

        print("Step 1: Creating Instagram media container...")
        c_res = call("POST", f"{base}/{uid}/media", {
            "image_url": img_url,
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
        for attempt in range(20):
            st_res = call("GET", f"{base}/{container_id}", {
                "fields": "status_code,status",
                "access_token": tok
            })
            st = st_res.get("status_code")
            print(f"Container status check ({attempt+1}/20): {st}")
            if st == "FINISHED":
                finished = True
                print("Container status is FINISHED. Allowing 5s propagation buffer before media_publish...")
                time.sleep(5)
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
        }, max_retries=5, initial_delay=8, retry_codes=(1, 2, 4, 17, 341, 9007))
        post_id = pub_res.get("id")
        if not post_id:
            print("::error::Media publishing did not return a post ID:", pub_res)
            sys.exit(1)

        hist_entry = {
            "date": t["date"],
            "id": t["id"],
            "tag": t.get("tag", ""),
            "status": "published",
            "type": "photo",
            "post_id": post_id,
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "caption": t["caption"]
        }
        hist.append(hist_entry)
        save("history.json", hist)
        print(f"SUCCESS: Post published to Instagram! Media ID: {post_id}")

        # Cross-post to Meta Threads
        threads_post_id = publish_to_threads(img_url, t["caption"], is_video=False)
        if threads_post_id:
            hist_entry["threads_post_id"] = threads_post_id
            save("history.json", hist)

def dryrun():
    print("=== STARTING FULL REEL DRY RUN ===")
    prepare()
    t = load("today.json", {})
    if t.get("skip"):
        print(f"Dry run complete: Day already marked as published ({t.get('reason')}).")
        return
    print("Dry run: Validating Reel container requirements...")
    print(f"Date: {t.get('date')}")
    print(f"Quote ID: {t.get('id')}")
    print(f"Tag: {t.get('tag')}")
    print(f"Media Type: {t.get('media_type')}")
    print(f"Video: {t.get('video')}")
    print(f"Cover: {t.get('image')}")
    print(f"Caption Length: {len(t.get('caption', ''))} characters")
    th_token_set = bool(os.environ.get("THREADS_ACCESS_TOKEN", "").strip())
    print(f"Threads Cross-post: {'Configured (Active)' if th_token_set else 'Awaiting THREADS_ACCESS_TOKEN secret'}")
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
