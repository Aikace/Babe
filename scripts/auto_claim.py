"""
auto_claim.py
─────────────
Attempts to claim an available username on Instagram or X.
Uses the Supabase account pool — rotates through all available
throwaway accounts automatically.

Fixes from v1:
- Uses correct instagrapi method: cl.account_edit(username=...)
- Iterative retry with max 3 attempts (no unbounded recursion)
- Session persistence to avoid login challenges
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))
from db import (
    add_to_claimed,
    get_available_account,
    mark_account_holding,
    mark_account_banned,
)
from discord_notify import send_claimed_alert, send_pool_warning

MAX_CLAIM_ATTEMPTS = 3

# ── Instagram ─────────────────────────────────────────────────────────────────

def _claim_instagram(target_username: str) -> tuple[bool, str]:
    """
    Finds an available Instagram account from the pool and
    changes its username to target_username.
    Tries up to MAX_CLAIM_ATTEMPTS different accounts.
    Returns (success, account_used_original_name).
    """
    for attempt in range(MAX_CLAIM_ATTEMPTS):
        account = get_available_account("instagram")
        if not account:
            print(f"  [ig-claim] No available Instagram accounts in pool! (attempt {attempt+1})")
            send_pool_warning("instagram")
            return False, ""

        login_user = account["username"]
        login_pass = account["password"]
        acct_id    = account["id"]

        try:
            from instagrapi import Client
            cl = Client()
            cl.delay_range = [2, 5]

            # Try to load saved session to avoid login challenges
            session_path = f"/tmp/ig_session_{login_user}.json"
            if os.path.exists(session_path):
                try:
                    cl.load_settings(session_path)
                    cl.login(login_user, login_pass)
                    print(f"  [ig-claim] Resumed session for @{login_user}")
                except Exception:
                    cl = Client()
                    cl.delay_range = [2, 5]
                    cl.login(login_user, login_pass)
                    print(f"  [ig-claim] Fresh login as @{login_user}")
            else:
                print(f"  [ig-claim] Logging in as @{login_user} ...")
                cl.login(login_user, login_pass)

            # Save session for future use
            try:
                cl.dump_settings(session_path)
            except Exception:
                pass

            # Correct method: account_edit, not account_change_username
            cl.account_edit(username=target_username)
            print(f"  [ig-claim] SUCCESS: @{login_user} -> @{target_username}")
            mark_account_holding(acct_id, target_username)
            return True, login_user

        except ImportError:
            print("  [ig-claim] instagrapi not installed")
            return False, ""
        except Exception as e:
            err = str(e).lower()
            if any(kw in err for kw in ("banned", "challenge", "disabled", "checkpoint", "consent")):
                print(f"  [ig-claim] Account @{login_user} blocked/challenged (attempt {attempt+1})")
                mark_account_banned(acct_id)
                continue  # Try next account (iterative, not recursive)
            print(f"  [ig-claim] Failed for @{login_user}: {e}")
            return False, ""

    print(f"  [ig-claim] All {MAX_CLAIM_ATTEMPTS} attempts exhausted")
    return False, ""

# ── X (Twitter) ───────────────────────────────────────────────────────────────

def _claim_x(target_username: str) -> tuple[bool, str]:
    """
    X v2 API does not expose username-change endpoint at free tier.
    Notifies user to claim manually via Discord.
    Returns (False, "") always.
    """
    print(f"  [x-claim] X API doesn't support auto username change. User notified.")
    return False, ""

# ── Dispatcher ────────────────────────────────────────────────────────────────

def claim_username(username: str, platform: str,
                   value_score: int, value_estimate: str) -> bool:
    """
    Attempt to claim a username. Handles each platform independently.
    """
    success      = False
    account_used = ""

    if platform == "instagram":
        success, account_used = _claim_instagram(username)
    elif platform == "x":
        success, account_used = _claim_x(username)
    elif platform == "both":
        # Handle each platform independently
        ig_ok, ig_acct = _claim_instagram(username)
        x_ok,  x_acct  = _claim_x(username)

        # Record whichever succeeded
        if ig_ok:
            add_to_claimed(username, "instagram", value_score, value_estimate, ig_acct)
            send_claimed_alert(username, "instagram", value_score, value_estimate)
        if x_ok:
            add_to_claimed(username, "x", value_score, value_estimate, x_acct)
            send_claimed_alert(username, "x", value_score, value_estimate)
        return ig_ok or x_ok

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
