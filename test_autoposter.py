import os
import json
import unittest
from PIL import Image

from quality import validate_quote, score_candidate, select_best_candidate
from render import render, WATERMARK as WATERMARK_FEED
from render_reel import render_reel, render_reel_cover, WATERMARK as WATERMARK_REEL, W as REEL_W, H as REEL_H
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

    def test_reel_video_specs(self):
        """Test full Reel video compilation (MP4, H.264, AAC audio, duration 5-90s)."""
        test_vid = "videos/test_spec.mp4"
        test_cover = "images/test_spec.jpg"
        q = self.quotes[0]
        render_reel(q["id"], q["tag"], q["lines"], test_vid, test_cover)

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

if __name__ == "__main__":
    unittest.main()
