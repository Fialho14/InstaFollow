/* ============================================================
   InstaFollow — lógica da aplicação
   Tudo corre localmente no browser. Sem pedidos externos.
   ============================================================ */

(function () {
  "use strict";

  document.documentElement.classList.add("js");

  /* ------------------------------ Constantes ------------------------------ */

  const DELETED_USERNAME_PREFIX = "__deleted__";
  const IG_IGNORED_PATHS = new Set(["accounts", "explore", "p", "reel", "stories", "_u"]);
  const STORAGE_KEY = "naoMeSeguemEstados:v2";
  const THEME_KEY = "instafollow:tema";

  const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)");

  /* ------------------------------ Elementos ------------------------------ */

  const el = (id) => document.getElementById(id);

  const fileInput = el("fileInput");
  const uploadButton = el("uploadButton");
  const demoButton = el("demoButton");
  const dropZone = el("dropZone");
  const uploadStatus = el("uploadStatus");
  const sourceStrip = el("sourceStrip");
  const search = el("search");
  const sortSelect = el("sort");
  const list = el("userList");
  const tabs = Array.from(document.querySelectorAll(".view-tab"));
  const visibleCount = el("visibleCount");
  const followersCount = el("followersCount");
  const followingCount = el("followingCount");
  const resultCount = el("resultCount");
  const pendingCount = el("pendingCount");
  const doneCount = el("doneCount");
  const unavailableCount = el("unavailableCount");
  const filterPendingCount = el("filterPendingCount");
  const filterAllCount = el("filterAllCount");
  const filterDoneCount = el("filterDoneCount");
  const filterUnavailableCount = el("filterUnavailableCount");
  const progressPercent = el("progressPercent");
  const progressText = el("progressText");
  const emptyState = el("emptyState");
  const emptyText = el("emptyText");
  const footnote = el("footnote");
  const exportCsvButton = el("exportCsv");
  const themeToggle = el("themeToggle");
  const siteHeader = el("siteHeader");
  const yearEl = el("year");
  const root = document.documentElement;

  /* ------------------------------ Estado ------------------------------ */

  let activeFilter = "pending";
  let savedState = readState();
  let cards = [];
  let totalResultCount = 0;

  function readState() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY));
      return value && typeof value === "object" ? value : {};
    } catch {
      return {};
    }
  }

  function writeState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      return;
    }
  }

  /* ------------------------------- Tema ------------------------------- */

  function readTheme() {
    try {
      const value = localStorage.getItem(THEME_KEY);
      return value === "light" || value === "dark" ? value : "auto";
    } catch {
      return "auto";
    }
  }

  function resolvedTheme() {
    const stored = readTheme();
    if (stored !== "auto") {
      return stored;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    root.dataset.theme = theme;
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* sem persistência disponível */
    }
  }

  themeToggle.addEventListener("click", () => {
    applyTheme(resolvedTheme() === "dark" ? "light" : "dark");
  });

  const storedTheme = readTheme();
  if (storedTheme !== "auto") {
    root.dataset.theme = storedTheme;
  }

  /* ------------------------------ Header ------------------------------ */

  function updateHeader() {
    siteHeader.classList.toggle("scrolled", window.scrollY > 8);
  }

  window.addEventListener("scroll", updateHeader, { passive: true });
  updateHeader();

  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }

  /* --------------------------- Reveal on scroll --------------------------- */

  const revealTargets = Array.from(document.querySelectorAll(".reveal"));

  if ("IntersectionObserver" in window && !REDUCED_MOTION.matches) {
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      }
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });

    for (const target of revealTargets) {
      observer.observe(target);
    }
  } else {
    for (const target of revealTargets) {
      target.classList.add("visible");
    }
  }

  /* --------------------------- Interface: upload --------------------------- */

  function setUploadStatus(message, tone) {
    uploadStatus.textContent = message;
    uploadStatus.classList.toggle("success", tone === "success");
    uploadStatus.classList.toggle("error", tone === "error");
  }

  function setControlsEnabled(enabled) {
    search.disabled = !enabled;
    sortSelect.disabled = !enabled;
    exportCsvButton.disabled = !enabled;
    for (const tab of tabs) {
      tab.disabled = !enabled;
    }
  }

  function setSourcePills(labels) {
    sourceStrip.replaceChildren(...labels.map((label) => {
      const pill = document.createElement("span");
      pill.className = "source-pill";
      pill.textContent = label;
      return pill;
    }));
  }

  /* --------------------------- Leitura de ficheiros --------------------------- */

  function fileBaseName(path) {
    return normalizePath(path).split("/").pop() || "";
  }

  function normalizePath(path) {
    return String(path || "").replace(/\\/g, "/").replace(/^\/+/, "");
  }

  function isZipFile(file) {
    const name = file.name.toLowerCase();
    return name.endsWith(".zip") || file.type === "application/zip" || file.type === "application/x-zip-compressed";
  }

  function isJsonFile(file) {
    return file.name.toLowerCase().endsWith(".json") || file.type === "application/json";
  }

  function isFollowersFileName(name) {
    return /^followers_\d+\.json$/i.test(name);
  }

  function isTargetInstagramJsonPath(path) {
    const normalized = normalizePath(path);
    const basename = fileBaseName(normalized);
    const isTargetName = basename.toLowerCase() === "following.json" || isFollowersFileName(basename);

    if (!isTargetName) {
      return false;
    }

    return normalized.includes("connections/followers_and_following/") ||
      normalized.includes("followers_and_following/") ||
      !normalized.includes("/");
  }

  async function filesFromUpload(fileList) {
    const files = Array.from(fileList || []);

    if (!files.length) {
      throw new Error("Nenhum ficheiro selecionado.");
    }

    const zipFiles = files.filter(isZipFile);
    if (zipFiles.length) {
      if (files.length !== 1) {
        throw new Error("Envia o ZIP sozinho, ou seleciona apenas ficheiros JSON.");
      }

      return filesFromZip(zipFiles[0]);
    }

    const jsonFiles = files.filter(isJsonFile);
    if (!jsonFiles.length) {
      throw new Error("Seleciona um ZIP do Instagram ou ficheiros JSON.");
    }

    if (jsonFiles.length !== files.length) {
      throw new Error("Remove ficheiros que não sejam JSON.");
    }

    return Promise.all(jsonFiles.map(async (file) => ({
      path: file.webkitRelativePath || file.name,
      name: file.name,
      text: await file.text(),
    })));
  }

  async function filesFromZip(file) {
    if (!window.fflate || typeof window.fflate.unzipSync !== "function") {
      throw new Error("O leitor ZIP local não carregou. Confirma que vendor/fflate.min.js existe.");
    }

    const bytes = new Uint8Array(await file.arrayBuffer());
    const entries = window.fflate.unzipSync(bytes, {
      filter(entry) {
        return isTargetInstagramJsonPath(entry.name);
      },
    });

    const jsonFiles = Object.entries(entries).map(([path, data]) => ({
      path,
      name: fileBaseName(path),
      text: window.fflate.strFromU8(data),
    }));

    if (!jsonFiles.length) {
      throw new Error("Não encontrei following.json nem followers_*.json dentro do ZIP.");
    }

    return jsonFiles;
  }

  /* --------------------------- Parsing do export --------------------------- */

  function parseJsonFile(file) {
    try {
      return JSON.parse(file.text);
    } catch {
      throw new Error(fileBaseName(file.path) + " não é JSON válido.");
    }
  }

  function parseInstagramFiles(files) {
    const followingFiles = files.filter((file) => fileBaseName(file.path).toLowerCase() === "following.json");
    const followersFiles = files.filter((file) => isFollowersFileName(fileBaseName(file.path)));

    if (!followingFiles.length) {
      throw new Error("following.json não encontrado.");
    }

    if (!followersFiles.length) {
      throw new Error("followers_*.json não encontrado.");
    }

    const following = loadFollowing(parseJsonFile(followingFiles[0]));
    const followers = new Map();

    for (const file of followersFiles.sort((a, b) => normalizePath(a.path).localeCompare(normalizePath(b.path)))) {
      mergeUsers(followers, loadFollowers(parseJsonFile(file)));
    }

    const rawNotFollowingBack = Array.from(following.keys())
      .filter((username) => !followers.has(username))
      .sort((a, b) => a.localeCompare(b));
    const usernames = rawNotFollowingBack.filter((username) => !isProbablyUnavailable(username));
    const skippedUnavailableCount = rawNotFollowingBack.length - usernames.length;

    return {
      followersCount: followers.size,
      followingCount: following.size,
      users: usernames.map((username) => following.get(username)),
      skippedUnavailableCount,
      files: {
        following: followingFiles[0],
        followers: followersFiles,
      },
    };
  }

  function loadFollowers(data) {
    const followers = new Map();

    if (Array.isArray(data)) {
      mergeUsers(followers, extractUsersFromEntries(data));
    } else if (data && typeof data === "object") {
      for (const value of Object.values(data)) {
        mergeUsers(followers, extractUsersFromEntries(value));
      }
    }

    return followers;
  }

  function loadFollowing(data) {
    if (data && typeof data === "object" && !Array.isArray(data)) {
      return extractUsersFromEntries(data.relationships_following);
    }

    return extractUsersFromEntries(data);
  }

  function mergeUsers(target, source) {
    for (const [username, user] of source) {
      target.set(username, user);
    }
  }

  function extractUsersFromEntries(entries) {
    const users = new Map();

    if (!Array.isArray(entries)) {
      return users;
    }

    for (const entry of entries) {
      if (!entry || typeof entry !== "object") {
        continue;
      }

      const title = entry.title;
      const stringListData = entry.string_list_data;
      if (!Array.isArray(stringListData) || !stringListData.length) {
        continue;
      }

      for (const item of stringListData) {
        if (!item || typeof item !== "object") {
          continue;
        }

        const username = normalizeUsername(item.value, title, item.href);
        if (!username) {
          continue;
        }

        users.set(username, {
          username,
          href: profileUrl(username, item.href),
          timestamp: timestampFromItem(item),
        });
      }
    }

    return users;
  }

  function normalizeUsername(...values) {
    for (const value of values) {
      if (typeof value !== "string" || !value.trim()) {
        continue;
      }

      let raw = value.trim();
      if (raw.includes("instagram.com")) {
        raw = usernameFromUrl(raw) || "";
      }

      raw = raw.trim().replace(/^@+/, "").replace(/^\/+|\/+$/g, "");
      if (!raw) {
        continue;
      }

      raw = decodeUriComponentSafe(raw).split("?")[0].split("#")[0].replace(/^\/+|\/+$/g, "").toLowerCase();

      if (!raw || IG_IGNORED_PATHS.has(raw)) {
        continue;
      }

      return raw;
    }

    return null;
  }

  function usernameFromUrl(url) {
    try {
      const parsed = new URL(url.trim());
      if (!parsed.hostname.endsWith("instagram.com")) {
        return null;
      }

      const parts = parsed.pathname
        .split("/")
        .map((part) => decodeUriComponentSafe(part))
        .filter(Boolean);

      if (!parts.length) {
        return null;
      }

      if (parts[0] === "_u" && parts.length > 1) {
        return parts[1];
      }

      return parts[0];
    } catch {
      return null;
    }
  }

  function profileUrl(username, href) {
    if (typeof href === "string" && href.includes("instagram.com")) {
      const usernameFromHref = normalizeUsername(href);
      if (usernameFromHref === username) {
        return "https://www.instagram.com/" + encodeURIComponent(username) + "/";
      }
    }

    return "https://www.instagram.com/" + encodeURIComponent(username) + "/";
  }

  function timestampFromItem(item) {
    return Number.isInteger(item.timestamp) ? item.timestamp : null;
  }

  function decodeUriComponentSafe(value) {
    try {
      return decodeURIComponent(value);
    } catch {
      return value;
    }
  }

  function isProbablyUnavailable(username) {
    return username.startsWith(DELETED_USERNAME_PREFIX);
  }

  /* ------------------------------ Utilitários ------------------------------ */

  function avatarLabel(username) {
    for (const char of username) {
      if (/^[a-z0-9]$/i.test(char)) {
        return char.toUpperCase();
      }
    }

    return "#";
  }

  function avatarHue(username) {
    let total = 0;
    for (let index = 0; index < username.length; index += 1) {
      total += (index + 1) * username.charCodeAt(index);
    }
    return total % 360;
  }

  function formatDate(timestamp) {
    if (timestamp === null || timestamp === undefined) {
      return "Data desconhecida";
    }

    const date = new Date(timestamp * 1000);
    if (Number.isNaN(date.getTime())) {
      return "Data desconhecida";
    }

    return date.toLocaleDateString("pt-PT", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatNumber(value) {
    return Number(value).toLocaleString("pt-PT");
  }

  const animatedValues = new WeakMap();

  function animateNumber(element, target) {
    const to = Number(target) || 0;
    const from = animatedValues.get(element) || 0;
    animatedValues.set(element, to);

    if (REDUCED_MOTION.matches || Math.abs(to - from) < 2) {
      element.textContent = formatNumber(to);
      return;
    }

    const duration = 500;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = formatNumber(Math.round(from + (to - from) * eased));
      if (progress < 1 && animatedValues.get(element) === to) {
        requestAnimationFrame(tick);
      }
    }

    requestAnimationFrame(tick);
  }

  /* ------------------------------ Renderização ------------------------------ */

  function renderResults(dataset) {
    totalResultCount = dataset.users.length;
    animateNumber(followersCount, dataset.followersCount);
    animateNumber(followingCount, dataset.followingCount);
    animateNumber(resultCount, totalResultCount);
    search.value = "";
    sortSelect.value = "username";
    activeFilter = "pending";
    resetTabs();

    list.replaceChildren();
    const fragment = document.createDocumentFragment();
    dataset.users.forEach((user, index) => {
      fragment.appendChild(createUserCard(user, index + 1));
    });
    list.appendChild(fragment);
    cards = Array.from(list.querySelectorAll(".user-card"));

    setControlsEnabled(cards.length > 0);
    hydrateState();
    sortUsers();
    filterUsers();

    const followerLabel = dataset.files.followers.length === 1
      ? "1 followers_*.json"
      : dataset.files.followers.length + " followers_*.json";
    setSourcePills([
      fileBaseName(dataset.files.following.path),
      followerLabel,
      dataset.skippedUnavailableCount + " apagadas removidas",
    ]);
    footnote.textContent = "Contas apagadas removidas automaticamente: " + dataset.skippedUnavailableCount + ". Tudo processado localmente.";
  }

  function createUserCard(user, index) {
    const li = document.createElement("li");
    const username = user.username;
    const timestamp = user.timestamp || 0;
    const href = user.href;
    li.className = "user-card";
    li.dataset.username = username;
    li.dataset.timestamp = String(timestamp);
    li.style.setProperty("--avatar-hue", avatarHue(username));

    li.innerHTML = `
      <label class="done-check">
        <input class="done-checkbox" type="checkbox" data-action="done" aria-label="Marcar @${escapeHtml(username)} como retirado">
        <span class="checkmark" aria-hidden="true">
          <svg viewBox="0 0 18 18" focusable="false">
            <path d="M4.2 9.3 7.5 12.6 13.9 5.5"></path>
          </svg>
        </span>
      </label>

      <div class="avatar" aria-hidden="true">${escapeHtml(avatarLabel(username))}</div>

      <div class="user-main">
        <div class="username-row">
          <a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">@${escapeHtml(username)}</a>
          <span class="status-pill">Pendente</span>
        </div>
        <div class="meta-row">
          <span>Seguido desde ${escapeHtml(formatDate(user.timestamp))}</span>
          <span class="meta-dot" aria-hidden="true"></span>
          <span>#${index}</span>
        </div>
      </div>

      <div class="actions">
        <a class="button primary" href="${escapeHtml(href)}" target="_blank" rel="noreferrer" aria-label="Abrir @${escapeHtml(username)} no Instagram">
          <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
            <path d="M7.5 4.8h7.7v7.7"></path>
            <path d="M15 5 6.2 13.8"></path>
            <path d="M13.9 15.3H4.7V6.1"></path>
          </svg>
          <span>Abrir</span>
        </a>
        <button class="button ghost unavailable-button" type="button" data-action="unavailable" aria-pressed="false">
          <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
            <path d="M10 6.2v4.4"></path>
            <path d="M10 13.8h.01"></path>
            <path d="M10 2.9 18 17H2Z"></path>
          </svg>
          <span>Erro</span>
        </button>
      </div>
    `;

    return li;
  }

  /* ------------------------------ Estado dos cartões ------------------------------ */

  function resetTabs() {
    for (const tab of tabs) {
      const isActive = tab.dataset.filter === activeFilter;
      tab.classList.toggle("active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    }
  }

  function stateFor(card) {
    return savedState[card.dataset.username] || "pending";
  }

  function setCardState(card, nextState) {
    const username = card.dataset.username;

    if (nextState === "pending") {
      delete savedState[username];
    } else {
      savedState[username] = nextState;
    }

    writeState(savedState);
    applyCardState(card, nextState);
    filterUsers();
  }

  function applyCardState(card, cardState) {
    card.classList.toggle("done", cardState === "done");
    card.classList.toggle("unavailable", cardState === "unavailable");

    const doneCheckbox = card.querySelector('[data-action="done"]');
    const unavailableButton = card.querySelector('[data-action="unavailable"]');
    const statusPill = card.querySelector(".status-pill");

    doneCheckbox.checked = cardState === "done";
    unavailableButton.querySelector("span").textContent = cardState === "unavailable" ? "Pendente" : "Erro";
    unavailableButton.setAttribute("aria-pressed", String(cardState === "unavailable"));

    if (cardState === "done") {
      statusPill.textContent = "Retirado";
    } else if (cardState === "unavailable") {
      statusPill.textContent = "Indisponível";
    } else {
      statusPill.textContent = "Pendente";
    }
  }

  function hydrateState() {
    for (const card of cards) {
      applyCardState(card, stateFor(card));
    }
  }

  function counts() {
    let pending = 0;
    let done = 0;
    let unavailable = 0;

    for (const card of cards) {
      const cardState = stateFor(card);
      if (cardState === "done") {
        done += 1;
      } else if (cardState === "unavailable") {
        unavailable += 1;
      } else {
        pending += 1;
      }
    }

    return { pending, done, unavailable };
  }

  function updateSummary() {
    const current = counts();
    const finished = current.done + current.unavailable;
    const progress = totalResultCount === 0 ? 0 : Math.round((finished / totalResultCount) * 100);

    animateNumber(pendingCount, current.pending);
    animateNumber(doneCount, current.done);
    animateNumber(unavailableCount, current.unavailable);
    filterPendingCount.textContent = current.pending;
    filterAllCount.textContent = totalResultCount;
    filterDoneCount.textContent = current.done;
    filterUnavailableCount.textContent = current.unavailable;
    progressPercent.textContent = progress + "%";

    if (cards.length === 0 && totalResultCount === 0) {
      progressText.textContent = "À espera do teu export local.";
    } else if (current.pending === 0) {
      progressText.textContent = "Não há perfis pendentes. Bom trabalho!";
    } else if (current.pending === 1) {
      progressText.textContent = "Ainda tens 1 perfil pendente.";
    } else {
      progressText.textContent = "Ainda tens " + current.pending + " perfis pendentes.";
    }

    root.style.setProperty("--progress", progress + "%");
  }

  /* --------------------------- Ordenar e filtrar --------------------------- */

  function sortUsers() {
    const mode = sortSelect.value;
    const ordered = cards.slice().sort((a, b) => {
      if (mode === "recent") {
        return Number(b.dataset.timestamp) - Number(a.dataset.timestamp);
      }

      if (mode === "oldest") {
        return Number(a.dataset.timestamp) - Number(b.dataset.timestamp);
      }

      return a.dataset.username.localeCompare(b.dataset.username);
    });

    for (const card of ordered) {
      list.appendChild(card);
    }
  }

  function filterUsers() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;

    for (const card of cards) {
      const username = card.dataset.username || "";
      const cardState = stateFor(card);
      const matchesQuery = username.includes(query);
      const matchesFilter =
        activeFilter === "all" ||
        (activeFilter === "pending" && cardState === "pending") ||
        (activeFilter === "done" && cardState === "done") ||
        (activeFilter === "unavailable" && cardState === "unavailable");
      const isVisible = matchesQuery && matchesFilter;

      card.hidden = !isVisible;
      if (isVisible) {
        visible += 1;
      }
    }

    visibleCount.textContent = visible;
    if (cards.length === 0) {
      emptyText.textContent = totalResultCount === 0
        ? "Carrega o export para veres resultados — ou espreita a demonstração."
        : "A lista está vazia.";
    } else {
      emptyText.textContent = "Não há resultados para essa pesquisa ou filtro.";
    }
    emptyState.style.display = visible === 0 ? "grid" : "none";
    updateSummary();
  }

  /* ------------------------------ Exportar CSV ------------------------------ */

  function exportCsv() {
    if (!cards.length) {
      return;
    }

    const stateLabels = { pending: "pendente", done: "retirado", unavailable: "indisponivel" };
    const rows = [["username", "estado", "seguido_desde", "perfil"]];

    for (const card of cards) {
      if (card.hidden) {
        continue;
      }

      const username = card.dataset.username;
      const timestamp = Number(card.dataset.timestamp) || null;
      rows.push([
        username,
        stateLabels[stateFor(card)] || "pendente",
        timestamp ? new Date(timestamp * 1000).toISOString().slice(0, 10) : "",
        "https://www.instagram.com/" + username + "/",
      ]);
    }

    const csv = rows
      .map((row) => row.map((value) => '"' + String(value).replaceAll('"', '""') + '"').join(","))
      .join("\r\n");

    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "instafollow-" + new Date().toISOString().slice(0, 10) + ".csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  /* ------------------------------ Demonstração ------------------------------ */

  function demoDataset() {
    const now = Math.floor(Date.now() / 1000);
    const day = 86400;
    const demoFollowing = [
      "fotografia.lisboa", "chef.tiago", "wanderlust.ana", "gym.motivation.pt", "arte.urbana",
      "receitas.da.avo", "surfcaparica", "livros.e.cafe", "startup.porto", "viajante.solitario",
      "musica.indie.pt", "design.diario", "trilhos.serra", "cinema.classico", "horta.na.varanda",
    ];
    const demoFollowers = [
      "fotografia.lisboa", "chef.tiago", "wanderlust.ana", "receitas.da.avo", "livros.e.cafe",
      "musica.indie.pt", "trilhos.serra",
    ];

    const entry = (username, index) => ({
      title: username,
      string_list_data: [{
        value: username,
        href: "https://www.instagram.com/" + username + "/",
        timestamp: now - (index + 2) * 37 * day,
      }],
    });

    return [
      {
        path: "connections/followers_and_following/following.json",
        name: "following.json",
        text: JSON.stringify({ relationships_following: demoFollowing.map(entry) }),
      },
      {
        path: "connections/followers_and_following/followers_1.json",
        name: "followers_1.json",
        text: JSON.stringify(demoFollowers.map(entry)),
      },
    ];
  }

  function runDemo() {
    try {
      const dataset = parseInstagramFiles(demoDataset());
      renderResults(dataset);
      setSourcePills(["dados de demonstração"]);
      setUploadStatus("Demonstração carregada: " + dataset.users.length + " perfis fictícios.", "success");
      scrollToResults();
    } catch (error) {
      setUploadStatus(error.message || "Não foi possível carregar a demonstração.", "error");
    }
  }

  function scrollToResults() {
    const target = document.getElementById("resultados");
    if (target) {
      target.scrollIntoView({ behavior: REDUCED_MOTION.matches ? "auto" : "smooth", block: "start" });
    }
  }

  /* ------------------------------ Upload ------------------------------ */

  async function handleUpload(fileList) {
    setUploadStatus("A processar ficheiros localmente…", "");
    uploadButton.disabled = true;

    try {
      const files = await filesFromUpload(fileList);
      const dataset = parseInstagramFiles(files);
      renderResults(dataset);
      setUploadStatus("Resultado pronto: " + dataset.users.length + " perfis encontrados.", "success");
      scrollToResults();
    } catch (error) {
      setUploadStatus(error.message || "Não foi possível processar os ficheiros.", "error");
    } finally {
      uploadButton.disabled = false;
      fileInput.value = "";
    }
  }

  /* ------------------------------ Eventos ------------------------------ */

  uploadButton.addEventListener("click", () => fileInput.click());
  demoButton.addEventListener("click", runDemo);
  fileInput.addEventListener("change", () => handleUpload(fileInput.files));
  exportCsvButton.addEventListener("click", exportCsv);

  for (const eventName of ["dragenter", "dragover"]) {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("dragging");
    });
  }

  for (const eventName of ["dragleave", "drop"]) {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("dragging");
    });
  }

  dropZone.addEventListener("drop", (event) => {
    handleUpload(event.dataTransfer.files);
  });

  list.addEventListener("click", (event) => {
    const unavailableButton = event.target.closest("button[data-action='unavailable']");
    if (!unavailableButton) {
      return;
    }

    const card = unavailableButton.closest(".user-card");
    const nextState = stateFor(card) === "unavailable" ? "pending" : "unavailable";
    setCardState(card, nextState);
  });

  list.addEventListener("change", (event) => {
    if (!event.target.matches("[data-action='done']")) {
      return;
    }

    const card = event.target.closest(".user-card");
    setCardState(card, event.target.checked ? "done" : "pending");
  });

  for (const tab of tabs) {
    tab.addEventListener("click", () => {
      activeFilter = tab.dataset.filter;
      resetTabs();
      filterUsers();
    });
  }

  search.addEventListener("input", filterUsers);
  sortSelect.addEventListener("change", () => {
    sortUsers();
    filterUsers();
  });

  updateSummary();
})();
