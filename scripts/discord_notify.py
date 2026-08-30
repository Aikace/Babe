import os
import requests
from datetime import datetime, timezone

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]
USER_ID     = os.environ["DISCORD_USER_ID"]

# Brand colors
COLOR_GREEN  = 0x00FF88
COLOR_GOLD   = 0xFFD700
COLOR_ORANGE = 0xFF8C00
COLOR_RED    = 0xFF4444
COLOR_BLUE   = 0x5865F2

PRIORITY_COLORS = {"HIGH": COLOR_RED, "MEDIUM": COLOR_ORANGE, "LOW": COLOR_BLUE}

def _value_badge(score: int) -> str:
    if score >= 90: return "💎"
    if score >= 75: return "🔥"
    if score >= 60: return "⭐"
    if score >= 40: return "📌"
    return "🔹"

def _platform_badge(platform: str) -> str:
    mapping = {"instagram": "📸 Instagram", "x": "🐦 X (Twitter)", "both": "📱 IG + X"}
    return mapping.get(platform, platform.upper())

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def _post(payload: dict) -> None:
    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[discord] Failed to send: {e}")

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
# DAILY REPORT
# ─────────────────────────────────────────────
def send_daily_report(stats: dict) -> None:
    top = stats.get("top_names", [])
    top_str = "\n".join(
        [f"`@{n['username']}` — {_value_badge(n['value_score'])} **{n['value_score']}/100**" for n in top]
    ) or "_No names yet_"

    embed = {
        "title": "📊  Daily Sniper Report",
        "color": COLOR_GOLD,
        "fields": [
            {"name": "👀 Monitoring",    "value": str(stats["total_monitored"]), "inline": True},
            {"name": "🟢 Available",     "value": str(stats["total_available"]), "inline": True},
            {"name": "✅ Claimed",       "value": str(stats["total_claimed"]),   "inline": True},
            {"name": "🌟 Top Watchlist", "value": top_str,                       "inline": False},
        ],
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
