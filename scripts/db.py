import os
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

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
        "last_checked": "now()"
    }).eq("username", username).eq("platform", platform).execute()

def mark_checked(username: str, platform: str) -> None:
    client = get_client()
    client.table("watchlist").update({
        "status": "monitoring",
        "last_checked": "now()"
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

def get_stats() -> dict:
    client = get_client()
    total_monitored = len(client.table("watchlist").select("id").eq("status", "monitoring").execute().data)
    total_available = len(client.table("watchlist").select("id").eq("status", "available").execute().data)
    total_claimed   = len(client.table("claimed").select("id").execute().data)
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
