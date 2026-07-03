// Shared helpers: auth, API calls, layout, formatting.

const API = window.PULTRACK_API;
const TOKEN_KEY = "pt_token";

function getToken() { return localStorage.getItem(TOKEN_KEY); }
function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
function logout() { localStorage.removeItem(TOKEN_KEY); location.href = "index.html"; }

// Redirect to login if not authenticated. Call at the top of protected pages.
function requireAuth() {
  if (!getToken()) { location.href = "index.html"; return false; }
  return true;
}

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;
  let res;
  try {
    res = await fetch(API + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    toast("Serverga ulanib bo'lmadi");
    return null;
  }
  if (res.status === 401) { logout(); return null; }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    toast(err.detail || "Xatolik yuz berdi");
    return null;
  }
  return res.status === 204 ? true : await res.json();
}

const apiGet = (p) => api("GET", p);
const apiPost = (p, b) => api("POST", p, b);
const apiPatch = (p, b) => api("PATCH", p, b);
const apiDelete = (p) => api("DELETE", p);

function fmtMoney(v) {
  return new Intl.NumberFormat("ru-RU").format(Math.round(v || 0)) + " so'm";
}

function toast(msg) {
  let el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(window.__t);
  window.__t = setTimeout(() => el.classList.remove("show"), 2400);
}

// Inject the sidebar into #sidebar-slot and mark the active page.
async function renderNav(active) {
  const items = [
    ["overview", "overview.html", "Umumiy", "▦"],
    ["transactions", "transactions.html", "Tranzaksiyalar", "≡"],
    ["analytics", "analytics.html", "Analitika", "◔"],
    ["categories", "categories.html", "Kategoriyalar", "⬡"],
  ];
  const links = items.map(([key, href, label, icon]) => `
    <a href="${href}" class="flex items-center gap-3 px-3 py-2 rounded-lg transition
       ${active === key ? "bg-emerald-50 text-emerald-700" : "text-slate-600 hover:bg-slate-50"}">
      <span class="w-5 text-center">${icon}</span>${label}
    </a>`).join("");

  const slot = document.getElementById("sidebar-slot");
  if (slot) {
    slot.outerHTML = `
      <aside class="w-60 shrink-0 border-r border-slate-200 bg-white flex flex-col">
        <div class="px-6 py-5 border-b border-slate-100">
          <div class="text-xl font-bold text-slate-900">Pul<span class="text-emerald-600">Track</span></div>
          <div class="text-xs text-slate-400 mt-0.5">Biznes moliya</div>
        </div>
        <nav class="p-3 space-y-1 text-sm font-medium">${links}</nav>
        <div class="mt-auto p-4 border-t border-slate-100">
          <div id="nav-user" class="text-sm text-slate-600 mb-2 truncate"></div>
          <button onclick="logout()" class="text-xs text-slate-400 hover:text-rose-600">Chiqish →</button>
        </div>
      </aside>`;
  }

  const me = await apiGet("/api/auth/me");
  if (me) {
    const u = document.getElementById("nav-user");
    if (u) u.textContent = "👤 " + (me.name || "Foydalanuvchi");
  }
}
