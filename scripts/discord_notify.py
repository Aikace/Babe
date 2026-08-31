import os
import time
import requests
from datetime import datetime, timezone

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK", "")
USER_ID     = os.environ.get("DISCORD_USER_ID", "")

# Brand colors
COLOR_GREEN  = 0x00FF88
COLOR_GOLD   = 0xFFD700
COLOR_ORANGE = 0xFF8C00
COLOR_RED    = 0xFF4444
COLOR_BLUE   = 0x5865F2

PRIORITY_COLORS = {"HIGH": COLOR_RED, "MEDIUM": COLOR_ORANGE, "LOW": COLOR_BLUE}

def _value_badge(score: int) -> str:
    if score >= 90: return "💎"
    if score >= 80: return "🔥"
    if score >= 65: return "⭐"
    if score >= 50: return "📌"
    return "🔹"

def _platform_badge(platform: str) -> str:
    mapping = {"instagram": "📸 Instagram", "x": "🐦 X (Twitter)", "both": "📱 IG + X"}
    return mapping.get(platform, platform.upper())

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def _post(payload: dict, max_retries: int = 3) -> None:
    if not WEBHOOK_URL:
        print("[discord] DISCORD_WEBHOOK not set, skipping notification")
        return
    for attempt in range(max_retries):
        try:
            resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 5)
                print(f"[discord] Rate limited, retrying in {retry_after}s (attempt {attempt+1})")
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            return
        except Exception as e:
            print(f"[discord] Failed to send (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)

# ─────────────────────────────────────────────
# AVAILABLE ALERT
# ─────────────────────────────────────────────
def send_available_alert(username: str, platform: str, value_score: int,
                         value_estimate: str, priority: str, claim_status: str) -> None:
    badge = _value_badge(value_score)
    color = PRIORITY_COLORS.get(priority, COLOR_BLUE)
    embed = {
        "title": f"🚨  @{username}  just dropped!",
        "description": f"> **Handle:** `@{username}`\n> **Platform:** {_platform_badge(platform)}",
        "color": color,
        "fields": [
            {"name": "💰 Est. Value",  "value": value_estimate,                  "inline": True},
            {"name": f"{badge} Score", "value": f"**{value_score}** / 100",      "inline": True},
            {"name": "⚡ Priority",    "value": priority,                         "inline": True},
            {"name": "🤖 Auto-Claim",  "value": claim_status,                    "inline": True},
            {"name": "🕒 Time",        "value": _now(),                          "inline": True},
        ],
        "footer": {"text": "Babe Sniper • username intelligence"},
        "thumbnail": {"url": "https://i.imgur.com/4M34hi2.png"},
    }
    _post({
        "content": f"<@{USER_ID}> 🎯 **Username available — move fast!**",
        "embeds": [embed],
    })

# ─────────────────────────────────────────────
# CLAIMED ALERT
# ─────────────────────────────────────────────
def send_claimed_alert(username: str, platform: str, value_score: int,
                       value_estimate: str) -> None:
    badge = _value_badge(value_score)
    embed = {
        "title": f"✅  @{username}  claimed!",
        "color": COLOR_GREEN,
        "fields": [
            {"name": "Platform",         "value": _platform_badge(platform),     "inline": True},
            {"name": f"{badge} Score",   "value": f"**{value_score}** / 100",   "inline": True},
            {"name": "💰 Est. Value",    "value": value_estimate,                "inline": True},
            {"name": "🕒 Claimed At",    "value": _now(),                        "inline": True},
        ],
        "footer": {"text": "Babe Sniper • added to your collection"},
    }
    _post({
        "content": f"<@{USER_ID}> 🎉 **@{username}** is yours!",
        "embeds": [embed],
    })

# ─────────────────────────────────────────────
# DAILY REPORT (enhanced)
# ─────────────────────────────────────────────
def send_daily_report(stats: dict, pool: dict = None, rotation: dict = None) -> None:
    top = stats.get("top_names", [])
    top_str = "\n".join(
        [f"`@{n['username']}` — {_value_badge(n['value_score'])} **{n['value_score']}/100**" for n in top]
    ) or "_No names yet_"

    fields = [
        {"name": "👀 Monitoring",    "value": str(stats["total_monitored"]), "inline": True},
        {"name": "🟢 Available",     "value": str(stats["total_available"]), "inline": True},
        {"name": "✅ Claimed",       "value": str(stats["total_claimed"]),   "inline": True},
        {"name": "🌟 Top Watchlist", "value": top_str,                       "inline": False},
    ]

    # Pool health
    if pool:
        ig_str = f"{pool.get('ig_free', 0)}/{pool.get('ig_total', 0)} free"
        x_str  = f"{pool.get('x_free', 0)}/{pool.get('x_total', 0)} free"
        pool_status = f"📸 IG: **{ig_str}** | 🐦 X: **{x_str}**"
        fields.append({"name": "🔑 Account Pool", "value": pool_status, "inline": False})

    # Priority rotation
    if rotation and rotation.get("demoted", 0) > 0:
        fields.append({
            "name": "🔄 Auto-Rotation",
            "value": f"Demoted **{rotation['demoted']}** stale names to LOW priority",
            "inline": False,
        })

    embed = {
        "title": "📊  Daily Sniper Report",
        "color": COLOR_GOLD,
        "fields": fields,
        "footer": {"text": f"Babe Sniper • {_now()}"},
    }
    _post({"embeds": [embed]})

# ─────────────────────────────────────────────
# POOL WARNING
# ─────────────────────────────────────────────
def send_pool_warning(platform: str) -> None:
    embed = {
        "title": f"⚠️  Account Pool Empty — {platform.upper()}",
        "description": (
            f"All `{platform}` throwaway accounts are either **holding a username** or **banned**.\n"
            "Add more accounts to keep auto-claiming."
        ),
        "color": COLOR_ORANGE,
        "footer": {"text": "Babe Sniper • account pool manager"},
    }
    _post({
        "content": f"<@{USER_ID}> ⚠️ **Pool is full — add more accounts!**",
        "embeds": [embed],
    })

# ─────────────────────────────────────────────
# RATE LIMIT WARNING
# ─────────────────────────────────────────────
def send_rate_limit_warning(platform: str, duration_sec: int = 60) -> None:
    embed = {
        "title": f"🛑  Rate Limited — {platform.upper()}",
        "description": f"Bot is backing off for **{duration_sec}s** to avoid ban.",
        "color": COLOR_RED,
        "footer": {"text": "Babe Sniper • rate limiter"},
    }
    _post({"embeds": [embed]})

# ─────────────────────────────────────────────
# TEST PING
# ─────────────────────────────────────────────
def send_test_ping() -> None:
    _post({
        "content": f"<@{USER_ID}> ✅ **Babe Sniper is live and watching usernames!**",
        "embeds": [{
            "title": "🚀 Bot Online",
            "description": "Username monitoring has started. You'll be pinged here whenever a name drops.",
            "color": COLOR_GREEN,
            "footer": {"text": "Babe Sniper • ready"},
        }],
    })
