/* SkyCache Nexus 0.4 - community broadband experience PWA */
(function () {
  const LANGS = ["en", "fr", "es", "ar", "sw", "hi", "pt"];
  const READER_BM_KEY = "skycache_reader_bookmarks";
  const READER_FS_KEY = "skycache_reader_fs";
  const READER_FS_MIN = 1.0;
  const READER_FS_MAX = 2.0;
  const READER_FS_STEP = 0.125;

  const state = {
    lang: localStorage.getItem("skycache_lang") || "en",
    i18n: {},
    packages: [],
    status: null,
    nexus: null,
    category: null,
    tts: localStorage.getItem("skycache_tts") === "1",
    board: "general",
    onboard: null,
    onboardStep: 0,
    voter: localStorage.getItem("skycache_voter") || ("v-" + Math.random().toString(36).slice(2, 10)),
    /** @type {object[]} last Library result set for prev/next */
    libResults: [],
    reader: {
      workId: null,
      packageId: null,
      path: null,
      index: -1,
      fontSize: parseFloat(localStorage.getItem(READER_FS_KEY) || "1.25") || 1.25,
      chapters: [],
      chapterIndex: 0,
      paginate: localStorage.getItem("skycache_reader_paginate") === "1",
      pageIndex: 0,
      pageCount: 1,
    },
  };
  localStorage.setItem("skycache_voter", state.voter);

  const $ = (id) => document.getElementById(id);

  const CAT_META = {
    emergency: { emoji: "🚨" },
    health: { emoji: "💚" },
    education: { emoji: "📚" },
    agriculture: { emoji: "🌾" },
    weather: { emoji: "🌤️" },
    maps: { emoji: "🗺️" },
    general: { emoji: "📦" },
  };

  function t(key, fallback) {
    return (state.i18n && state.i18n[key]) || fallback || key;
  }

  function titleOf(pkg) {
    return (pkg.title && (pkg.title[state.lang] || pkg.title.en)) || pkg.id;
  }

  function summaryOf(pkg) {
    return (pkg.summary && (pkg.summary[state.lang] || pkg.summary.en)) || "";
  }

  function ageLabel(hours) {
    if (hours < 1) return t("age_just_now", "Just now");
    if (hours < 24) return t("age_hours", "{n}h ago").replace("{n}", Math.round(hours));
    return t("age_days", "{n}d ago").replace("{n}", Math.round(hours / 24));
  }

  function speak(text) {
    if (!state.tts || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = state.lang === "ar" ? "ar" : state.lang === "hi" ? "hi-IN" : state.lang;
    window.speechSynthesis.speak(u);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function loadI18n() {
    try {
      const res = await fetch(`/static/i18n/${state.lang}.json`);
      state.i18n = res.ok ? await res.json() : {};
    } catch {
      state.i18n = {};
    }
  }

  async function loadData() {
    const [st, pkgs, nexus] = await Promise.all([
      fetch("/api/status").then((r) => r.json()),
      fetch("/api/packages").then((r) => r.json()),
      fetch("/api/nexus/status").then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]);
    state.status = st;
    state.packages = pkgs;
    state.nexus = nexus;
  }

  function renderLang() {
    const row = $("langRow");
    if (!row) return;
    row.innerHTML = "";
    LANGS.forEach((code) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = code.toUpperCase();
      b.className = code === state.lang ? "active" : "";
      b.addEventListener("click", async () => {
        state.lang = code;
        localStorage.setItem("skycache_lang", code);
        document.documentElement.lang = code;
        document.documentElement.dir = code === "ar" ? "rtl" : "ltr";
        await loadI18n();
        renderAll();
      });
      row.appendChild(b);
    });
  }

  function renderHeader() {
    $("legalBanner").textContent = t(
      "legal_banner",
      "SkyCache Nexus: store-and-forward knowledge + community mesh. Receive-only satellite. Not free commercial broadband or Starlink."
    );
    $("offlineChip").textContent = t("offline_ok", "Offline OK");
    $("pkgCount").textContent = `${state.packages.length} ${t("items", "items")}`;
    const mode = state.status ? state.status.power_mode : " - ";
    const bat =
      state.status && state.status.battery_percent != null
        ? `${Math.round(state.status.battery_percent)}%`
        : "";
    $("powerChip").textContent = bat ? `${bat}  |  ${mode}` : mode;
    if (mode === "critical" || mode === "emergency") {
      $("powerChip").classList.add("warn");
    }
    $("ttsToggle").textContent = state.tts ? t("voice_on", "Voice on") : t("voice_off", "Voice");
    $("ttsToggle").setAttribute("aria-pressed", state.tts ? "true" : "false");
    $("recentTitle").textContent = t("recent", "Recent");
    $("msgTitle").textContent = t("messages", "Community notes");
    $("msgSend").textContent = t("queue_note", "Queue note");
    $("navHome").textContent = t("home", "Home");
    $("navMsg").textContent = t("notes", "Notes");
    if ($("navBoard")) $("navBoard").textContent = t("board", "Board");
    if ($("navLib")) $("navLib").textContent = t("library", "Library");
    if ($("navReq")) $("navReq").textContent = t("request", "Request");
    $("navAdmin").textContent = t("admin", "Admin");
    if ($("libTitle")) $("libTitle").textContent = t("skybrary", "Skybrary");
    if ($("libLead")) {
      $("libLead").textContent = t(
        "skybrary_lead",
        "Open written knowledge - public domain samples. Not a complete archive. Not free commercial internet."
      );
    }
    if ($("libSearch")) $("libSearch").placeholder = t("lib_search_ph", "Search Skybrary works...");
    // capabilities chip optional
    if (state.capsSummary && $("meshChip")) {
      /* leave mesh chip; capabilities in admin */
    }
    $("backHome").textContent = "← " + t("back", "Back");
    if ($("readerBack")) $("readerBack").textContent = "← " + t("back", "Back");
    if ($("readerLegal")) {
      $("readerLegal").textContent = t(
        "reader_legal",
        "Open / public-domain text  |  local bookmark only  |  not free commercial broadband"
      );
    }
    if ($("readerRaw")) $("readerRaw").textContent = t("reader_raw", "Raw file");
    if ($("readerSave")) $("readerSave").textContent = t("reader_save", "Save file");
    if ($("phoneDemoTitle")) {
      $("phoneDemoTitle").textContent = t(
        "phone_demo_title",
        "No cell plan? Save demos here"
      );
    }
    if ($("phoneDemoBody")) {
      $("phoneDemoBody").textContent = t(
        "phone_demo_body",
        "You are on the local hub Wi-Fi. Tap below to download three public-domain sample texts onto this phone. Works without mobile data - not commercial satellite internet."
      );
    }
    if ($("phoneDemoDownload")) {
      $("phoneDemoDownload").textContent = t(
        "phone_demo_download",
        "Save demos to this phone"
      );
    }
    if ($("libDemoDownload")) {
      $("libDemoDownload").textContent = t(
        "phone_demo_download",
        "Save demos to this phone"
      );
    }
    if ($("phoneDemoOpenLib")) {
      $("phoneDemoOpenLib").textContent = t("phone_demo_open_lib", "Open Library");
    }
    if ($("zeroNetLead")) {
      $("zeroNetLead").textContent = t(
        "zero_net_lead",
        "No Wi-Fi and no cell? Use the zero-network kit (USB / Bluetooth / SD) - open READ-OFFLINE.html offline."
      );
    }
    if ($("zeroNetKit")) {
      $("zeroNetKit").textContent = t("zero_net_kit", "Zero-network kit (USB/BT/SD)");
    }
    if ($("zeroNetHtml")) {
      $("zeroNetHtml").textContent = t("zero_net_html", "Offline reader HTML");
    }
    if ($("readerBookmarkHint")) {
      $("readerBookmarkHint").textContent = t(
        "reader_bookmark_hint",
        "Position saved on this device"
      );
    }
    if ($("readerPrev")) $("readerPrev").setAttribute("title", t("reader_prev", "Previous work"));
    if ($("readerNext")) $("readerNext").setAttribute("title", t("reader_next", "Next work"));
    if ($("readerFontDown")) $("readerFontDown").setAttribute("aria-label", t("reader_font_down", "Smaller text"));
    if ($("readerFontUp")) $("readerFontUp").setAttribute("aria-label", t("reader_font_up", "Larger text"));
    if ($("reqTitle")) $("reqTitle").textContent = t("request_content", "Request content");
    if ($("reqLead")) {
      $("reqLead").textContent = t(
        "request_lead",
        "Queue an open-content pack for the next USB mule or legal gateway pull. Emergency and health first. Not commercial internet."
      );
    }
    if ($("reqSend")) $("reqSend").textContent = t("queue_request", "Queue request");
    if ($("meshTitle")) $("meshTitle").textContent = t("mesh_status", "Mesh & traffic");
    if ($("boardTitle")) $("boardTitle").textContent = t("boards", "Village boards");
    if ($("boardSend")) $("boardSend").textContent = t("post_board", "Post to board");
    if ($("searchBox")) $("searchBox").placeholder = t("search_ph", "Search library...");
    if ($("searchTitle")) $("searchTitle").textContent = t("search_results", "Search results");
    const meshEl = $("meshChip");
    if (meshEl) {
      const n = state.nexus;
      if (n && n.mesh) {
        const peers = (n.mesh.peers && n.mesh.peers.length) || 0;
        const dm = n.disaster_mode ? "  |  disaster" : "";
        meshEl.textContent = `${t("mesh_chip", "Mesh")} ${peers}${dm}`;
        meshEl.classList.toggle("ok", n.mesh.enabled);
        meshEl.classList.toggle("warn", !!n.disaster_mode);
      } else {
        meshEl.textContent = t("mesh_chip", "Mesh");
      }
    }
  }

  function renderCategories() {
    const grid = $("categoryGrid");
    grid.innerHTML = "";
    const order = ["emergency", "health", "education", "agriculture", "weather", "maps"];
    order.forEach((id) => {
      const count = state.packages.filter((p) => p.priority_class === id).length;
      const card = document.createElement("button");
      card.type = "button";
      card.className = "cat-card";
      card.innerHTML = `
        <span class="emoji">${CAT_META[id].emoji}</span>
        <span class="label">${t("cat_" + id, id)}</span>
        <span class="count">${count}</span>
      `;
      card.addEventListener("click", () => {
        state.category = id;
        speak(t("cat_" + id, id));
        showView("category");
        renderCategory();
      });
      grid.appendChild(card);
    });
  }

  function redisChipClass(flag) {
    if (flag === "yes") return "yes";
    if (flag === "no") return "no";
    return "review";
  }

  function fillPassportBody(p) {
    const body = $("passportBody");
    if (!body || !p) return;
    const redist = p.redistribute || "review";
    const url =
      (p.provenance && (p.provenance.url || (p.provenance.detail && p.provenance.detail.url))) || "";
    const srcType = (p.provenance && (p.provenance.source_type || p.provenance.note)) || "";
    const hashDisp = p.sha256 ? String(p.sha256) : " - ";
    body.innerHTML = `
      <div class="row"><span class="k">${t("passport_license", "License")}</span>
        <span class="v">${escapeHtml(p.license || "unknown")}</span></div>
      <div class="row"><span class="k">${t("passport_redistribute", "Redistribute")}</span>
        <span class="v"><span class="chip passport ${redisChipClass(redist)}">${escapeHtml(redist)}</span>
        ${escapeHtml(p.redistribute_note || "")}</span></div>
      <div class="row"><span class="k">${t("passport_provenance", "Provenance")}</span>
        <span class="v">${url ? `<a href="${escapeHtml(url)}" style="color:var(--accent)">${escapeHtml(url)}</a>` : escapeHtml(srcType || " - ")}</span></div>
      <div class="row"><span class="k">${t("passport_retrieved", "Retrieved")}</span>
        <span class="v">${escapeHtml(p.retrieval_date || " - ")}</span></div>
      <div class="row"><span class="k">${t("passport_sha256", "SHA-256")}</span>
        <span class="v hash">${escapeHtml(hashDisp)}</span></div>
      <p class="note">${escapeHtml(p.legal || "")}</p>
    `;
  }

  async function openPassport(kind, id) {
    const sheet = $("passportSheet");
    const body = $("passportBody");
    if (!sheet || !body) return;
    $("passportTitle").textContent = t("passport_title", "License passport");
    body.innerHTML = `<p class="note">${t("passport_loading", "Loading passport...")}</p>`;
    sheet.classList.remove("hidden");
    const url =
      kind === "work"
        ? `/api/skybrary/works/${encodeURIComponent(id)}/passport`
        : `/api/packages/${encodeURIComponent(id)}/passport`;
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error("fail");
      const p = await r.json();
      $("passportTitle").textContent =
        (p.title || id) + "  |  " + t("passport", "Passport");
      fillPassportBody(p);
      speak(t("passport", "Passport") + " " + (p.license || ""));
    } catch {
      body.innerHTML = `<p class="note" style="color:var(--danger)">${t("passport_fail", "Passport unavailable")}</p>`;
    }
  }

  function closePassport() {
    const sheet = $("passportSheet");
    if (sheet) sheet.classList.add("hidden");
  }

  function packageCard(pkg) {
    const a = document.createElement("div");
    a.className = "item-card";
    const primary =
      (pkg.files || []).find((f) => f.path && f.path.endsWith(".html")) || (pkg.files || [])[0];
    const href = primary ? `/content/${pkg.id}/${primary.path}` : "#";
    const rating =
      pkg.rating && pkg.rating.count
        ? `  |  ★ ${pkg.rating.average} (${pkg.rating.count})`
        : "";
    a.innerHTML = `
      <a href="${href}" style="color:inherit;text-decoration:none">
        <h3>${escapeHtml(titleOf(pkg))}</h3>
        <p>${escapeHtml(summaryOf(pkg))}</p>
      </a>
      <div class="meta">
        <span class="chip">${ageLabel(pkg.age_hours || 0)}</span>
        ${pkg.is_stale ? `<span class="chip stale">${t("stale", "May be outdated")}</span>` : ""}
        <span class="chip">${pkg.priority_class}${rating}</span>
        <button type="button" class="chip passport pass-btn" data-pkg="${escapeHtml(pkg.id)}" title="${t("passport_title", "License passport")}">
          ${t("passport", "Passport")}  |  ${escapeHtml(pkg.license || " - ")}
        </button>
      </div>
      <div class="meta" style="margin-top:0.4rem">
        <button type="button" class="chip rate-btn" data-id="${escapeHtml(pkg.id)}" data-stars="5">★5</button>
        <button type="button" class="chip rate-btn" data-id="${escapeHtml(pkg.id)}" data-stars="4">★4</button>
        <button type="button" class="chip rate-btn" data-id="${escapeHtml(pkg.id)}" data-stars="3">★3</button>
      </div>
    `;
    a.querySelectorAll(".rate-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const id = btn.getAttribute("data-id");
        const stars = Number(btn.getAttribute("data-stars"));
        await fetch(`/api/packages/${id}/rating`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ stars, token: state.voter }),
        });
        speak(t("rated", "Thanks"));
      });
    });
    a.querySelectorAll(".pass-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        openPassport("package", btn.getAttribute("data-pkg"));
      });
    });
    return a;
  }

  function renderRecent() {
    const list = $("recentList");
    list.innerHTML = "";
    state.packages.slice(0, 8).forEach((pkg) => list.appendChild(packageCard(pkg)));
  }

  function renderCategory() {
    $("catTitle").textContent = t("cat_" + state.category, state.category);
    const list = $("catList");
    list.innerHTML = "";
    state.packages
      .filter((p) => p.priority_class === state.category)
      .forEach((pkg) => list.appendChild(packageCard(pkg)));
  }

  async function runSearch(q) {
    showView("search");
    const list = $("searchList");
    list.innerHTML = `<p style="color:#94a3b8">${t("searching", "Searching...")}</p>`;
    try {
      const data = await fetch(`/api/search?q=${encodeURIComponent(q)}`).then((r) => r.json());
      list.innerHTML = "";
      if (!data.results || !data.results.length) {
        list.innerHTML = `<p style="color:#94a3b8">${t("no_results", "No results")}</p>`;
        return;
      }
      data.results.forEach((pkg) => list.appendChild(packageCard(pkg)));
    } catch {
      list.innerHTML = `<p style="color:#f87171">Search unavailable</p>`;
    }
  }

  async function renderMessages() {
    const list = $("msgList");
    list.innerHTML = "";
    try {
      const msgs = await fetch("/api/messages").then((r) => r.json());
      if (!msgs.length) {
        list.innerHTML = `<p style="color:#94a3b8">${t("no_messages", "No community notes yet.")}</p>`;
        return;
      }
      msgs.reverse().forEach((m) => {
        const div = document.createElement("div");
        div.className = "item-card";
        div.innerHTML = `<h3>${escapeHtml(m.subject)}</h3><p>${escapeHtml(m.body)}</p>
          <div class="meta"><span class="chip">${escapeHtml(m.author)}</span></div>`;
        list.appendChild(div);
      });
    } catch {
      list.innerHTML = `<p style="color:#f87171">Messages unavailable</p>`;
    }
  }

  async function renderBoard() {
    const tabs = $("boardTabs");
    const list = $("boardList");
    const sel = $("boardSelect");
    if (!tabs || !list) return;
    try {
      const boards = await fetch("/api/boards").then((r) => r.json());
      tabs.innerHTML = "";
      sel.innerHTML = "";
      boards.forEach((b) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = b.label || b.id;
        btn.className = b.id === state.board ? "active" : "";
        btn.addEventListener("click", () => {
          state.board = b.id;
          renderBoard();
        });
        tabs.appendChild(btn);
        const opt = document.createElement("option");
        opt.value = b.id;
        opt.textContent = b.label || b.id;
        if (b.id === state.board) opt.selected = true;
        sel.appendChild(opt);
      });
      const posts = await fetch(
        `/api/boards/posts?board=${encodeURIComponent(state.board)}`
      ).then((r) => r.json());
      list.innerHTML = "";
      if (!posts.length) {
        list.innerHTML = `<p style="color:#94a3b8">${t("no_posts", "No posts yet.")}</p>`;
        return;
      }
      posts.forEach((p) => {
        const div = document.createElement("div");
        div.className = "item-card";
        div.innerHTML = `<h3>${escapeHtml(p.title)}</h3><p>${escapeHtml(p.body)}</p>
          <div class="meta"><span class="chip">${escapeHtml(p.author)}</span>
          <span class="chip">${escapeHtml(p.board)}</span></div>`;
        list.appendChild(div);
      });
    } catch {
      list.innerHTML = `<p style="color:#f87171">Boards unavailable</p>`;
    }
  }

  async function renderRequest() {
    const panel = $("meshPanel");
    if (!panel) return;
    try {
      const n = await fetch("/api/nexus/status").then((r) => r.json());
      panel.textContent = JSON.stringify(
        {
          node_id: n.node_id,
          packages: n.packages,
          disaster_mode: n.disaster_mode,
          traffic: n.traffic,
          power_map: n.power_map,
          control_plane: n.control_plane,
          gateway: n.gateway,
          mesh: { peers: (n.mesh && n.mesh.peers) || [], mode: n.mesh && n.mesh.mode },
          banner: n.banner,
        },
        null,
        2
      );
    } catch {
      panel.textContent = "Mesh status unavailable";
    }
  }

  function showView(name) {
    const map = {
      home: "viewHome",
      category: "viewCategory",
      messages: "viewMessages",
      request: "viewRequest",
      board: "viewBoard",
      search: "viewSearch",
      library: "viewLibrary",
      reader: "viewReader",
    };
    Object.keys(map).forEach((k) => {
      const el = $(map[k]);
      if (el) el.classList.toggle("hidden", k !== name);
    });
    document.body.classList.toggle("reader-mode", name === "reader");
    $("navHome").classList.toggle("active", name === "home" || name === "category" || name === "search");
    $("navMsg").classList.toggle("active", name === "messages");
    if ($("navReq")) $("navReq").classList.toggle("active", name === "request");
    if ($("navBoard")) $("navBoard").classList.toggle("active", name === "board");
    if ($("navLib")) $("navLib").classList.toggle("active", name === "library" || name === "reader");
  }

  /* - -  Reader bookmarks (local only, no PII cloud) - -  */
  function loadBookmarks() {
    try {
      return JSON.parse(localStorage.getItem(READER_BM_KEY) || "{}") || {};
    } catch {
      return {};
    }
  }

  function saveBookmark(workId, data) {
    if (!workId) return;
    const all = loadBookmarks();
    all[workId] = {
      ratio: data.ratio || 0,
      scrollY: data.scrollY || 0,
      packageId: data.packageId || null,
      path: data.path || null,
      updated: Date.now(),
    };
    try {
      localStorage.setItem(READER_BM_KEY, JSON.stringify(all));
    } catch {
      /* quota - ignore */
    }
  }

  function getBookmark(workId) {
    const all = loadBookmarks();
    return all[workId] || null;
  }

  function pickReadablePath(work) {
    const editions = work.editions || [];
    const txt = editions.find(
      (e) =>
        e.format === "txt" ||
        (e.path && (e.path.endsWith(".txt") || e.path.endsWith(".md")))
    );
    if (txt && txt.path) return txt.path;
    const html = editions.find(
      (e) => e.format === "html" || (e.path && e.path.endsWith(".html"))
    );
    if (html && html.path) return html.path;
    // Skybrary packs always ship work.txt + index.html
    return "work.txt";
  }

  function applyReaderFont() {
    const fs = Math.min(READER_FS_MAX, Math.max(READER_FS_MIN, state.reader.fontSize));
    state.reader.fontSize = fs;
    document.documentElement.style.setProperty("--reader-fs", fs + "rem");
    localStorage.setItem(READER_FS_KEY, String(fs));
  }

  function updateReaderProgress() {
    const bar = $("readerProgress");
    if (!bar) return;
    const doc = document.documentElement;
    const max = Math.max(1, doc.scrollHeight - window.innerHeight);
    const ratio = Math.min(1, Math.max(0, window.scrollY / max));
    bar.style.width = (ratio * 100).toFixed(1) + "%";
    if (state.reader.workId) {
      saveBookmark(state.reader.workId, {
        ratio,
        scrollY: window.scrollY,
        packageId: state.reader.packageId,
        path: state.reader.path,
      });
    }
  }

  function extractReadableText(raw, path) {
    const lower = (path || "").toLowerCase();
    if (lower.endsWith(".txt") || lower.endsWith(".md") || lower.endsWith(".text")) {
      return { kind: "text", body: raw };
    }
    // HTML: prefer <pre> payload (sample packs), else strip chrome to body text
    try {
      const doc = new DOMParser().parseFromString(raw, "text/html");
      const pre = doc.querySelector("pre");
      if (pre && (pre.textContent || "").trim().length > 40) {
        return { kind: "text", body: pre.textContent };
      }
      const article = doc.querySelector("article") || doc.body;
      if (article) {
        // Keep simple markup for large-type reading
        const clone = article.cloneNode(true);
        clone.querySelectorAll("script,style,nav,header,footer").forEach((n) => n.remove());
        const html = clone.innerHTML.trim();
        if (html.length > 20) return { kind: "html", body: html };
        return { kind: "text", body: clone.textContent || raw };
      }
    } catch {
      /* fall through */
    }
    return { kind: "text", body: raw };
  }

  function renderChapterNav() {
    const el = $("readerChapters");
    const chs = state.reader.chapters || [];
    if (!el) return;
    if (chs.length <= 1) {
      el.hidden = true;
      el.innerHTML = "";
      return;
    }
    el.hidden = false;
    el.innerHTML = chs
      .map((c, i) => {
        const active = i === state.reader.chapterIndex ? " active" : "";
        return `<button type="button" class="chip${active}" data-ch="${i}">${escapeHtml(
          c.title || "Ch " + (i + 1)
        )}</button>`;
      })
      .join(" ");
    el.querySelectorAll("button[data-ch]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = parseInt(btn.getAttribute("data-ch") || "0", 10);
        loadReaderChapter(i);
      });
    });
    const cp = $("readerChapPrev");
    const cn = $("readerChapNext");
    if (cp) cp.disabled = state.reader.chapterIndex <= 0;
    if (cn) cn.disabled = state.reader.chapterIndex >= chs.length - 1;
  }

  async function loadReaderChapter(chapterIndex) {
    const workId = state.reader.workId;
    if (!workId) return;
    const chs = state.reader.chapters || [];
    state.reader.chapterIndex = chapterIndex;
    $("readerBody").textContent = t("searching", "Searching...");
    try {
      // Prefer chapter API (EPUB sections + multi-file)
      const res = await fetch(
        `/api/skybrary/works/${encodeURIComponent(workId)}/chapters/${chapterIndex}`
      );
      if (res.ok) {
        const data = await res.json();
        const path = (data.chapter && data.chapter.path) || data.path || state.reader.path;
        state.reader.path = path;
        const kind = data.kind === "html" ? "html" : "text";
        renderReaderBody({ kind, body: data.body || "" });
        const chTitle = (data.chapter && data.chapter.title) || "";
        if ($("readerMeta") && chTitle) {
          const base = $("readerMeta").textContent.split("  |  ")[0] || "";
          $("readerMeta").textContent = [base, chTitle, path].filter(Boolean).join("  |  ");
        }
        renderChapterNav();
        window.scrollTo(0, 0);
        updateReaderProgress();
        return;
      }
      // Fallback: raw content path from chapter list
      const ch = chs[chapterIndex];
      if (!ch || !state.reader.packageId) throw new Error("no chapter");
      const path = ch.path || "work.txt";
      const contentUrl = `/content/${encodeURIComponent(state.reader.packageId)}/${path
        .split("/")
        .map(encodeURIComponent)
        .join("/")}`;
      const res2 = await fetch(contentUrl);
      if (!res2.ok) throw new Error("not found");
      const raw = await res2.text();
      state.reader.path = path;
      renderReaderBody(extractReadableText(raw, path));
      renderChapterNav();
      window.scrollTo(0, 0);
    } catch {
      $("readerBody").textContent = t(
        "reader_load_error",
        "Could not load chapter on this node."
      );
    }
  }

  async function openReader(work, index) {
    if (!work || !work.package_id) {
      speak(t("reader_unavailable", "Content not on this node"));
      return;
    }
    const path = pickReadablePath(work);
    const title =
      (work.title && (work.title[state.lang] || work.title.en)) || work.work_id;
    const creators = (work.creators || []).join(", ");
    const license = work.license || "";

    state.reader.workId = work.work_id;
    state.reader.packageId = work.package_id;
    state.reader.path = path;
    state.reader.index = typeof index === "number" ? index : state.libResults.findIndex(
      (w) => w.work_id === work.work_id
    );
    state.reader.chapters = [];
    state.reader.chapterIndex = 0;

    showView("reader");
    applyReaderFont();
    $("readerTitle").textContent = title;
    $("readerMeta").textContent = [creators, license, path].filter(Boolean).join("  |  ");
    $("readerBody").textContent = t("searching", "Searching...");
    $("readerBody").classList.remove("reader-html");

    const contentUrl = `/content/${encodeURIComponent(work.package_id)}/${path
      .split("/")
      .map(encodeURIComponent)
      .join("/")}`;
    const downloadUrl = contentUrl + (contentUrl.includes("?") ? "&" : "?") + "download=1";
    const rawLink = $("readerRaw");
    if (rawLink) {
      rawLink.href = contentUrl;
      rawLink.style.display = "";
    }
    const saveLink = $("readerSave");
    if (saveLink) {
      const fname = (path.split("/").pop() || "work.txt").replace(/[^\w.\-]+/g, "_");
      saveLink.href = downloadUrl;
      saveLink.setAttribute("download", fname);
      saveLink.style.display = "";
    }

    const prevBtn = $("readerPrev");
    const nextBtn = $("readerNext");
    if (prevBtn) prevBtn.disabled = state.reader.index <= 0;
    if (nextBtn) {
      nextBtn.disabled =
        state.reader.index < 0 || state.reader.index >= state.libResults.length - 1;
    }

    // Load chapter list (multi-file + EPUB spine)
    try {
      const chRes = await fetch(
        `/api/skybrary/works/${encodeURIComponent(work.work_id)}/chapters`
      );
      if (chRes.ok) {
        const chData = await chRes.json();
        state.reader.chapters = chData.chapters || [];
      }
    } catch {
      state.reader.chapters = [];
    }
    renderChapterNav();

    if (state.reader.chapters.length > 1) {
      await loadReaderChapter(0);
      speak(title);
      return;
    }

    try {
      const res = await fetch(contentUrl);
      if (!res.ok) {
        if (path !== "index.html") {
          const fb = `/content/${encodeURIComponent(work.package_id)}/index.html`;
          const res2 = await fetch(fb);
          if (!res2.ok) throw new Error("not found");
          const raw2 = await res2.text();
          const parsed2 = extractReadableText(raw2, "index.html");
          renderReaderBody(parsed2);
          if (rawLink) rawLink.href = fb;
          state.reader.path = "index.html";
        } else {
          throw new Error("not found");
        }
      } else {
        const raw = await res.text();
        renderReaderBody(extractReadableText(raw, path));
      }
      requestAnimationFrame(() => {
        const bm = getBookmark(work.work_id);
        if (bm && (bm.ratio > 0.02 || bm.scrollY > 40)) {
          const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
          const y = bm.ratio != null ? bm.ratio * max : bm.scrollY;
          window.scrollTo(0, y);
        } else {
          window.scrollTo(0, 0);
        }
        updateReaderProgress();
      });
      speak(title);
    } catch {
      $("readerBody").textContent = t(
        "reader_load_error",
        "Could not load text. Is the package on this node? Try: skycache skybrary samples --ingest"
      );
    }
  }

  function renderReaderBody(parsed) {
    const el = $("readerBody");
    if (!el) return;
    if (parsed.kind === "html") {
      el.classList.add("reader-html");
      const tmp = document.createElement("div");
      tmp.innerHTML = parsed.body;
      tmp.querySelectorAll("*").forEach((node) => {
        [...node.attributes].forEach((attr) => {
          if (/^on/i.test(attr.name) || attr.name === "srcdoc") node.removeAttribute(attr.name);
          if (attr.name === "href" && /^\s*javascript:/i.test(attr.value)) node.removeAttribute("href");
        });
      });
      el.innerHTML = tmp.innerHTML;
    } else {
      el.classList.remove("reader-html");
      // Convert plain text to paragraphs for CSS pagination columns
      const text = parsed.body || "";
      if (state.reader.paginate) {
        el.classList.add("reader-html");
        el.innerHTML = text
          .split(/\n\n+/)
          .map((p) => `<p>${escapeHtml(p).replace(/\n/g, "<br/>")}</p>`)
          .join("");
      } else {
        el.textContent = text;
      }
    }
    applyPaginationMode();
  }

  function applyPaginationMode() {
    const wrap = $("readerPageWrap");
    const btn = $("readerPaginate");
    const ind = $("readerPageInd");
    if (!wrap) return;
    wrap.classList.toggle("paginate-on", !!state.reader.paginate);
    if (btn) {
      btn.setAttribute("aria-pressed", state.reader.paginate ? "true" : "false");
      btn.classList.toggle("primary", !!state.reader.paginate);
    }
    if (!state.reader.paginate) {
      if (ind) ind.hidden = true;
      state.reader.pageIndex = 0;
      state.reader.pageCount = 1;
      return;
    }
    // After layout, estimate page count from scrollWidth
    requestAnimationFrame(() => {
      const pageW = wrap.clientWidth || 1;
      const total = wrap.scrollWidth || pageW;
      const pages = Math.max(1, Math.ceil(total / pageW - 0.01));
      state.reader.pageCount = pages;
      state.reader.pageIndex = Math.min(
        state.reader.pageIndex,
        Math.max(0, pages - 1)
      );
      wrap.scrollLeft = state.reader.pageIndex * pageW;
      updatePageIndicator();
    });
  }

  function updatePageIndicator() {
    const ind = $("readerPageInd");
    const wrap = $("readerPageWrap");
    if (!ind || !wrap || !state.reader.paginate) return;
    ind.hidden = false;
    ind.textContent =
      t("reader_page", "Page") +
      " " +
      (state.reader.pageIndex + 1) +
      " / " +
      state.reader.pageCount;
    const pp = $("readerPagePrev");
    const pn = $("readerPageNext");
    if (pp) pp.disabled = state.reader.pageIndex <= 0;
    if (pn) pn.disabled = state.reader.pageIndex >= state.reader.pageCount - 1;
  }

  function readerPageNavigate(delta) {
    if (!state.reader.paginate) return;
    const wrap = $("readerPageWrap");
    if (!wrap) return;
    const pageW = wrap.clientWidth || 1;
    const next = Math.max(
      0,
      Math.min(state.reader.pageCount - 1, state.reader.pageIndex + delta)
    );
    state.reader.pageIndex = next;
    wrap.scrollTo({ left: next * pageW, behavior: "smooth" });
    updatePageIndicator();
  }

  function togglePagination() {
    state.reader.paginate = !state.reader.paginate;
    try {
      localStorage.setItem(
        "skycache_reader_paginate",
        state.reader.paginate ? "1" : "0"
      );
    } catch {
      /* ignore */
    }
    state.reader.pageIndex = 0;
    // Re-render body for plain text -> paragraphs when enabling pages
    const el = $("readerBody");
    if (el && !el.classList.contains("reader-html") && state.reader.paginate) {
      const text = el.textContent || "";
      el.classList.add("reader-html");
      el.innerHTML = text
        .split(/\n\n+/)
        .map((p) => `<p>${escapeHtml(p).replace(/\n/g, "<br/>")}</p>`)
        .join("");
    }
    applyPaginationMode();
  }

  function readerNavigate(delta) {
    const i = state.reader.index + delta;
    if (i < 0 || i >= state.libResults.length) return;
    openReader(state.libResults[i], i);
  }

  async function renderLibrary(q, subject) {
    const list = $("libList");
    const facetsEl = $("libFacets");
    if (!list) return;
    list.innerHTML = `<p style="color:#94a3b8">${t("searching", "Searching...")}</p>`;
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (subject) params.set("subject", subject);
      const data = await fetch(`/api/skybrary/works?${params}`).then((r) => r.json());
      if (facetsEl && data.facets && data.facets.subjects) {
        facetsEl.innerHTML = "";
        const all = document.createElement("button");
        all.type = "button";
        all.textContent = t("all", "All");
        all.className = !subject ? "active" : "";
        all.addEventListener("click", () => renderLibrary($("libSearch").value.trim(), null));
        facetsEl.appendChild(all);
        Object.keys(data.facets.subjects).slice(0, 8).forEach((sub) => {
          const b = document.createElement("button");
          b.type = "button";
          b.textContent = sub;
          b.className = subject === sub ? "active" : "";
          b.addEventListener("click", () => renderLibrary($("libSearch").value.trim(), sub));
          facetsEl.appendChild(b);
        });
      }
      list.innerHTML = "";
      state.libResults = data.results || [];
      if (!data.results || !data.results.length) {
        list.innerHTML = `<p style="color:#94a3b8">${t("no_results", "No results")} - ${t("run_samples", "Run: skycache skybrary samples --ingest")}</p>`;
        return;
      }
      data.results.forEach((w, idx) => {
        const title = (w.title && (w.title[state.lang] || w.title.en)) || w.work_id;
        const summary = (w.summary && (w.summary[state.lang] || w.summary.en)) || "";
        const pkg = w.package_id;
        const div = document.createElement("div");
        div.className = "item-card";
        const bm = getBookmark(w.work_id);
        const bmChip =
          bm && bm.ratio > 0.02
            ? `<span class="chip ok">${t("reader_resume", "Resume")} ${Math.round(bm.ratio * 100)}%</span>`
            : "";
        div.innerHTML = `
          <button type="button" class="reader-open" style="all:unset;cursor:pointer;display:block;width:100%">
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(summary)}</p>
          </button>
          <div class="meta">
            <span class="chip">${escapeHtml((w.creators || []).join(", "))}</span>
            <button type="button" class="chip passport pass-work-btn" data-work="${escapeHtml(w.work_id)}" title="${t("passport_title", "License passport")}">
              ${t("passport", "Passport")}  |  ${escapeHtml(w.license || " - ")}
            </button>
            <span class="chip">tier ${w.civilizational_tier}</span>
            ${(w.subjects || []).slice(0, 3).map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join("")}
            ${bmChip}
            ${pkg ? `<a class="chip" href="/content/${encodeURIComponent(pkg)}/index.html" target="_blank" rel="noopener">${t("reader_raw", "Raw file")}</a>` : ""}
            ${pkg ? `<a class="chip ok" href="/content/${encodeURIComponent(pkg)}/work.txt?download=1" download="${escapeHtml(pkg)}.txt">${t("reader_save", "Save file")}</a>` : ""}
          </div>`;
        const openBtn = div.querySelector(".reader-open");
        openBtn.addEventListener("click", () => openReader(w, idx));
        div.querySelectorAll(".pass-work-btn").forEach((btn) => {
          btn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            openPassport("work", btn.getAttribute("data-work"));
          });
        });
        list.appendChild(div);
      });
    } catch {
      list.innerHTML = `<p style="color:#f87171">Skybrary unavailable</p>`;
      state.libResults = [];
    }
  }

  function renderAll() {
    renderLang();
    renderHeader();
    renderCategories();
    renderRecent();
    if (state.category) renderCategory();
  }

  async function setupPhoneDemo() {
    const statusEl = $("phoneDemoStatus");
    try {
      const data = await fetch("/api/demo?ensure=1").then((r) => r.json());
      const ready = data && data.ok;
      const n = (data && data.count_ready) || 0;
      const exp = (data && data.count_expected) || 3;
      if (statusEl) {
        statusEl.textContent = ready
          ? t("phone_demo_ready", "Ready") + `: ${n}/${exp} ` + t("phone_demo_texts", "demo texts on this hub")
          : t("phone_demo_missing", "Demos not ready on this hub yet");
        statusEl.style.color = ready ? "#34d399" : "#fbbf24";
      }
      const href = (data && data.download_all_path) || "/api/demo/pack.zip";
      ["phoneDemoDownload", "libDemoDownload"].forEach((id) => {
        const a = $(id);
        if (a) {
          a.href = href;
          a.setAttribute("download", (data && data.download_all_filename) || "skycache-skybrary-demo-3texts.zip");
        }
      });
    } catch {
      if (statusEl) {
        statusEl.textContent = t("phone_demo_error", "Could not check demos");
        statusEl.style.color = "#f87171";
      }
    }
  }

  async function setupOnboarding() {
    if (localStorage.getItem("skycache_onboard_done") === "1") return;
    try {
      state.onboard = await fetch("/api/onboarding").then((r) => r.json());
    } catch {
      return;
    }
    const box = $("onboardBanner");
    if (!box || !state.onboard || !state.onboard.steps) return;
    box.style.display = "block";
    const total = state.onboard.steps.length;
    const show = () => {
      const step = state.onboard.steps[state.onboardStep];
      if (!step) {
        box.style.display = "none";
        localStorage.setItem("skycache_onboard_done", "1");
        return;
      }
      const n = state.onboardStep + 1;
      $("onboardTitle").textContent = total > 1 ? `(${n}/${total}) ${step.title}` : step.title;
      $("onboardBody").textContent = step.body;
    };
    show();
    $("onboardNext").onclick = () => {
      state.onboardStep += 1;
      show();
    };
    $("onboardSkip").onclick = () => {
      box.style.display = "none";
      localStorage.setItem("skycache_onboard_done", "1");
    };
  }

  function wire() {
    if ($("passportClose")) {
      $("passportClose").addEventListener("click", closePassport);
    }
    if ($("passportSheet")) {
      $("passportSheet").addEventListener("click", (e) => {
        if (e.target === $("passportSheet")) closePassport();
      });
    }
    $("backHome").addEventListener("click", () => {
      state.category = null;
      showView("home");
    });
    $("navHome").addEventListener("click", () => {
      state.category = null;
      showView("home");
    });
    $("navMsg").addEventListener("click", () => {
      showView("messages");
      renderMessages();
    });
    if ($("navBoard")) {
      $("navBoard").addEventListener("click", () => {
        showView("board");
        renderBoard();
      });
    }
    if ($("navLib")) {
      $("navLib").addEventListener("click", () => {
        showView("library");
        renderLibrary("", null);
      });
    }
    if ($("phoneDemoOpenLib")) {
      $("phoneDemoOpenLib").addEventListener("click", () => {
        showView("library");
        renderLibrary("", null);
      });
    }
    if ($("readerBack")) {
      $("readerBack").addEventListener("click", () => {
        updateReaderProgress();
        showView("library");
        // keep last list if present
        if (!state.libResults.length) renderLibrary($("libSearch") ? $("libSearch").value.trim() : "", null);
      });
    }
    if ($("readerPrev")) $("readerPrev").addEventListener("click", () => readerNavigate(-1));
    if ($("readerNext")) $("readerNext").addEventListener("click", () => readerNavigate(1));
    if ($("readerChapPrev")) {
      $("readerChapPrev").addEventListener("click", () => {
        if (state.reader.chapterIndex > 0) loadReaderChapter(state.reader.chapterIndex - 1);
      });
    }
    if ($("readerChapNext")) {
      $("readerChapNext").addEventListener("click", () => {
        const n = (state.reader.chapters || []).length;
        if (state.reader.chapterIndex < n - 1) loadReaderChapter(state.reader.chapterIndex + 1);
      });
    }
    if ($("readerPagePrev")) {
      $("readerPagePrev").addEventListener("click", () => readerPageNavigate(-1));
    }
    if ($("readerPageNext")) {
      $("readerPageNext").addEventListener("click", () => readerPageNavigate(1));
    }
    if ($("readerPaginate")) {
      $("readerPaginate").addEventListener("click", () => togglePagination());
    }
    if ($("readerPageWrap")) {
      $("readerPageWrap").addEventListener("scroll", () => {
        if (!state.reader.paginate) return;
        const wrap = $("readerPageWrap");
        const pageW = wrap.clientWidth || 1;
        state.reader.pageIndex = Math.round(wrap.scrollLeft / pageW);
        updatePageIndicator();
      });
    }
    if ($("readerFontUp")) {
      $("readerFontUp").addEventListener("click", () => {
        state.reader.fontSize = Math.min(READER_FS_MAX, state.reader.fontSize + READER_FS_STEP);
        applyReaderFont();
      });
    }
    if ($("readerFontDown")) {
      $("readerFontDown").addEventListener("click", () => {
        state.reader.fontSize = Math.max(READER_FS_MIN, state.reader.fontSize - READER_FS_STEP);
        applyReaderFont();
      });
    }
    let scrollT = null;
    window.addEventListener(
      "scroll",
      () => {
        if (!$("viewReader") || $("viewReader").classList.contains("hidden")) return;
        clearTimeout(scrollT);
        scrollT = setTimeout(updateReaderProgress, 120);
      },
      { passive: true }
    );
    if ($("libSearch")) {
      let lt = null;
      $("libSearch").addEventListener("input", () => {
        clearTimeout(lt);
        lt = setTimeout(() => renderLibrary($("libSearch").value.trim(), null), 280);
      });
    }
    if ($("navReq")) {
      $("navReq").addEventListener("click", () => {
        showView("request");
        renderRequest();
      });
    }
    $("ttsToggle").addEventListener("click", () => {
      state.tts = !state.tts;
      localStorage.setItem("skycache_tts", state.tts ? "1" : "0");
      renderHeader();
      if (state.tts) speak(t("voice_on", "Voice on"));
    });
    $("msgForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      await fetch("/api/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          author: $("msgAuthor").value,
          subject: $("msgSubject").value,
          body: $("msgBody").value,
        }),
      });
      $("msgBody").value = "";
      renderMessages();
    });
    if ($("boardForm")) {
      $("boardForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        await fetch("/api/boards/posts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            board: $("boardSelect").value || state.board,
            author: $("boardAuthor").value,
            title: $("boardPostTitle").value,
            body: $("boardBody").value,
          }),
        });
        $("boardBody").value = "";
        $("boardPostTitle").value = "";
        renderBoard();
      });
    }
    if ($("reqForm")) {
      $("reqForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const pid = ($("reqPackage").value || "").trim();
        const st = $("reqStatus");
        if (!pid) {
          st.textContent = t("need_package", "Enter a package id");
          st.style.color = "#f87171";
          return;
        }
        try {
          const res = await fetch("/api/nexus/request", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              package_id: pid,
              priority_class: $("reqPriority").value || "education",
            }),
          });
          const body = await res.json();
          if (!res.ok) throw new Error(body.detail || res.statusText);
          st.textContent = t("request_queued", "Queued") + ": " + (body.bundle_id || "").slice(0, 8);
          st.style.color = "#34d399";
          $("reqPackage").value = "";
          renderRequest();
        } catch (err) {
          st.textContent = String(err.message || err);
          st.style.color = "#f87171";
        }
      });
    }
    let searchTimer = null;
    $("searchBox").addEventListener("input", () => {
      const q = $("searchBox").value.trim();
      clearTimeout(searchTimer);
      if (!q) {
        showView("home");
        return;
      }
      searchTimer = setTimeout(() => runSearch(q), 280);
    });
  }

  async function boot() {
    document.documentElement.lang = state.lang;
    document.documentElement.dir = state.lang === "ar" ? "rtl" : "ltr";
    applyReaderFont();
    wire();
    await loadI18n();
    try {
      await loadData();
    } catch (e) {
      console.error(e);
    }
    renderAll();
    setupOnboarding();
    setupPhoneDemo();
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }

  boot();
})();
