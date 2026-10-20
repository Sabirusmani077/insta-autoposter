"""
Quality validation and scoring engine for Instagram Hindi content autoposter.
Ensures every selected quote meets strict standards for:
- Devanagari character integrity
- Readability and balanced typography
- Absence of duplicates, offensive terms, and fabricated attributions
- Theme variety and poetic cadence
"""
import re

BLOCKED_WORDS = {
    "गाली", "नफ़रत", "धोखा", "घमंड", "कमीना", "अपमान", "लाश", "मौत"
}

HIGH_IMPACT_KEYWORDS = {
    "मंज़िल", "हौसला", "मेहनत", "सब्र", "वक़्त", "वक़्त", "क़िस्मत", "तक़दीर",
    "जीत", "इतिहास", "रास्ता", "पहचान", "सफलता", "अनुशासन", "विश्वास", "सपना",
    "उम्मीद", "शुरुआत", "हिम्मत", "इंसान", "लक्ष्य", "संघर्ष", "ज़िंदगी"
}

def validate_quote(q):
    """
    Validates structural and content requirements of a quote.
    Returns (is_valid: bool, message: str)
    """
    if not isinstance(q, dict):
        return False, "Quote is not a dictionary"
    
    qid = q.get("id")
    tag = q.get("tag", "").strip()
    lines = q.get("lines", [])

    if qid is None or not isinstance(qid, int):
        return False, f"Invalid quote id: {qid}"
    
    if not tag or len(tag) < 2 or len(tag) > 20:
        return False, f"Invalid tag '{tag}' in quote {qid}"
    
    if not isinstance(lines, list) or len(lines) < 2 or len(lines) > 4:
        return False, f"Quote {qid} must have 2 to 4 lines, found {len(lines)}"

    full_text = " ".join(lines)

    # Check for Unicode corruption (e.g. '?', replacement characters, or empty lines)
    if "\ufffd" in full_text or "??" in full_text:
        return False, f"Quote {qid} contains corrupted Unicode characters"
    
    # Check for fake author attributions (e.g. '— गालिब', '- APJ Abdul Kalam')
    if any(re.search(r"[-—~]\s*[\w\s]+$", line) for line in lines):
        return False, f"Quote {qid} appears to contain an author attribution, must be original"

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            return False, f"Line {i+1} in quote {qid} is empty"
        if len(line) < 6:
            return False, f"Line {i+1} in quote {qid} is too short ({len(line)} chars)"
        if len(line) > 55:
            return False, f"Line {i+1} in quote {qid} is too long ({len(line)} chars) - exceeds safe typography width"
        
        # Check Devanagari presence
        has_devanagari = any(0x0900 <= ord(c) <= 0x097F for c in line)
        if not has_devanagari:
            return False, f"Line {i+1} in quote {qid} does not contain Devanagari characters"

        # Check blocklist using whole-word matching
        words = set(re.findall(r"[\u0900-\u097F]+", line))
        for bw in BLOCKED_WORDS:
            if bw in words:
                return False, f"Quote {qid} contains restricted keyword: {bw}"

    return True, "Valid"

def score_candidate(q, history):
    """
    Calculates a quality score (0 - 100) for a candidate quote:
    - Line length balance (0-20)
    - Theme / tag freshness against recent history (0-25)
    - Rhyme / poetic cadence (0-20)
    - Emotional impact keywords (0-20)
    - Readability word count (0-15)
    """
    lines = q.get("lines", [])
    tag = q.get("tag", "").strip()
    
    lengths = [len(l.strip()) for l in lines]
    avg_len = sum(lengths) / len(lengths)
    variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
    
    # 1. Line Balance Score (0-20): lower variance = more symmetric typography
    balance_score = max(0.0, 20.0 - (variance * 0.5))

    # 2. Tag Freshness Score (0-25): penalize repeating the same tag as recent posts
    recent_tags = [h.get("tag") for h in history[-7:] if h.get("tag")]
    if not recent_tags:
        freshness_score = 25.0
    elif tag == recent_tags[-1]:
        freshness_score = 5.0  # posted yesterday
    elif tag in recent_tags:
        freshness_score = 15.0 # posted within last 7 days
    else:
        freshness_score = 25.0 # fresh theme

    # 3. Rhyme / Cadence Score (0-20)
    # Check end of line 2 and line 4 (or 1 and 2 if 2-line)
    rhyme_score = 10.0
    if len(lines) == 4:
        end2 = lines[1].strip(" ,।!.-")[-3:]
        end4 = lines[3].strip(" ,।!.-")[-3:]
        if end2 and end4 and (end2 == end4 or end2[-2:] == end4[-2:]):
            rhyme_score = 20.0
    elif len(lines) == 2:
        end1 = lines[0].strip(" ,।!.-")[-3:]
        end2 = lines[1].strip(" ,।!.-")[-3:]
        if end1 and end2 and (end1 == end2 or end1[-2:] == end2[-2:]):
            rhyme_score = 20.0

    # 4. High Impact Keywords (0-20)
    full_text = " ".join(lines)
    keyword_hits = sum(1 for kw in HIGH_IMPACT_KEYWORDS if kw in full_text)
    keyword_score = min(20.0, keyword_hits * 7.0)

    # 5. Readability / Word count (0-15)
    word_count = len(full_text.split())
    if 16 <= word_count <= 28:
        readability_score = 15.0
    elif 12 <= word_count <= 34:
        readability_score = 10.0
    else:
        readability_score = 6.0

    total_score = balance_score + freshness_score + rhyme_score + keyword_score + readability_score
    return round(total_score, 2)

def select_best_candidate(quotes, history):
    """
    Selects the highest quality valid candidate that has not been posted yet.
    Returns (selected_quote, score, evaluated_candidates_count)
    """
    used_ids = {h.get("id") for h in history if h.get("status") == "published"}
    unposted = [q for q in quotes if q.get("id") not in used_ids]
    
    if not unposted:
        return None, 0.0, 0
    
    scored_candidates = []
    for q in unposted:
        is_valid, reason = validate_quote(q)
        if not is_valid:
            continue
        score = score_candidate(q, history)
        scored_candidates.append((score, q))
    
    if not scored_candidates:
        return None, 0.0, len(unposted)
    
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_quote = scored_candidates[0]
    return best_quote, best_score, len(scored_candidates)
