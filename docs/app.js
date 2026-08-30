// ── Config ───────────────────────────────────────────────────────────────────
const SUPABASE_URL = "https://vogztajdwxkzcfrgaica.supabase.co";
const SUPABASE_ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvZ3p0YWpkd3hremNmcmdhaWNhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU0MTUzODIsImV4cCI6MjEwMDk5MTM4Mn0.nhT6bv8Za1LJW7iz_vsJDIMJ_av8dSF_vnatrZRpyl8";

const HEADERS = {
  "apikey":        SUPABASE_ANON,
  "Authorization": `Bearer ${SUPABASE_ANON}`,
};

// ── State ────────────────────────────────────────────────────────────────────
let allWatchlist = [];
let allAvailable = [];
let allClaimed   = [];
let allPool      = [];
let activeTab    = "watchlist";

// ── Fetch helpers ─────────────────────────────────────────────────────────────
async function fetchTable(table, params = "") {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}?${params}`, { headers: HEADERS });
  if (!res.ok) throw new Error(`${table}: ${res.status}`);
  return res.json();
}

async function loadData() {
  try {
    const [watchlist, available, claimed, pool] = await Promise.all([
      fetchTable("watchlist", "status=eq.monitoring&order=value_score.desc&limit=500"),
      fetchTable("watchlist", "status=eq.available&order=value_score.desc"),
      fetchTable("claimed",   "order=claimed_at.desc&limit=200"),
      fetchTable("accounts",  "order=platform.asc,status.asc"),
    ]);

    allWatchlist = watchlist;
    allAvailable = available;
    allClaimed   = claimed;
    allPool      = pool;

    updateStats(watchlist, available, claimed);
    renderCurrentTab();
    document.getElementById("lastRefresh").textContent =
      "Updated " + new Date().toLocaleTimeString();
  } catch (e) {
    console.error("Load error:", e);
  }
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function estimateMin(est) {
  // Extract the lower bound dollar number from strings like "$200 – $1,000"
  const m = est.match(/\$[\d,]+/);
  return m ? parseInt(m[0].replace(/[\$,]/g, "")) : 0;
}

function updateStats(watchlist, available, claimed) {
  document.getElementById("statMonitoring").textContent = watchlist.length.toLocaleString();
  document.getElementById("statAvailable").textContent  = available.length.toLocaleString();
  document.getElementById("statClaimed").textContent    = claimed.length.toLocaleString();

  const portfolio = claimed.reduce((sum, r) => sum + estimateMin(r.value_estimate || ""), 0);
  document.getElementById("statPortfolio").textContent =
    portfolio > 0 ? `$${portfolio.toLocaleString()}+` : "—";
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function valueBadge(score) {
  if (score >= 90) return "💎";
  if (score >= 75) return "🔥";
  if (score >= 60) return "⭐";
  return "📌";
}

function platformBadge(p) {
  if (p === "instagram") return `<span class="badge badge-ig">📸 IG</span>`;
  if (p === "x")         return `<span class="badge badge-x">🐦 X</span>`;
  return `<span class="badge">${p}</span>`;
}

function priorityBadge(p) {
  const cls = { HIGH: "badge-high", MEDIUM: "badge-medium", LOW: "badge-low" }[p] || "";
  return `<span class="badge ${cls}">${p}</span>`;
}

function scoreBar(score) {
  return `
    <div class="score-wrap">
      <div class="score-bar-bg">
        <div class="score-bar-fill" style="width:${score}%"></div>
      </div>
      <span class="score-num">${valueBadge(score)} ${score}</span>
    </div>`;
}

function relativeTime(ts) {
  if (!ts) return "—";
  const diff = Date.now() - new Date(ts).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)   return "just now";
  if (m < 60)  return `${m}m ago`;
  if (m < 1440) return `${Math.floor(m/60)}h ago`;
  return `${Math.floor(m/1440)}d ago`;
}

function platformLink(username, platform) {
  const url = platform === "instagram"
    ? `https://instagram.com/${username}`
    : `https://x.com/${username}`;
  return `<div class="handle"><a href="${url}" target="_blank">@${username}</a></div>`;
}

// ── Filter ────────────────────────────────────────────────────────────────────
function getFilters() {
  return {
    search:   document.getElementById("searchInput").value.toLowerCase(),
    platform: document.getElementById("platformFilter").value,
    priority: document.getElementById("priorityFilter").value,
  };
}

function applyFilters(rows) {
  const { search, platform, priority } = getFilters();
  return rows.filter(r => {
    if (search   && !r.username.toLowerCase().includes(search)) return false;
    if (platform && r.platform !== platform) return false;
    if (priority && r.priority !== priority) return false;
    return true;
  });
}

// ── Tab renderers ─────────────────────────────────────────────────────────────
function renderWatchlist() {
  const rows = applyFilters(allWatchlist);
  document.getElementById("watchlistBody").innerHTML = rows.length
    ? rows.map(r => `
        <tr>
          <td>${platformLink(r.username, r.platform)}</td>
          <td>${platformBadge(r.platform)}</td>
          <td>${scoreBar(r.value_score || 0)}</td>
          <td class="value-est">${r.value_estimate || "—"}</td>
          <td>${priorityBadge(r.priority)}</td>
          <td class="ts">${relativeTime(r.last_checked)}</td>
        </tr>`).join("")
    : `<tr><td colspan="6" class="loading">No results</td></tr>`;
}

function renderAvailable() {
  const rows = applyFilters(allAvailable);
  document.getElementById("availableBody").innerHTML = rows.length
    ? rows.map(r => `
        <tr>
          <td>${platformLink(r.username, r.platform)}</td>
          <td>${platformBadge(r.platform)}</td>
          <td>${scoreBar(r.value_score || 0)}</td>
          <td class="value-est">${r.value_estimate || "—"}</td>
          <td>${priorityBadge(r.priority)}</td>
          <td class="ts">${relativeTime(r.last_checked)}</td>
        </tr>`).join("")
    : `<tr><td colspan="6" class="loading">No usernames available right now — watching 👀</td></tr>`;
}

function renderClaimed() {
  const rows = applyFilters(allClaimed);
  document.getElementById("claimedBody").innerHTML = rows.length
    ? rows.map(r => `
        <tr>
          <td>${platformLink(r.username, r.platform)}</td>
          <td>${platformBadge(r.platform)}</td>
          <td>${scoreBar(r.value_score || 0)}</td>
          <td class="value-est">${r.value_estimate || "—"}</td>
          <td class="ts">${r.account_used || "—"}</td>
          <td class="ts">${relativeTime(r.claimed_at)}</td>
        </tr>`).join("")
    : `<tr><td colspan="6" class="loading">Nothing claimed yet — the sniper is warming up 🎯</td></tr>`;
}

function renderPool() {
  const statusIcon = { available: "🟢", holding: "🟡", banned: "🔴" };
  document.getElementById("poolBody").innerHTML = allPool.length
    ? allPool.map(r => `
        <tr>
          <td class="handle">@${r.username}</td>
          <td>${platformBadge(r.platform)}</td>
          <td>${statusIcon[r.status] || "❓"} <strong>${r.status}</strong></td>
          <td class="value-est">${r.holding_username ? `@${r.holding_username}` : "—"}</td>
        </tr>`).join("")
    : `<tr><td colspan="4" class="loading">No accounts in pool yet</td></tr>`;
}

function renderCurrentTab() {
  if      (activeTab === "watchlist") renderWatchlist();
  else if (activeTab === "available") renderAvailable();
  else if (activeTab === "claimed")   renderClaimed();
  else if (activeTab === "pool")      renderPool();
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    activeTab = btn.dataset.tab;
    document.getElementById(`tab-${activeTab}`).classList.add("active");
    renderCurrentTab();
  });
});

// ── Filters ───────────────────────────────────────────────────────────────────
["searchInput", "platformFilter", "priorityFilter"].forEach(id => {
  document.getElementById(id).addEventListener("input", renderCurrentTab);
});

// ── Auto-refresh every 60 seconds ────────────────────────────────────────────
loadData();
setInterval(loadData, 60_000);
