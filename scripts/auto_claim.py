"""
auto_claim.py
─────────────
Attempts to claim an available username on Instagram or X.
Uses the Supabase account pool — rotates through all available
throwaway accounts automatically. No hardcoded credentials.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from db import (
    add_to_claimed,
    get_available_account,
    mark_account_holding,
    mark_account_banned,
)
from discord_notify import send_claimed_alert, send_pool_warning

X_API_KEY       = os.environ.get("X_API_KEY", "")
X_API_SECRET    = os.environ.get("X_API_SECRET", "")
X_ACCESS_TOKEN  = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "")

# ── Instagram ─────────────────────────────────────────────────────────────────

def _claim_instagram(target_username: str) -> tuple[bool, str]:
    """
    Finds an available Instagram account from the pool and
    changes its username to target_username.
    Returns (success, account_used).
    """
    account = get_available_account("instagram")
    if not account:
        print("  [ig-claim] No available Instagram accounts in pool!")
        send_pool_warning("instagram")
        return False, ""

    login_user = account["username"]
    login_pass = account["password"]
    acct_id    = account["id"]

    try:
        from instagrapi import Client
        cl = Client()
        cl.delay_range = [2, 5]
        print(f"  [ig-claim] Logging in as @{login_user} ...")
        cl.login(login_user, login_pass)
        cl.account_change_username(target_username)
        print(f"  [ig-claim] SUCCESS: @{login_user} is now @{target_username}")
        mark_account_holding(acct_id, target_username)
        return True, login_user
    except ImportError:
        print("  [ig-claim] instagrapi not installed")
        return False, ""
    except Exception as e:
        err = str(e).lower()
        if "banned" in err or "challenge" in err or "disabled" in err:
            print(f"  [ig-claim] Account @{login_user} appears banned/challenged")
            mark_account_banned(acct_id)
            # Retry with next available account recursively
            return _claim_instagram(target_username)
        print(f"  [ig-claim] Failed for @{login_user}: {e}")
        return False, ""

# ── X (Twitter) ───────────────────────────────────────────────────────────────

def _claim_x(target_username: str) -> tuple[bool, str]:
    """
    X v2 API does not expose username-change endpoint.
    Notifies user to claim manually.
    Returns (success, account_used).
    """
    if not X_API_KEY:
        print("  [x-claim] X credentials not configured")
        return False, ""
    print(f"  [x-claim] X API does not support auto username change. Notify user.")
    return False, ""

# ── Dispatcher ────────────────────────────────────────────────────────────────

def claim_username(username: str, platform: str,
                   value_score: int, value_estimate: str) -> bool:
    success      = False
    account_used = ""

    if platform == "instagram":
        success, account_used = _claim_instagram(username)
    elif platform == "x":
        success, account_used = _claim_x(username)
    elif platform == "both":
        ig_ok, ig_acct = _claim_instagram(username)
        x_ok,  x_acct  = _claim_x(username)
        success      = ig_ok or x_ok
        account_used = ig_acct or x_acct

    if success:
        add_to_claimed(username, platform, value_score, value_estimate, account_used)
        send_claimed_alert(username, platform, value_score, value_estimate)

    return success

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        u  = sys.argv[1]
        p  = sys.argv[2]
        vs = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        ve = sys.argv[4]      if len(sys.argv) > 4 else "Unknown"
        claim_username(u, p, vs, ve)
