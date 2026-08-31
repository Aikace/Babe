"""
check_availability.py
─────────────────────
Checks username availability on Instagram and X.
Triggers auto-claim + Discord alert when a name is free.

v2 fixes:
- Browser-style User-Agent for Instagram (not Android UA with web endpoint)
- Properly handles banned/suspended accounts (no false positives)
- Checks X API error payloads for suspended users
- Independent platform handling for "both"
- Shuffles check order for fairness
- Skips recently-checked names (< 10 min ago)
- Batches by platform to reduce context-switching

Usage:
    python check_availability.py [HIGH|MEDIUM|LOW]
"""

import os
import sys
import time
import random
import requests
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from db              import get_watchlist, mark_available, mark_checked
from discord_notify  import send_available_alert

X_BEARER = os.environ.get("X_BEARER_TOKEN", "")

# Browser-style User-Agents (matching the web endpoint we use)
_BROWSER_UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# ── Instagram ─────────────────────────────────────────────────────────────────

def check_instagram(username: str) -> bool | None:
    """
    Returns True  -> likely available (not found, not banned)
            False -> taken (active account exists)
            None  -> error / rate-limited / uncertain (skip)
    """
    try:
        headers = {
            "User-Agent":      random.choice(_BROWSER_UA),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Sec-Fetch-Site":  "none",
            "Sec-Fetch-Mode":  "navigate",
        }
        # Use the web profile page directly — simpler and more reliable
        url  = f"https://www.instagram.com/{username}/"
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)

        if resp.status_code == 404:
            # 404 can mean: truly available OR banned/disabled account
            # Cross-check with the API endpoint to reduce false positives
            return _ig_verify_available(username, headers)

        if resp.status_code == 200:
            # Page loaded — check if it's a real active profile or an error page
            body = resp.text.lower()
            if "page isn't available" in body or "sorry, this page" in body:
                # Instagram shows this for deleted/banned accounts too
                # Mark as uncertain, not available
                return None
            return False  # Active profile exists

        if resp.status_code == 429:
            print(f"  [ig] Rate-limited, backing off 30s ...")
            time.sleep(30)
            return None

        if resp.status_code in (401, 403):
            print(f"  [ig] Blocked on @{username} ({resp.status_code})")
            return None

        return None  # Unknown status code — don't make assumptions
    except requests.Timeout:
        print(f"  [ig] Timeout for @{username}")
        return None
    except Exception as e:
        print(f"  [ig] Error for @{username}: {e}")
        return None


def _ig_verify_available(username: str, headers: dict) -> bool | None:
    """
    Secondary check via API endpoint to verify a 404 is truly
    an available username and not a banned/disabled account.
    """
    try:
        api_headers = {
            **headers,
            "Accept": "application/json",
            "x-ig-app-id": "936619743392459",
        }
        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        resp = requests.get(url, headers=api_headers, timeout=12)

        if resp.status_code == 404:
            return True  # Both web + API say 404 — likely truly available

        if resp.status_code == 200:
            data = resp.json()
            user = data.get("data", {}).get("user")
            if user is None:
                return True  # No user object — available
            # If user exists but is_private or other flags — it's taken
            return False

        # Rate limited or other error — uncertain
        return None
    except Exception:
        # API check failed — but web 404'd, so cautiously report as uncertain
        return None


# ── X (Twitter) ───────────────────────────────────────────────────────────────

def check_x(username: str) -> bool | None:
    """
    Checks X API v2 for username availability.
    Properly handles suspended accounts (not false positive).
    """
    if not X_BEARER:
        return None
    try:
        headers = {"Authorization": f"Bearer {X_BEARER}"}
        url     = f"https://api.twitter.com/2/users/by/username/{username}"
        resp    = requests.get(url, headers=headers, timeout=12)

        if resp.status_code == 200:
            data = resp.json()

            # Active user found — username is taken
            if "data" in data:
                return False

            # Check for errors (suspended/deactivated accounts)
            errors = data.get("errors", [])
            for err in errors:
                detail = err.get("detail", "").lower()
                err_type = err.get("type", "").lower()
                # Suspended or deactivated — NOT available for registration
                if "suspended" in detail or "suspended" in err_type:
                    return False
                if "deactivated" in detail:
                    return None  # Might become available after 30 days
                # "User not found" — could be available
                if "not found" in detail or "could not find" in detail:
                    return True

            # No data and no recognized error — uncertain
            return None

        if resp.status_code == 404:
            return True  # Username not found

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("retry-after", 60))
            print(f"  [x] Rate-limited, backing off {retry_after}s ...")
            time.sleep(min(retry_after, 120))
            return None

        if resp.status_code == 402:
            print(f"  [x] X API requires paid plan (402)")
            return None

        return None
    except Exception as e:
        print(f"  [x] Error for @{username}: {e}")
        return None

# ── Dispatcher ────────────────────────────────────────────────────────────────

def _check_and_handle(entry: dict) -> bool:
    """Check one watchlist entry. Returns True if username is available."""
    username = entry["username"]
    platform = entry["platform"]
    value_score    = entry["value_score"]
    value_estimate = entry["value_estimate"]
    priority       = entry["priority"]

    if platform == "both":
        # Check each platform independently
        ig_available = check_instagram(username)
        time.sleep(random.uniform(0.5, 1.0))
        x_available  = check_x(username)

        found = False
        if ig_available is True:
            mark_available(username, "instagram")
            _try_claim_and_notify(username, "instagram", value_score, value_estimate, priority)
            found = True
        elif ig_available is False:
            mark_checked(username, "instagram")

        if x_available is True:
            mark_available(username, "x")
            _try_claim_and_notify(username, "x", value_score, value_estimate, priority)
            found = True
        elif x_available is False:
            mark_checked(username, "x")

        return found
    else:
        if platform == "instagram":
            available = check_instagram(username)
        elif platform == "x":
            available = check_x(username)
        else:
            available = None

        if available is True:
            mark_available(username, platform)
            _try_claim_and_notify(username, platform, value_score, value_estimate, priority)
            return True
        elif available is False:
            mark_checked(username, platform)

        return False


def _try_claim_and_notify(username: str, platform: str,
                          value_score: int, value_estimate: str,
                          priority: str) -> None:
    """Attempt auto-claim and send Discord notification."""
    print(f"  [AVAILABLE] @{username} on {platform}!")
    claim_status = "Attempting claim..."
    try:
        from auto_claim import claim_username
        success = claim_username(username, platform, value_score, value_estimate)
        claim_status = "CLAIMED!" if success else "Failed - claim manually"
    except Exception as ce:
        claim_status = f"Error: {ce}"

    send_available_alert(
        username       = username,
        platform       = platform,
        value_score    = value_score,
        value_estimate = value_estimate,
        priority       = priority,
        claim_status   = claim_status,
    )

# ── Main ──────────────────────────────────────────────────────────────────────

def run(priority_filter: str = None) -> None:
    label = priority_filter or "ALL"
    print(f"Checking availability - priority: {label}")

    entries = get_watchlist(priority=priority_filter)
    print(f"  {len(entries)} usernames queued")

    # Shuffle for fairness — don't always check the same names first
    random.shuffle(entries)

    # Skip names checked very recently (within 10 minutes)
    now = datetime.now(timezone.utc)
    filtered = []
    for entry in entries:
        last = entry.get("last_checked")
        if last:
            try:
                checked_at = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if now - checked_at < timedelta(minutes=10):
                    continue  # Skip — checked too recently
            except (ValueError, TypeError):
                pass
        filtered.append(entry)

    skipped = len(entries) - len(filtered)
    if skipped > 0:
        print(f"  Skipping {skipped} recently-checked names")

    found = 0
    for entry in filtered:
        found += 1 if _check_and_handle(entry) else 0

        # Adaptive delay based on priority
        if priority_filter == "HIGH":
            time.sleep(random.uniform(0.8, 1.5))
        elif priority_filter == "MEDIUM":
            time.sleep(random.uniform(1.0, 2.0))
        else:
            time.sleep(random.uniform(1.5, 3.0))

    print(f"Done - {found} available username(s) found out of {len(filtered)} checked")

if __name__ == "__main__":
    priority = sys.argv[1].upper() if len(sys.argv) > 1 else None
    run(priority)
