"""
auto_claim.py
─────────────
Attempts to claim an available username on Instagram or X.
Falls back to Discord notification if auto-claim is not possible.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from db             import add_to_claimed
from discord_notify import send_claimed_alert

IG_USERNAME    = os.environ.get("IG_USERNAME", "")
IG_PASSWORD    = os.environ.get("IG_PASSWORD", "")
X_USERNAME     = os.environ.get("X_USERNAME", "")
X_API_KEY      = os.environ.get("X_API_KEY", "")
X_API_SECRET   = os.environ.get("X_API_SECRET", "")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET= os.environ.get("X_ACCESS_SECRET", "")

# ── Instagram ─────────────────────────────────────────────────────────────────

def _claim_instagram(username: str) -> bool:
    if not IG_USERNAME or not IG_PASSWORD:
        print("  [ig-claim] Credentials not configured — skipping auto-claim")
        return False
    try:
        from instagrapi import Client
        cl = Client()
        cl.delay_range = [2, 5]                     # Human-like delays
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.account_change_username(username)
        print(f"  [ig-claim] ✅ Claimed @{username} on Instagram!")
        return True
    except ImportError:
        print("  [ig-claim] instagrapi not installed")
        return False
    except Exception as e:
        print(f"  [ig-claim] ❌ Failed: {e}")
        return False

# ── X (Twitter) ───────────────────────────────────────────────────────────────

def _claim_x(username: str) -> bool:
    """
    X's v2 API does not expose an account username-change endpoint.
    We notify the user to claim manually via the app/website.
    When you have Elevated access, the v1.1 account/settings endpoint
    supports username changes — add that here once available.
    """
    if not X_API_KEY:
        print("  [x-claim] Credentials not configured — skipping auto-claim")
        return False
    print(f"  [x-claim] ⚠️ X does not support auto-claim via API. Notify user.")
    return False

# ── Dispatcher ────────────────────────────────────────────────────────────────

def claim_username(username: str, platform: str,
                   value_score: int, value_estimate: str) -> bool:
    success = False

    if platform == "instagram":
        success = _claim_instagram(username)
        account_used = IG_USERNAME
    elif platform == "x":
        success = _claim_x(username)
        account_used = X_USERNAME
    elif platform == "both":
        ig_ok = _claim_instagram(username)
        x_ok  = _claim_x(username)
        success = ig_ok or x_ok
        account_used = IG_USERNAME if ig_ok else X_USERNAME
    else:
        account_used = ""

    if success:
        add_to_claimed(username, platform, value_score, value_estimate, account_used)
        send_claimed_alert(username, platform, value_score, value_estimate)

    return success

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        u, p = sys.argv[1], sys.argv[2]
        vs   = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        ve   = sys.argv[4]      if len(sys.argv) > 4 else "Unknown"
        claim_username(u, p, vs, ve)
