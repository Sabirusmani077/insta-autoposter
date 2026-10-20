import os
import json
import unittest
from PIL import Image

from quality import validate_quote, score_candidate, select_best_candidate
from render import render, W, H, WATERMARK
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
        self.assertEqual(WATERMARK, "@sabir_usmani_077")
        self.assertNotIn("MDK", WATERMARK)

    def test_candidate_selection_and_scoring(self):
        """Ensure best candidate selection picks top scoring unposted quote."""
        best_quote, score, count = select_best_candidate(self.quotes, self.history)
        self.assertIsNotNone(best_quote)
        self.assertGreater(score, 70.0, "Selected quote score should be above quality threshold")
        self.assertEqual(count, 365)

    def test_image_rendering_specs(self):
        """Test image generation for correct dimensions (1080x1350) and file creation."""
        test_img = "images/test_spec.jpg"
        q = self.quotes[0]
        render(q["id"], q["tag"], q["lines"], test_img)
        
        self.assertTrue(os.path.exists(test_img))
        with Image.open(test_img) as im:
            self.assertEqual(im.size, (1080, 1350), "Dimensions must be 1080x1350 (4:5)")
            self.assertEqual(im.mode, "RGB", "Color mode must be RGB")
        
        size_kb = os.path.getsize(test_img) / 1024
        self.assertGreater(size_kb, 30, "Rendered image file should be larger than 30KB")
        
        # Cleanup
        if os.path.exists(test_img):
            os.remove(test_img)

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
