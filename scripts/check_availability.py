"""
check_availability.py
─────────────────────
Checks username availability on Instagram and X.
Triggers auto-claim + Discord alert when a name is free.

Usage:
    python check_availability.py [HIGH|MEDIUM|LOW]
"""

import os
import sys
import time
import random
import requests

sys.path.insert(0, os.path.dirname(__file__))
from db              import get_watchlist, mark_available, mark_checked
from discord_notify  import send_available_alert

X_BEARER = os.environ.get("X_BEARER_TOKEN", "")

# Rotating User-Agent pool to reduce fingerprinting
_IG_UA = [
    "Instagram 275.0.0.27.98 Android (31/12; 560dpi; 1440x3040; samsung; SM-G998B; p3q; exynos2100)",
    "Instagram 264.0.0.19.105 Android (30/11; 480dpi; 1080x2340; OnePlus; IN2023; OnePlus8T; qcom)",
    "Instagram 281.0.0.21.101 Android (33/13; 440dpi; 1080x2400; google; Pixel 7; panther; gs101)",
]

# ── Instagram ─────────────────────────────────────────────────────────────────

def check_instagram(username: str) -> bool | None:
    """
    Returns True  → available
            False → taken
            None  → error / rate-limited (skip for now)
    """
    try:
        headers = {
            "User-Agent":      random.choice(_IG_UA),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept":          "application/json",
            "x-ig-app-id":    "936619743392459",
        }
        url  = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        resp = requests.get(url, headers=headers, timeout=12)

        if resp.status_code == 404:
            return True                              # Account does not exist
        if resp.status_code == 200:
            data = resp.json()
            user = data.get("data", {}).get("user")
            return user is None                      # None means no account found
        if resp.status_code == 429:
            print(f"  [ig] Rate-limited, backing off …")
            time.sleep(60)
            return None
        if resp.status_code in (401, 403):
            print(f"  [ig] Auth/block on @{username} (status {resp.status_code})")
            return None
        return False
    except requests.Timeout:
        print(f"  [ig] Timeout for @{username}")
        return None
    except Exception as e:
        print(f"  [ig] Error for @{username}: {e}")
        return None

# ── X (Twitter) ───────────────────────────────────────────────────────────────

def check_x(username: str) -> bool | None:
    if not X_BEARER:
        return None
    try:
        headers = {"Authorization": f"Bearer {X_BEARER}"}
        url     = f"https://api.twitter.com/2/users/by/username/{username}"
        resp    = requests.get(url, headers=headers, timeout=12)

        if resp.status_code == 200:
            data = resp.json()
            return "data" not in data               # No data = not found = available
        if resp.status_code == 404:
            return True
        if resp.status_code == 429:
            print(f"  [x] Rate-limited, backing off …")
            time.sleep(120)
            return None
        return False
    except Exception as e:
        print(f"  [x] Error for @{username}: {e}")
        return None

# ── Dispatcher ────────────────────────────────────────────────────────────────

def _check(username: str, platform: str) -> bool | None:
    if   platform == "instagram": return check_instagram(username)
    elif platform == "x":         return check_x(username)
    elif platform == "both":
        ig = check_instagram(username);  time.sleep(1.5)
        xr = check_x(username)
        if ig is True or xr is True: return True
        if ig is False or xr is False: return False
        return None
    return None

# ── Main ──────────────────────────────────────────────────────────────────────

def run(priority_filter: str = None) -> None:
    label = priority_filter or "ALL"
    print(f"🔍  Checking availability — priority: {label}")

    entries = get_watchlist(priority=priority_filter)
    print(f"    {len(entries)} usernames queued")

    found = 0
    for entry in entries:
        username = entry["username"]
        platform = entry["platform"]

        available = _check(username, platform)

        if available is True:
            print(f"  🟢 AVAILABLE: @{username} on {platform}")
            mark_available(username, platform)
            found += 1

            # Attempt auto-claim first, then notify
            claim_status = "⏳ attempting …"
            try:
                from auto_claim import claim_username
                success = claim_username(
                    username, platform,
                    entry["value_score"], entry["value_estimate"]
                )
                claim_status = "✅ Claimed!" if success else "❌ Failed — claim manually"
            except Exception as ce:
                claim_status = f"⚠️ {ce}"

            send_available_alert(
                username     = username,
                platform     = platform,
                value_score  = entry["value_score"],
                value_estimate = entry["value_estimate"],
                priority     = entry["priority"],
                claim_status = claim_status,
            )
        elif available is False:
            mark_checked(username, platform)

        # Polite delay between requests
        time.sleep(random.uniform(1.2, 2.8))

    print(f"✅  Done — {found} available username(s) found")

if __name__ == "__main__":
    priority = sys.argv[1].upper() if len(sys.argv) > 1 else None
    run(priority)
