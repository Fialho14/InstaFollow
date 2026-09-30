/* Pedidos de seguimento enviados — tudo processado localmente. */

(function () {
  "use strict";

  const TARGET_FILE = "pending_follow_requests.json";
  const THEME_KEY = "instafollow:tema";
  const root = document.documentElement;
  const el = (id) => document.getElementById(id);

  const fileInput = el("pendingFileInput");
  const uploadButton = el("pendingUploadButton");
  const dropZone = el("pendingDropZone");
  const uploadStatus = el("pendingUploadStatus");
  const results = el("pendingResults");
  const total = el("pendingTotal");
  const visible = el("pendingVisible");
  const search = el("pendingSearch");
  const sort = el("pendingSort");
  const list = el("pendingRequestList");
  const empty = el("pendingEmpty");
  const themeToggle = el("themeToggle");
  const siteHeader = el("siteHeader");

  let requests = [];

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
      /* preferência não disponível */
    }
  }

  const storedTheme = readTheme();
  if (storedTheme !== "auto") {
    root.dataset.theme = storedTheme;
  }

  themeToggle.addEventListener("click", () => {
    applyTheme(resolvedTheme() === "dark" ? "light" : "dark");
  });

  function updateHeader() {
    siteHeader.classList.toggle("scrolled", window.scrollY > 8);
  }

  window.addEventListener("scroll", updateHeader, { passive: true });
  updateHeader();
  el("year").textContent = String(new Date().getFullYear());

  function fileBaseName(path) {
    return String(path || "").replace(/\\/g, "/").split("/").pop().toLowerCase();
  }

  function isZip(file) {
    const name = file.name.toLowerCase();
    return name.endsWith(".zip") || file.type === "application/zip" || file.type === "application/x-zip-compressed";
  }

  async function readPendingFile(file) {
    if (isZip(file)) {
      if (!window.fflate || typeof window.fflate.unzipSync !== "function") {
        throw new Error("O leitor ZIP local não carregou.");
      }

      const entries = window.fflate.unzipSync(new Uint8Array(await file.arrayBuffer()), {
        filter(entry) {
          return fileBaseName(entry.name) === TARGET_FILE;
        },
      });
      const match = Object.entries(entries).find(([path]) => fileBaseName(path) === TARGET_FILE);
      if (!match) {
        throw new Error("Não encontrei pending_follow_requests.json dentro do ZIP.");
      }
      return window.fflate.strFromU8(match[1]);
    }

    if (fileBaseName(file.name) !== TARGET_FILE) {
      throw new Error("Escolhe o ZIP do Instagram ou pending_follow_requests.json.");
    }
    return file.text();
  }

  function labelValue(entry, wantedLabel) {
    if (!entry || !Array.isArray(entry.label_values)) {
      return "";
    }
    const match = entry.label_values.find((item) =>
      item && String(item.label || "").trim().toLowerCase() === wantedLabel
    );
    return match && typeof match.value === "string" ? match.value.trim() : "";
  }

  function normalizeUsername(value) {
    if (typeof value !== "string") {
      return "";
    }
    let username = value.trim().replace(/^@+/, "");
    if (username.includes("instagram.com")) {
      try {
        const url = new URL(username);
        username = url.pathname.split("/").filter(Boolean).pop() || "";
      } catch {
        return "";
      }
    }
    return username.replace(/^\/+|\/+$/g, "").split("?")[0].split("#")[0].toLowerCase();
  }

  function usersFromStringList(entries) {
    if (!Array.isArray(entries)) {
      return [];
    }
    return entries.flatMap((entry) => {
      if (!entry || !Array.isArray(entry.string_list_data)) {
        return [];
      }
      return entry.string_list_data.map((item) => ({
        username: normalizeUsername(item && (item.value || item.href)),
        name: typeof entry.title === "string" ? entry.title.trim() : "",
        timestamp: Number.isFinite(Number(item && item.timestamp)) ? Number(item.timestamp) : null,
      }));
    });
  }

  function parseRequests(text) {
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("pending_follow_requests.json não é JSON válido.");
    }

    let parsed = [];
    if (Array.isArray(data)) {
      parsed = data.map((entry) => ({
        username: normalizeUsername(labelValue(entry, "username") || labelValue(entry, "url")),
        name: labelValue(entry, "name"),
        timestamp: Number.isFinite(Number(entry && entry.timestamp)) ? Number(entry.timestamp) : null,
      }));
    } else if (data && typeof data === "object") {
      parsed = usersFromStringList(
        data.relationships_follow_requests_sent ||
        data.relationships_pending_follow_requests ||
        data.pending_follow_requests
      );
    }

    const unique = new Map();
    for (const request of parsed) {
      if (request.username) {
        unique.set(request.username, request);
      }
    }
    return Array.from(unique.values());
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatDate(timestamp) {
    if (!timestamp) {
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

  function avatarLabel(username) {
    const match = username.match(/[a-z0-9]/i);
    return match ? match[0].toUpperCase() : "#";
  }

  function avatarHue(username) {
    return Array.from(username).reduce((sum, char, index) =>
      sum + (index + 1) * char.charCodeAt(0), 0) % 360;
  }

  function render() {
    const query = search.value.trim().toLowerCase();
    const ordered = requests
      .filter((request) =>
        request.username.includes(query) || request.name.toLowerCase().includes(query)
      )
      .sort((a, b) => {
        if (sort.value === "oldest") {
          return (a.timestamp || 0) - (b.timestamp || 0);
        }
        if (sort.value === "username") {
          return a.username.localeCompare(b.username);
        }
        return (b.timestamp || 0) - (a.timestamp || 0);
      });

    const fragment = document.createDocumentFragment();
    ordered.forEach((request) => {
      const item = document.createElement("li");
      const href = "https://www.instagram.com/" + encodeURIComponent(request.username) + "/";
      item.className = "pending-request-card";
      item.style.setProperty("--avatar-hue", avatarHue(request.username));
      item.innerHTML = `
        <div class="avatar" aria-hidden="true">${escapeHtml(avatarLabel(request.username))}</div>
        <div class="user-main">
          <div class="username-row">
            <a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">@${escapeHtml(request.username)}</a>
            <span class="status-pill">À espera</span>
          </div>
          <div class="meta-row">
            ${request.name ? `<span>${escapeHtml(request.name)}</span><span class="meta-dot" aria-hidden="true"></span>` : ""}
            <span>Enviado em ${escapeHtml(formatDate(request.timestamp))}</span>
          </div>
        </div>
        <a class="button ghost small" href="${escapeHtml(href)}" target="_blank" rel="noreferrer">Abrir</a>
      `;
      fragment.appendChild(item);
    });

    list.replaceChildren(fragment);
    visible.textContent = String(ordered.length);
    empty.hidden = ordered.length !== 0;
  }

  async function handleUpload(fileList) {
    const files = Array.from(fileList || []);
    if (files.length !== 1) {
      uploadStatus.textContent = "Escolhe apenas um ZIP ou o ficheiro JSON.";
      uploadStatus.className = "upload-status error";
      return;
    }

    uploadButton.disabled = true;
    uploadStatus.textContent = "A processar localmente…";
    uploadStatus.className = "upload-status";

    try {
      const text = await readPendingFile(files[0]);
      requests = parseRequests(text);
      total.textContent = String(requests.length);
      search.value = "";
      sort.value = "recent";
      results.hidden = false;
      render();
      uploadStatus.textContent = requests.length
        ? "Pronto: " + requests.length + " pedidos encontrados."
        : "Ficheiro carregado: não há pedidos pendentes.";
      uploadStatus.className = "upload-status success";
      results.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        block: "start",
      });
    } catch (error) {
      results.hidden = true;
      uploadStatus.textContent = error.message || "Não foi possível processar o ficheiro.";
      uploadStatus.className = "upload-status error";
    } finally {
      uploadButton.disabled = false;
      fileInput.value = "";
    }
  }

  uploadButton.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => handleUpload(fileInput.files));
  search.addEventListener("input", render);
  sort.addEventListener("change", render);

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

  dropZone.addEventListener("click", (event) => {
    if (event.target.closest("label, input, button, a")) {
      return;
    }
    fileInput.click();
  });

  dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  dropZone.addEventListener("drop", (event) => {
    handleUpload(event.dataTransfer.files);
  });
})();
