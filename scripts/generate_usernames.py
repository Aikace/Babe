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
    "ace", "alex", "aria", "axel", "ava", "adam", "alan", "amy", "anna", "andy",
    "ben", "blake", "beau", "blue", "brad", "beth", "bill", "bob", "carl", "cleo",
    "cole", "chad", "chris", "clay", "dane", "dana", "drew", "dan", "dave", "dean",
    "eden", "evan", "eli", "emma", "ella", "eric", "faye", "finn", "fox", "fred",
    "gabe", "gary", "glen", "grace", "hank", "hope", "hugh", "ian", "iris", "ivy",
    "jack", "jade", "jake", "james", "jane", "jason", "jay", "jean", "jeff", "jenny",
    "jess", "jill", "joan", "joel", "john", "joy", "juan", "jude", "june", "kai",
    "kane", "kara", "karl", "kate", "kira", "kurt", "kyle", "lace", "lane", "lara",
    "laura", "lee", "leo", "liam", "lily", "lisa", "logan", "lola", "luca", "luke",
    "luna", "lynn", "marc", "mark", "matt", "max", "mia", "mike", "milo", "mona",
    "moss", "nate", "neil", "nia", "nick", "nina", "noel", "nora", "nova", "omar",
    "otto", "owen", "page", "paul", "pax", "pete", "phil", "quinn", "rain", "ray",
    "reed", "remy", "rex", "rhea", "rich", "rick", "rio", "rob", "rosa", "rose",
    "ross", "ruby", "russ", "ruth", "ryan", "sage", "sam", "sara", "saul", "sean",
    "seth", "shay", "skye", "stan", "sue", "tara", "tate", "ted", "theo", "tina",
    "todd", "tony", "tori", "trey", "troy", "tyler", "uma", "val", "vale", "vera",
    "wade", "walt", "wes", "will", "wren", "wyatt", "zach", "zane", "zara", "zeke",
    "zion", "zoe",
    "gray", "ren", "sia", "rue", "bay", "ash"
}

# High-demand brandable / aesthetic words
THEME_WORDS = {
    # Power/Status
    "money", "cash", "trade", "king", "queen", "chief", "boss", "alpha", "rich",
    "gold", "crown", "royal", "elite", "prime", "noble", "ultra", "reign", "lord",
    "titan", "legend", "icon", "hero", "god", "saint",
    
    # Tech
    "code", "data", "hack", "cloud", "cyber", "pixel", "dev", "app", "web", "byte",
    "chip", "tech", "node", "bot", "algo", "api", "stack", "loop", "root", "core",
    "log", "ping", "host", "port", "link",
    
    # Crypto/Finance  
    "coin", "mint", "swap", "pool", "stake", "yield", "vault", "chain", "block",
    "dao", "token", "whale", "hodl", "pump", "bull", "bear", "moon", "gem", "degen",
    "ape",
    
    # Nature
    "fire", "ice", "wolf", "hawk", "lion", "sun", "star", "sky", "sea", "oak", "elm",
    "pine", "rose", "fern", "rain", "snow", "sand", "reef", "lake", "clay", "rock",
    "jade", "opal", "onyx",
    
    # Gaming/Culture
    "play", "game", "grind", "quest", "loot", "raid", "pro", "clan", "guild", "rank",
    "level", "mode", "zone", "arena", "score", "win", "epic", "rare", "myth",
    
    # Emotion/Vibe
    "love", "hope", "fear", "rage", "dream", "bliss", "peace", "fury", "mood", "soul",
    "mind", "calm", "wild", "bold", "dark", "pure", "true", "real", "raw", "deep",
    "free", "lone", "lost", "zen",
    
    # Original (minus duplicates)
    "echo", "flux", "nova", "vibe", "apex", "drift", "edge",
    "flow", "glow", "haze", "lux", "mesh", "mist", "neon", "orb",
    "peak", "pulse", "rift", "rush", "shift", "spark", "storm",
    "surge", "tide", "void", "wave", "arc", "bolt", "dawn", "dusk",
    "fuse", "grid", "iris", "leaf", "lore", "rune",
    "silk", "spin", "sync", "volt", "warp", "wind", "wisp", "blaze",
    "frost", "ember", "prism", "cipher", "orbit", "aura",
    "zeal", "zest", "flare", "gleam",
    "lumen", "lyric", "manor", "modal", "morph", "mystic", "niche",
    "phase", "pivot", "plaid", "polar", "realm", "remix", "reset",
    "rider", "scala", "scout", "sigma", "slate", "sleek", "smart",
    "solar", "sonic", "squad", "stark", "steel", "swift",
    "union", "valor", "vapor", "verve", "vigor", "viral",
    "vista", "vital", "vivid", "voice", "vogue"
}

ACRONYMS = {
    "AI", "VR", "AR", "VPN", "CEO", "MVP", "VIP", "OG", "DJ", "MC", "PR", "GM", "GG", "EU", "UK", "US", "LA", "NY",
    "HQ", "IO", "DB", "IT", "PC", "TV", "FM", "AM", "PM", "AC", "DC", "HP", "BMW", "NBA", "NFL", "NHL", "MLB", "UFC",
    "BTC", "ETH", "SOL", "NFT", "APR", "ROI", "IPO", "GDP", "ATM", "ATF", "FBI", "CIA", "DOJ", "IRS", "NASA",
    "DEA", "ICE", "WHO", "CNN", "BBC", "FOX", "ESPN", "WWE", "MMA"
}
# convert to lower just in case
ACRONYMS = {a.lower() for a in ACRONYMS}

# ── Scoring ───────────────────────────────────────────────────────────────────

def _is_pronounceable(name: str) -> bool:
    """Good vowel/consonant balance = easier to say and remember."""
    vowels = sum(1 for c in name if c in "aeiou")
    ratio  = vowels / len(name) if len(name) > 0 else 0
    return 0.15 <= ratio <= 0.70

def _has_clean_pattern(name: str) -> bool:
    """No three consecutive consonants or vowels."""
    if len(name) < 3:
        return True
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
    length_pts = {2: 65, 3: 48, 4: 25, 5: 14, 6: 7}
    score += length_pts.get(L, 0)

    # ② Real English word
    if n in WORDLIST:
        score += 20

    # ③ Common first name
    if n in FIRST_NAMES:
        score += 15

    # ④ Brandable / theme word
    if n in THEME_WORDS:
        score += 10

    # ⑤ Pronounceable
    if _is_pronounceable(n):
        score += 6

    # ⑥ Clean consonant/vowel pattern
    if _has_clean_pattern(n):
        score += 4

    # ⑦ All letters, no digits / underscores
    if n.isalpha():
        score += 3

    # ⑧ No consecutive repeated chars (aab, llc look spammy)
    if not any(n[i] == n[i+1] for i in range(L-1)):
        score += 2

    return min(score, 100)

def get_priority(score: int) -> str:
    if score >= 80: return "HIGH"
    if score >= 55: return "MEDIUM"
    return "LOW"

def get_value_estimate(score: int) -> str:
    if score >= 90: return "💎 $5,000-$50,000+"
    if score >= 80: return "🔥 $1,000-$5,000"
    if score >= 65: return "⭐ $200-$1,000"
    if score >= 50: return "📌 $50-$200"
    return "< $50"

# ── Generators ────────────────────────────────────────────────────────────────

VOWELS     = list("aeiou")
CONSONANTS = list("bcdfghjklmnpqrstvwxyz")

def generate_candidates() -> set:
    candidates: set = set()
    alpha = "abcdefghijklmnopqrstuvwxyz"

    # ① Every 2-letter combo
    for combo in itertools.product(alpha, repeat=2):
        candidates.add("".join(combo))

    # ② Every 3-letter combo
    for combo in itertools.product(alpha, repeat=3):
        candidates.add("".join(combo))

    # ③ Dictionary words up to 6 chars
    candidates.update(w for w in WORDLIST if 2 <= len(w) <= 6 and w.isalpha())

    # ④ Theme + first-name sets + acronyms
    candidates.update(THEME_WORDS)
    candidates.update(FIRST_NAMES)
    candidates.update(ACRONYMS)

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
    return name.lower() in BLOCKLIST

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
        if s >= 35:
            scored.append((s, name))

    random.shuffle(scored)
    
    batch = scored[:600]
    print(f"    {len(scored):,} valid candidates (score ≥ 35). Taking random batch of {len(batch):,}.")

    added = 0
    for score, name in batch:
        priority = get_priority(score)
        estimate = get_value_estimate(score)
        
        platforms = ["instagram"] if len(name) <= 3 else ["instagram", "x"]
        
        for platform in platforms:
            if add_to_watchlist(name, platform, priority, score, estimate):
                added += 1

    print(f"✅  Added / updated {added} watchlist entries")

if __name__ == "__main__":
    run()
