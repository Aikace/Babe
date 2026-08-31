"""
db.py
─────
Supabase database abstraction layer.
Manages watchlist, claimed, and accounts tables.
"""

import os
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

_client: Client | None = None

def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

def _now() -> str:
    """Return current UTC timestamp as ISO-8601 string for PostgREST."""
    return datetime.now(timezone.utc).isoformat()

# ── Watchlist ─────────────────────────────────────────────────────────────────

def get_watchlist(priority: str = None, status: str = "monitoring") -> list:
    client = get_client()
    query = client.table("watchlist").select("*").eq("status", status)
    if priority:
        query = query.eq("priority", priority)
    return query.execute().data

def add_to_watchlist(username: str, platform: str, priority: str,
                     value_score: int, value_estimate: str) -> bool:
    client = get_client()
    try:
        client.table("watchlist").upsert({
            "username": username,
            "platform": platform,
            "priority": priority,
            "value_score": value_score,
            "value_estimate": value_estimate,
            "status": "monitoring"
        }, on_conflict="username,platform").execute()
        return True
    except Exception as e:
        print(f"  [db] Error adding {username}@{platform}: {e}")
        return False

def mark_available(username: str, platform: str) -> None:
    client = get_client()
    client.table("watchlist").update({
        "status": "available",
        "last_checked": _now()
    }).eq("username", username).eq("platform", platform).execute()

def mark_checked(username: str, platform: str) -> None:
    client = get_client()
    client.table("watchlist").update({
        "last_checked": _now()
    }).eq("username", username).eq("platform", platform).execute()

def mark_claimed(username: str, platform: str) -> None:
    client = get_client()
    client.table("watchlist").update({
        "status": "claimed"
    }).eq("username", username).eq("platform", platform).execute()

def add_to_claimed(username: str, platform: str, value_score: int,
                   value_estimate: str, account_used: str) -> None:
    client = get_client()
    client.table("claimed").insert({
        "username": username,
        "platform": platform,
        "value_score": value_score,
        "value_estimate": value_estimate,
        "account_used": account_used
    }).execute()
    mark_claimed(username, platform)

# ── Account Pool ──────────────────────────────────────────────────────────────

def get_available_account(platform: str) -> dict | None:
    """Return the first available account for a platform, or None."""
    client = get_client()
    result = (client.table("accounts")
              .select("*")
              .eq("platform", platform)
              .eq("status", "available")
              .limit(1)
              .execute())
    return result.data[0] if result.data else None

def mark_account_holding(account_id: str, claimed_username: str) -> None:
    client = get_client()
    client.table("accounts").update({
        "status": "holding",
        "holding_username": claimed_username
    }).eq("id", account_id).execute()

def mark_account_available(account_id: str) -> None:
    client = get_client()
    client.table("accounts").update({
        "status": "available",
        "holding_username": None
    }).eq("id", account_id).execute()

def mark_account_banned(account_id: str) -> None:
    client = get_client()
    client.table("accounts").update({
        "status": "banned"
    }).eq("id", account_id).execute()

def add_account(platform: str, username: str, password: str) -> bool:
    client = get_client()
    try:
        client.table("accounts").upsert({
            "platform": platform,
            "username": username,
            "password": password,
            "status":   "available"
        }, on_conflict="username,platform").execute()
        return True
    except Exception as e:
        print(f"  [db] Error adding account {username}: {e}")
        return False

def get_account_pool_status() -> list:
    client = get_client()
    return client.table("accounts").select("*").order("platform").execute().data

# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    client = get_client()
    # Use proper counting to avoid Supabase 1000-row pagination cap
    try:
        mon_result = client.table("watchlist").select("id", count="exact").eq("status", "monitoring").execute()
        total_monitored = mon_result.count or 0
    except Exception:
        total_monitored = len(client.table("watchlist").select("id").eq("status", "monitoring").execute().data)

    try:
        avail_result = client.table("watchlist").select("id", count="exact").eq("status", "available").execute()
        total_available = avail_result.count or 0
    except Exception:
        total_available = len(client.table("watchlist").select("id").eq("status", "available").execute().data)

    try:
        claim_result = client.table("claimed").select("id", count="exact").execute()
        total_claimed = claim_result.count or 0
    except Exception:
        total_claimed = len(client.table("claimed").select("id").execute().data)

    top_names = (client.table("watchlist")
                 .select("username,value_score")
                 .eq("status", "monitoring")
                 .order("value_score", desc=True)
                 .limit(5)
                 .execute().data)
    return {
        "total_monitored": total_monitored,
        "total_available": total_available,
        "total_claimed":   total_claimed,
        "top_names":       top_names,
    }

# ── Auto Priority Rotation ───────────────────────────────────────────────────

def auto_rotate_priorities() -> dict:
    """
    Demote names monitored 30+ days without becoming available -> LOW priority.
    This saves checking budget on stale names.
    Returns {"demoted": count}.
    """
    client = get_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    # Find HIGH/MEDIUM names created before cutoff that are still monitoring
    stale_high = (client.table("watchlist")
                  .select("id,username,priority")
                  .eq("status", "monitoring")
                  .in_("priority", ["HIGH", "MEDIUM"])
                  .lt("created_at", cutoff)
                  .execute().data)

    demoted = 0
    for entry in stale_high:
        # Only demote if never been available (still monitoring after 30 days)
        client.table("watchlist").update({
            "priority": "LOW"
        }).eq("id", entry["id"]).execute()
        demoted += 1

    if demoted:
        print(f"  [rotate] Demoted {demoted} stale names to LOW priority")
    return {"demoted": demoted}

# ── Pool Summary ──────────────────────────────────────────────────────────────

def get_pool_summary() -> dict:
    """Get account pool summary for Discord digest."""
    client = get_client()
    try:
        accounts = client.table("accounts").select("platform,status").execute().data
    except Exception:
        return {"ig_total": 0, "ig_free": 0, "x_total": 0, "x_free": 0}

    ig_total = sum(1 for a in accounts if a["platform"] == "instagram")
    ig_free  = sum(1 for a in accounts if a["platform"] == "instagram" and a["status"] == "available")
    x_total  = sum(1 for a in accounts if a["platform"] == "x")
    x_free   = sum(1 for a in accounts if a["platform"] == "x" and a["status"] == "available")
    return {"ig_total": ig_total, "ig_free": ig_free, "x_total": x_total, "x_free": x_free}

