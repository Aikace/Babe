"""
generate_usernames.py
────────────────────
Generates high-value username candidates, scores them,
and populates the Supabase watchlist.
"""

import os
import sys
import itertools
import random

# Allow running from repo root or scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from db import add_to_watchlist

# ── Load data files ───────────────────────────────────────────────────────────
_DATA = os.path.join(os.path.dirname(__file__), "..", "data")

def _load(filename: str) -> set:
    path = os.path.join(_DATA, filename)
    with open(path, encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}

WORDLIST  = _load("wordlist.txt")
BLOCKLIST = _load("blocklist.txt")

# Curated first names that make great handles
FIRST_NAMES = {
    "ace", "alex", "aria", "axel", "ava", "blue", "blake", "beau",
    "cleo", "cole", "dana", "drew", "eden", "evan", "faye", "finn",
    "gray", "jade", "jake", "jay", "june", "kai", "kira", "kyle",
    "lane", "lee", "leo", "liam", "lily", "luna", "mia", "max",
    "noel", "nova", "omar", "pax", "quinn", "ray", "reed", "rex",
    "rio", "rose", "sam", "sage", "skye", "tate", "theo", "troy",
    "vale", "will", "wren", "zara", "zion", "zoe", "ivy", "eli",
    "nia", "ren", "sia", "rue", "bay", "fox", "ash", "joy",
}

# High-demand brandable / aesthetic words
THEME_WORDS = {
    "echo", "flux", "nova", "vibe", "apex", "crest", "drift", "edge",
    "flow", "glow", "haze", "lux", "mesh", "mist", "neon", "orb",
    "peak", "pulse", "rift", "rush", "shift", "spark", "storm",
    "surge", "tide", "void", "wave", "arc", "bolt", "dawn", "dusk",
    "fuse", "grid", "iris", "leaf", "lore", "onyx", "opal", "rune",
    "silk", "spin", "sync", "volt", "warp", "wind", "wisp", "blaze",
    "frost", "ember", "prism", "cipher", "pixel", "orbit", "aura",
    "zen", "zeal", "zest", "quest", "crest", "flare", "gleam",
    "lumen", "lyric", "manor", "modal", "morph", "mystic", "niche",
    "phase", "pivot", "plaid", "polar", "realm", "remix", "reset",
    "rider", "scala", "scout", "sigma", "slate", "sleek", "smart",
    "solar", "sonic", "squad", "stark", "steel", "swift", "ultra",
    "union", "valor", "vapor", "vault", "verve", "vigor", "viral",
    "vista", "vital", "vivid", "voice", "vogue",
}

# ── Scoring ───────────────────────────────────────────────────────────────────

def _is_pronounceable(name: str) -> bool:
    """Good vowel/consonant balance = easier to say and remember."""
    vowels = sum(1 for c in name if c in "aeiou")
    ratio  = vowels / len(name)
    return 0.15 <= ratio <= 0.70

def _has_clean_pattern(name: str) -> bool:
    """No three consecutive consonants or vowels."""
    vow = set("aeiou")
    run = 1
    for i in range(1, len(name)):
        if (name[i] in vow) == (name[i-1] in vow):
            run += 1
            if run >= 3:
                return False
        else:
            run = 1
    return True

def score_username(name: str) -> int:
    """Return value score 0-100 for a username."""
    score = 0
    n = name.lower()
    L = len(n)

    # ① Length — king metric
    length_pts = {2: 42, 3: 32, 4: 22, 5: 13, 6: 7}
    score += length_pts.get(L, 2)

    # ② Real English word
    if n in WORDLIST:
        score += 18

    # ③ Common first name
    if n in FIRST_NAMES:
        score += 14

    # ④ Brandable / theme word
    if n in THEME_WORDS:
        score += 8

    # ⑤ Pronounceable
    if _is_pronounceable(n):
        score += 8

    # ⑥ Clean consonant/vowel pattern
    if _has_clean_pattern(n):
        score += 4

    # ⑦ All letters, no digits / underscores
    if n.isalpha():
        score += 4

    # ⑧ No consecutive repeated chars (aab, llc look spammy)
    if not any(n[i] == n[i+1] for i in range(L-1)):
        score += 3

    return min(score, 100)

def get_priority(score: int) -> str:
    if score >= 75: return "HIGH"
    if score >= 50: return "MEDIUM"
    return "LOW"

def get_value_estimate(score: int) -> str:
    if score >= 90: return "💎 $1,000 – $10,000+"
    if score >= 75: return "🔥 $200 – $1,000"
    if score >= 60: return "⭐ $50 – $200"
    if score >= 40: return "📌 $10 – $50"
    return "< $10"

# ── Generators ────────────────────────────────────────────────────────────────

VOWELS     = list("aeiou")
CONSONANTS = list("bcdfghjklmnpqrstvwxyz")

def generate_candidates() -> set:
    candidates: set = set()

    # ① Every 2-letter combo
    for combo in itertools.product("abcdefghijklmnopqrstuvwxyz", repeat=2):
        candidates.add("".join(combo))

    # ② Pronounceable 3-letter patterns: CVC, VCV, CCV, VCC
    for c1 in CONSONANTS:
        for v in VOWELS:
            for c2 in CONSONANTS:
                candidates.add(c1 + v + c2)   # CVC
            for c2 in CONSONANTS:
                candidates.add(v + c1 + c2)   # VCC

    for v1 in VOWELS:
        for c in CONSONANTS:
            for v2 in VOWELS:
                candidates.add(v1 + c + v2)   # VCV

    # ③ Dictionary words up to 6 chars
    candidates.update(w for w in WORDLIST  if 2 <= len(w) <= 6 and w.isalpha())

    # ④ Theme + first-name sets
    candidates.update(THEME_WORDS)
    candidates.update(FIRST_NAMES)

    # ⑤ 4-letter patterns (CVCV, CVCC, CCVC, VCVC) — random sample
    patterns = ["CVCV", "CVCC", "CCVC", "VCVC", "CVVC"]
    for _ in range(800):
        p = random.choice(patterns)
        name = "".join(
            random.choice(CONSONANTS) if ch == "C" else random.choice(VOWELS)
            for ch in p
        )
        candidates.add(name)

    return candidates

# ── Blocklist filter ──────────────────────────────────────────────────────────

def is_blocked(name: str) -> bool:
    n = name.lower()
    return any(bad in n for bad in BLOCKLIST)

# ── Main ──────────────────────────────────────────────────────────────────────

def run() -> None:
    print("🧠  Generating username candidates …")
    candidates = generate_candidates()
    print(f"    {len(candidates):,} raw candidates")

    scored = []
    for name in candidates:
        if not name.isalpha():
            continue
        if is_blocked(name):
            continue
        s = score_username(name)
        if s >= 40:                         # Only track worthwhile names
            scored.append((s, name))

    scored.sort(reverse=True)
    print(f"    {len(scored):,} high-value candidates (score ≥ 40)")

    # Push top 600 per run to avoid hammering Supabase
    added = 0
    for score, name in scored[:600]:
        priority = get_priority(score)
        estimate = get_value_estimate(score)
        for platform in ("instagram", "x"):
            if add_to_watchlist(name, platform, priority, score, estimate):
                added += 1

    print(f"✅  Added / updated {added} watchlist entries")

if __name__ == "__main__":
    run()
