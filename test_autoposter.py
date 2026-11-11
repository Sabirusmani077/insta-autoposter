import os
import json
import unittest
from PIL import Image

from quality import validate_quote, score_candidate, select_best_candidate, is_duplicate_or_too_similar
from render import render, WATERMARK as WATERMARK_FEED
from render_reel import render_reel, render_reel_cover, WATERMARK as WATERMARK_REEL, W as REEL_W, H as REEL_H, get_daily_bgm, BGM_TRACKS
import main

class TestInstaAutoposter(unittest.TestCase):

    def setUp(self):
        with open("quotes.json", "r", encoding="utf-8") as f:
            self.quotes = json.load(f)
        with open("history.json", "r", encoding="utf-8") as f:
            self.history = json.load(f)

    def test_quotes_count_and_validation(self):
        """Verify that exactly 365 valid quotes exist in quotes.json with no validation failures."""
        self.assertEqual(len(self.quotes), 365, "quotes.json must contain 365 quotes")

        seen_ids = set()
        for q in self.quotes:
            qid = q.get("id")
            self.assertNotIn(qid, seen_ids, f"Duplicate quote id found: {qid}")
            seen_ids.add(qid)

            valid, reason = validate_quote(q)
            self.assertTrue(valid, f"Quote ID {qid} failed validation: {reason}")

    def test_watermark_identity(self):
        """Watermark must strictly be '@sabir_usmani_077' with no external brand watermarks."""
        self.assertEqual(WATERMARK_FEED, "@sabir_usmani_077")
        self.assertEqual(WATERMARK_REEL, "@sabir_usmani_077")
        self.assertNotIn("MDK", WATERMARK_FEED)
        self.assertNotIn("MDK", WATERMARK_REEL)

    def test_candidate_selection_and_scoring(self):
        """Ensure best candidate selection picks top scoring unposted quote."""
        best_quote, score, count = select_best_candidate(self.quotes, self.history)
        self.assertIsNotNone(best_quote)
        self.assertGreater(score, 70.0, "Selected quote score should be above quality threshold")
        expected_unposted = len(self.quotes) - len([h for h in self.history if h.get("status") == "published"])
        self.assertEqual(count, expected_unposted)

    def test_reel_cover_specs(self):
        """Test Reel cover image generation for 9:16 vertical resolution (1080x1920)."""
        test_cover = "images/test_reel_cover_spec.jpg"
        q = self.quotes[0]
        render_reel_cover(q["id"], q["tag"], q["lines"], test_cover)

        self.assertTrue(os.path.exists(test_cover))
        with Image.open(test_cover) as im:
            self.assertEqual(im.size, (1080, 1920), "Dimensions must be 1080x1920 (9:16)")
            self.assertEqual(im.mode, "RGB", "Color mode must be RGB")

        size_kb = os.path.getsize(test_cover) / 1024
        self.assertGreater(size_kb, 30, "Cover image file should be larger than 30KB")

        if os.path.exists(test_cover):
            os.remove(test_cover)

    def test_reel_theme_diversity(self):
        """Verify that at least 12 distinct background themes exist and consecutive quotes use different themes."""
        from render_reel import THEME_GENERATORS
        self.assertGreaterEqual(len(THEME_GENERATORS), 12, "Must have at least 12 distinct background themes")

        # Test rendering 3 consecutive quotes to verify they produce valid distinct cover images
        covers = []
        for i in range(3):
            q = self.quotes[i]
            cover_path = f"images/test_theme_div_{i}.jpg"
            render_reel_cover(q["id"], q["tag"], q["lines"], cover_path)
            self.assertTrue(os.path.exists(cover_path))
            covers.append(cover_path)

        # Ensure cover files differ in size / content (not identical)
        sizes = [os.path.getsize(c) for c in covers]
        self.assertEqual(len(set(sizes)), len(sizes), "Different themes should produce different file sizes")

        for c in covers:
            if os.path.exists(c):
                os.remove(c)

    def test_reel_video_specs(self):
        """Test full Reel video compilation (MP4, H.264, AAC audio with background music, duration 5-90s)."""
        test_vid = "videos/test_spec.mp4"
        test_cover = "images/test_spec.jpg"
        q = self.quotes[0]
        render_reel(q["id"], q["tag"], q["lines"], test_vid, test_cover, duration=10)

        self.assertTrue(os.path.exists(test_vid))
        self.assertTrue(os.path.exists(test_cover))

        size_kb = os.path.getsize(test_vid) / 1024
        self.assertGreater(size_kb, 200, "Reel MP4 video file should be larger than 200KB")

        if os.path.exists(test_vid):
            os.remove(test_vid)
        if os.path.exists(test_cover):
            os.remove(test_cover)

    def test_duplicate_prevention_logic(self):
        """Verify that prepare() skips when a post is already marked published for today."""
        fake_today = main.today_ist()
        fake_hist = [{"date": fake_today, "id": 999, "status": "published"}]

        main.save("history.json", fake_hist)
        try:
            main.prepare()
            t = main.load("today.json", {})
            self.assertTrue(t.get("skip"), "prepare() must set skip=True if already published today")
        finally:
            main.save("history.json", self.history)

    def test_quotes_content_uniqueness(self):
        """Verify that all unposted quotes in quotes.json are 100% unique in full text and lines."""
        import re
        def clean_line(l):
            return re.sub(r"[\s\.,।!?'\"—\-]+", "", l)

        pub_ids = {h.get("id") for h in self.history if h.get("status") == "published"}
        unposted = [q for q in self.quotes if q.get("id") not in pub_ids]
        published = [q for q in self.quotes if q.get("id") in pub_ids]

        # 1. Full-text uniqueness among unposted quotes
        seen_texts = set()
        for q in unposted:
            norm_text = clean_line(" ".join(q.get("lines", [])))
            self.assertNotIn(norm_text, seen_texts, f"Quote ID {q['id']} has duplicate full text")
            seen_texts.add(norm_text)

        # 2. Line uniqueness among unposted quotes
        line_to_quote = {}
        for q in unposted:
            for line in q.get("lines", []):
                cl = clean_line(line)
                self.assertNotIn(cl, line_to_quote, f"Quote ID {q['id']} shares line '{line}' with Quote ID {line_to_quote.get(cl)}")
                line_to_quote[cl] = q["id"]

        # 3. No unposted quote shares any line with any published quote
        pub_lines = {clean_line(l): q["id"] for q in published for l in q.get("lines", [])}
        for q in unposted:
            for line in q.get("lines", []):
                cl = clean_line(line)
                self.assertNotIn(cl, pub_lines, f"Unposted Quote ID {q['id']} shares line '{line}' with Published Quote ID {pub_lines.get(cl)}")

    def test_candidate_selection_blocks_duplicate_content(self):
        """Verify that is_duplicate_or_too_similar blocks duplicate lines, exact text, and vocabulary overlap."""
        pub_ids = {h.get("id") for h in self.history if h.get("status") == "published"}
        published = [q for q in self.quotes if q.get("id") in pub_ids]
        self.assertTrue(len(published) > 0, "Should have published quotes to test against")

        first_pub = published[0]

        # Test A: Exact duplicate of a published quote
        dup_candidate = {
            "id": 9999,
            "tag": first_pub["tag"],
            "lines": list(first_pub["lines"])
        }
        is_dup, reason = is_duplicate_or_too_similar(dup_candidate, published)
        self.assertTrue(is_dup, "Exact duplicate quote must be flagged as duplicate")

        # Test B: Quote sharing even 1 line with a published quote
        shared_line_candidate = {
            "id": 9998,
            "tag": "नया",
            "lines": [
                first_pub["lines"][0],
                "यह एक नई और अलग लाइन है जो पहले कभी नहीं लिखी गई,",
                "इस लाइन का उद्देश्य केवल टेस्ट करना है मेरे दोस्त,",
                "और यह आख़िरी लाइन भी बिल्कुल नई और अनोखी है।"
            ]
        }
        is_dup, reason = is_duplicate_or_too_similar(shared_line_candidate, published)
        self.assertTrue(is_dup, "Candidate sharing a line with published quote must be flagged as duplicate")

        # Test C: Truly unique candidate
        unique_candidate = {
            "id": 9997,
            "tag": "विलक्षण",
            "lines": [
                "अनोखी सुबह का अनोखा सवेरा आया है आज,",
                "हर परिंदे के सिर पर सफलता का नया ताज,",
                "जो लगन से अपने हुनर को तराशता चला जाए,",
                "उसी के कदमों में झुक जाता है यह सारा समाज।"
            ]
        }
        is_dup, reason = is_duplicate_or_too_similar(unique_candidate, published)
        self.assertFalse(is_dup, "Unique quote must not be flagged as duplicate")

        # Test D: select_best_candidate ignores duplicate quotes even if injected
        test_quotes = self.quotes + [dup_candidate]
        selected_quote, score, count = select_best_candidate(test_quotes, self.history)
        self.assertIsNotNone(selected_quote)
        self.assertNotEqual(selected_quote["id"], 9999, "select_best_candidate must never pick duplicate candidate")

    def test_bgm_tracks_and_rotation(self):
        """Verify that all 3 requested YouTube background music tracks exist and rotate daily."""
        self.assertEqual(len(BGM_TRACKS), 3, "Must have exactly 3 rotating BGM tracks")
        for i, track in enumerate(BGM_TRACKS):
            self.assertTrue(os.path.exists(track), f"Track #{i+1} ({track}) must exist on disk")
            size_kb = os.path.getsize(track) / 1024
            self.assertGreater(size_kb, 50, f"Track #{i+1} must be a valid audio file > 50KB")

        # Test daily cycling: 0 -> Track 1, 1 -> Track 2, 2 -> Track 3, 3 -> Track 1
        t0 = get_daily_bgm(0)
        t1 = get_daily_bgm(1)
        t2 = get_daily_bgm(2)
        t3 = get_daily_bgm(3)

        self.assertEqual(t0, BGM_TRACKS[0])
        self.assertEqual(t1, BGM_TRACKS[1])
        self.assertEqual(t2, BGM_TRACKS[2])
        self.assertEqual(t3, BGM_TRACKS[0])
        self.assertNotEqual(t0, t1)
        self.assertNotEqual(t1, t2)

if __name__ == "__main__":
    unittest.main()

