import json, os, sys, time, datetime, urllib.request, urllib.parse
from render import render
ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(ROOT, f)
CAPTIONS = [
 "आज का दिन आपका है। इसे पूरी ताक़त से जिएँ। 💪",
 "जिसे आज ये सुनने की ज़रूरत हो, उसे ज़रूर भेजें। ❤️",
 "एक लाइन में बताइए, आज आपका लक्ष्य क्या है? 👇",
 "इसे सेव कर लें, जब हिम्मत टूटे तब पढ़ना। 🔖",
 "छोटा क़दम भी क़दम होता है। चलते रहिए। 🌱",
 "आप कितना भी थके हों, रुकना विकल्प नहीं है। 🔥",
 "आज ख़ुद से एक वादा कीजिए और उसे निभाइए। ✅",
 "कौन सी पंक्ति आपके दिल को छू गई? कमेंट में लिखें। 💬",
 "अपने उस दोस्त को टैग करें जो कभी हार नहीं मानता। 🤝",
 "सब्र रखिए, मेहनत रंग लाती है। 🌅",
]
HASH = ["#हिंदीशायरी","#हिंदीमोटिवेशन","#motivation","#hindiquotes","#success","#lifelessons","#selfgrowth","#positivevibes","#मेहनत","#सफलता","#discipline","#dailymotivation","#hindishayari","#जिंदगी","#hustle"]

def load(f, d):
    try: return json.load(open(P(f), encoding="utf-8"))
    except FileNotFoundError: return d
def save(f, o): json.dump(o, open(P(f), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
def today_ist():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date().isoformat()

def prepare():
    quotes, hist, today = load("quotes.json", []), load("history.json", []), today_ist()
    if any(h["date"] == today and h["status"] == "published" for h in hist):
        print("Already published today. Nothing to do."); save("today.json", {"skip": True}); return
    used = {h["id"] for h in hist if h["status"] == "published"}
    left = [q for q in quotes if q["id"] not in used]
    print(f"Quotes left in queue: {len(left)}")
    if len(left) < 7: print("::warning::Fewer than 7 quotes left. Add more to quotes.json")
    if not left: print("::error::Quote bank empty"); sys.exit(1)
    q = left[0]; n = len(used)
    img = f"images/{today}.jpg"
    render(q["id"], q["tag"], q["lines"], P(img))
    tags = ["#हिंदीशायरी", "#hindishayari"] + [HASH[(n * 3 + i) % len(HASH)] for i in range(5)]
    tags = list(dict.fromkeys(tags))
    caption = CAPTIONS[n % len(CAPTIONS)] + "\n\n✍️ Original shayari | @sabir_usmani_077\n\n" + " ".join(tags)
    assert len(caption) < 2000 and len(tags) <= 30
    save("today.json", {"date": today, "id": q["id"], "image": img, "caption": caption})
    print("Prepared:", img); print(caption)

def call(method, url, params):
    data = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + ("?" + data if method == "GET" else ""), data=None if method == "GET" else data.encode(), method=method)
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        print("::error::API error", e.read().decode()); sys.exit(1)

def publish():
    t = load("today.json", {})
    if t.get("skip"): return
    hist = load("history.json", [])
    if any(h["date"] == t["date"] and h["status"] == "published" for h in hist): print("Duplicate blocked."); return
    tok, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
    url = f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/main/{t['image']}"
    for _ in range(6):  # wait until the image is reachable
        try:
            if urllib.request.urlopen(url, timeout=20).status == 200: break
        except Exception: time.sleep(10)
    base = "https://graph.instagram.com/v21.0"
    c = call("POST", f"{base}/{uid}/media", {"image_url": url, "caption": t["caption"], "access_token": tok})["id"]
    for _ in range(12):
        st = call("GET", f"{base}/{c}", {"fields": "status_code", "access_token": tok}).get("status_code")
        if st == "FINISHED": break
        if st == "ERROR": print("::error::Container failed"); sys.exit(1)
        time.sleep(5)
    pid = call("POST", f"{base}/{uid}/media_publish", {"creation_id": c, "access_token": tok})["id"]
    hist.append({"date": t["date"], "id": t["id"], "status": "published", "post_id": pid, "caption": t["caption"]})
    save("history.json", hist); print("Published", pid)

if __name__ == "__main__":
    {"prepare": prepare, "publish": publish}[sys.argv[1]]()
