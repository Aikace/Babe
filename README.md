# 🎯 Babe Sniper

> Fully automated username sniping system for **Instagram** and **X (Twitter)**.
> Monitors 24/7, scores by value, alerts on Discord, auto-claims when possible.

---

## Live Dashboard

👉 **[Open Dashboard](https://aikace.github.io/Babe/dashboard/)**

---

## How It Works

```
GitHub Actions (cron, free)
    │
    ├─► Daily: generate + score new usernames → Supabase
    ├─► Every 5 min:  check HIGH priority names
    ├─► Every 15 min: check MEDIUM priority names
    ├─► Every hour:   check LOW priority names
    └─► Daily 8AM:    Discord summary report
              │
              ▼
    Username Available?
        ├── Yes → Auto-claim attempt + Discord ping with value estimate
        └── No  → Mark checked, continue
```

---

## Value Scoring

| Score | Badge | Est. Value |
|-------|-------|-----------|
| 90–100 | 💎 | \$1,000–\$10,000+ |
| 75–89  | 🔥 | \$200–\$1,000 |
| 60–74  | ⭐ | \$50–\$200 |
| 40–59  | 📌 | \$10–\$50 |

---

## Stack

| Layer | Tool |
|-------|------|
| Runner | GitHub Actions (free) |
| Database | Supabase (free tier) |
| Alerts | Discord Webhooks |
| Dashboard | GitHub Pages |
| IG automation | instagrapi |
| X API | tweepy / X API v2 |

---

## Setup (first time)

1. **Supabase tables** — run `setup.sql` in your Supabase SQL editor
2. **GitHub Secrets** — run `python setup_secrets.py` once
3. **Enable GitHub Pages** — Settings → Pages → Source: `main` branch, `/dashboard` folder
4. **Trigger first generation** — Actions → "Generate Usernames" → Run workflow

---

## Files

```
.github/workflows/   GitHub Actions cron jobs
scripts/             Core bot logic
data/                Wordlist + blocklist
dashboard/           Web dashboard (GitHub Pages)
setup.sql            One-time Supabase table creation
setup_secrets.py     One-time GitHub secrets upload
```
