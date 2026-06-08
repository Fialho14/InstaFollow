# ------------------------------------------------------------
# FERRAMENTA AUXILIAR OPCIONAL (no terminal):
#
# 1. Faz download dos teus dados do Instagram:
#       Instagram > Settings > Your information and permissions
#       > Download your information > ONLY "Followers and Following"
#       > Formato: JSON
#
# 2. Extrai o .zip.
#
# 3. Dentro da pasta extraida procura:
#       connections/followers_and_following/
#
# 4. Mete o caminho dessa pasta na variavel DATA_PATH aqui em baixo.
#
# 5. No terminal, corre:
#       python3 Insta/naoseguidores.py
#
# 6. Abre o ficheiro gerado:
#       Insta/nao_me_seguem_gerado.html
# ------------------------------------------------------------

from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


# === CAMINHO PARA A PASTA followers_and_following ===
DATA_PATH = Path("/Users/pedrofialho/Desktop/connections/followers_and_following")
# ====================================================

OUTPUT_HTML = Path(__file__).with_name("nao_me_seguem_gerado.html")
DELETED_USERNAME_PREFIX = "__deleted__"


@dataclass(frozen=True)
class InstagramUser:
    username: str
    href: str
    timestamp: int | None = None


def normalize_username(*values: str | None) -> str | None:
    """
    Normaliza usernames vindos do value/title/href:
    - tira espacos e @ no inicio
    - extrai corretamente links instagram.com/_u/username
    - ignora links de hashtags/explore
    - passa a minusculas para a comparacao bater certo
    """
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue

        raw = value.strip()
        if "instagram.com" in raw:
            raw = username_from_url(raw) or ""

        raw = raw.strip().lstrip("@").strip("/")
        if not raw:
            continue

        raw = unquote(raw).split("?")[0].split("#")[0].strip("/")
        raw = raw.lower()

        if raw in {"accounts", "explore", "p", "reel", "stories", "_u"}:
            continue

        return raw

    return None


def username_from_url(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if "instagram.com" not in parsed.netloc:
        return None

    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if not parts:
        return None

    if parts[0] == "_u" and len(parts) > 1:
        return parts[1]

    return parts[0]


def profile_url(username: str, href: str | None = None) -> str:
    if isinstance(href, str) and "instagram.com" in href:
        username_from_href = normalize_username(href)
        if username_from_href == username:
            return f"https://www.instagram.com/{username}/"

    return f"https://www.instagram.com/{username}/"


def timestamp_from_item(item: dict) -> int | None:
    timestamp = item.get("timestamp")
    return timestamp if isinstance(timestamp, int) else None


def extract_users_from_entries(entries: object) -> dict[str, InstagramUser]:
    users: dict[str, InstagramUser] = {}
    if not isinstance(entries, list):
        return users

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        title = entry.get("title")
        string_list_data = entry.get("string_list_data")
        if not isinstance(string_list_data, list) or not string_list_data:
            continue

        for item in string_list_data:
            if not isinstance(item, dict):
                continue

            value = item.get("value")
            href = item.get("href")
            username = normalize_username(value, title, href)
            if not username:
                continue

            users[username] = InstagramUser(
                username=username,
                href=profile_url(username, href),
                timestamp=timestamp_from_item(item),
            )

    return users


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_followers(data_path: Path) -> dict[str, InstagramUser]:
    followers: dict[str, InstagramUser] = {}

    for file_path in sorted(data_path.glob("followers_*.json")):
        data = load_json(file_path)

        if isinstance(data, list):
            followers.update(extract_users_from_entries(data))
        elif isinstance(data, dict):
            for value in data.values():
                followers.update(extract_users_from_entries(value))

    return followers


def load_following(data_path: Path) -> dict[str, InstagramUser]:
    # Importante: ler so following.json. O antigo following*.json tambem apanhava
    # following_hashtags.json e podia meter hashtags no resultado.
    file_path = data_path / "following.json"
    data = load_json(file_path)

    if isinstance(data, dict):
        return extract_users_from_entries(data.get("relationships_following"))

    return extract_users_from_entries(data)


def format_date(timestamp: int | None) -> str:
    if timestamp is None:
        return "Data desconhecida"

    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y")


def is_probably_unavailable(username: str) -> bool:
    return username.startswith(DELETED_USERNAME_PREFIX)


def avatar_label(username: str) -> str:
    for char in username:
        if char.isalnum():
            return char.upper()

    return "#"


def avatar_hue(username: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(username)) % 360


def html_user_rows(users: list[InstagramUser]) -> str:
    rows = []
    for index, user in enumerate(users, start=1):
        username = html.escape(user.username)
        href = html.escape(user.href, quote=True)
        followed_at = html.escape(format_date(user.timestamp))
        timestamp = user.timestamp or 0
        hue = avatar_hue(user.username)
        avatar = html.escape(avatar_label(user.username))
        rows.append(
            f"""
            <li class="user-card" data-username="{username}" data-timestamp="{timestamp}" style="--avatar-hue: {hue}">
              <label class="done-check">
                <input class="done-checkbox" type="checkbox" data-action="done" aria-label="Marcar @{username} como retirado">
                <span class="checkmark" aria-hidden="true">
                  <svg viewBox="0 0 18 18" focusable="false">
                    <path d="M4.2 9.3 7.5 12.6 13.9 5.5" />
                  </svg>
                </span>
              </label>

              <div class="avatar" aria-hidden="true">{avatar}</div>

              <div class="user-main">
                <div class="username-row">
                  <a href="{href}" target="_blank" rel="noreferrer">@{username}</a>
                  <span class="status-pill">Pendente</span>
                </div>
                <div class="meta-row">
                  <span>Seguido desde {followed_at}</span>
                  <span class="meta-dot" aria-hidden="true"></span>
                  <span>#{index}</span>
                </div>
              </div>

              <div class="actions">
                <a class="icon-button primary" href="{href}" target="_blank" rel="noreferrer" aria-label="Abrir @{username} no Instagram">
                  <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
                    <path d="M7.5 4.8h7.7v7.7" />
                    <path d="M15 5 6.2 13.8" />
                    <path d="M13.9 15.3H4.7V6.1" />
                  </svg>
                  <span>Abrir</span>
                </a>
                <button class="icon-button ghost unavailable-button" type="button" data-action="unavailable" aria-pressed="false">
                  <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
                    <path d="M10 6.2v4.4" />
                    <path d="M10 13.8h.01" />
                    <path d="M10 2.9 18 17H2Z" />
                  </svg>
                  <span>Erro</span>
                </button>
              </div>
            </li>
            """
        )

    return "\n".join(rows)


def build_html(
    followers_count: int,
    following_count: int,
    not_following_back: list[InstagramUser],
    skipped_unavailable_count: int,
) -> str:
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    result_count = len(not_following_back)
    rows = html_user_rows(not_following_back)
    initial_progress = 0 if result_count else 100

    return f"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nao me seguem de volta</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #15171a;
      --muted: #667085;
      --border: #d8dde6;
      --accent: #0f766e;
      --accent-dark: #0b5e58;
      --danger: #b42318;
      --done: #027a48;
      --warning: #b54708;
      --shadow: 0 10px 25px rgba(16, 24, 40, 0.08);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }}

    main {{
      width: min(980px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}

    header {{
      display: grid;
      gap: 18px;
      margin-bottom: 22px;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(2rem, 5vw, 3.4rem);
      line-height: 1;
      letter-spacing: 0;
    }}

    .subtitle {{
      margin: 0;
      max-width: 760px;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.55;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 22px 0;
    }}

    .stat {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      box-shadow: var(--shadow);
    }}

    .stat strong {{
      display: block;
      font-size: 1.9rem;
      line-height: 1.1;
    }}

    .stat span {{
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 0.92rem;
    }}

    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 2;
      display: grid;
      grid-template-columns: minmax(220px, 1fr) auto auto;
      gap: 12px;
      align-items: center;
      padding: 12px 0;
      background: rgba(246, 247, 249, 0.92);
      backdrop-filter: blur(12px);
    }}

    label {{
      display: grid;
      gap: 7px;
      color: var(--muted);
      font-size: 0.9rem;
      font-weight: 600;
    }}

    input {{
      width: 100%;
      min-height: 46px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0 14px;
      font: inherit;
      color: var(--text);
      background: var(--panel);
      outline: none;
    }}

    input:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.16);
    }}

    .visible-count {{
      align-self: end;
      min-height: 46px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      white-space: nowrap;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0 14px;
      background: var(--panel);
      color: var(--muted);
      font-weight: 700;
    }}

    .view-tabs {{
      align-self: end;
      display: inline-flex;
      min-height: 46px;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      background: var(--panel);
    }}

    button {{
      font: inherit;
    }}

    .view-tab {{
      border: 0;
      border-right: 1px solid var(--border);
      padding: 0 12px;
      background: transparent;
      color: var(--muted);
      font-weight: 800;
      cursor: pointer;
    }}

    .view-tab:last-child {{
      border-right: 0;
    }}

    .view-tab.active {{
      background: var(--accent);
      color: #ffffff;
    }}

    .user-list {{
      list-style: none;
      margin: 10px 0 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}

    .user-card {{
      display: grid;
      grid-template-columns: 44px 1fr auto;
      gap: 14px;
      align-items: center;
      min-height: 72px;
      padding: 12px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
    }}

    .user-card.done,
    .user-card.unavailable {{
      background: #f8fafc;
    }}

    .user-card.done .user-main a,
    .user-card.unavailable .user-main a {{
      color: var(--muted);
      text-decoration: line-through;
    }}

    .rank {{
      width: 38px;
      height: 38px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background: #e8f3f1;
      color: var(--accent-dark);
      font-weight: 800;
      font-size: 0.9rem;
    }}

    .user-main {{
      min-width: 0;
      display: grid;
      gap: 4px;
    }}

    .user-main a {{
      overflow-wrap: anywhere;
      color: var(--text);
      font-weight: 800;
      text-decoration: none;
    }}

    .user-main a:hover,
    .user-main a:focus {{
      color: var(--accent-dark);
      text-decoration: underline;
    }}

    .user-main span {{
      color: var(--muted);
      font-size: 0.92rem;
    }}

    .open-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
      border-radius: 8px;
      padding: 0 14px;
      background: var(--accent);
      color: #ffffff;
      text-decoration: none;
      font-weight: 800;
    }}

    .open-link:hover,
    .open-link:focus {{
      background: var(--accent-dark);
    }}

    .actions {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }}

    .state-button {{
      min-height: 40px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0 12px;
      background: var(--panel);
      color: var(--muted);
      font-weight: 800;
      cursor: pointer;
    }}

    .state-button:hover,
    .state-button:focus {{
      border-color: var(--accent);
      color: var(--accent-dark);
    }}

    .user-card.done .done-button {{
      border-color: rgba(2, 122, 72, 0.28);
      background: #ecfdf3;
      color: var(--done);
    }}

    .user-card.unavailable .unavailable-button {{
      border-color: rgba(180, 71, 8, 0.28);
      background: #fffaeb;
      color: var(--warning);
    }}

    .empty {{
      display: none;
      margin-top: 18px;
      padding: 20px;
      border: 1px dashed var(--border);
      border-radius: 8px;
      background: var(--panel);
      color: var(--muted);
      text-align: center;
    }}

    @media (max-width: 680px) {{
      main {{
        width: min(100% - 22px, 980px);
        padding-top: 22px;
      }}

      .stats {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .toolbar {{
        grid-template-columns: 1fr;
      }}

      .visible-count,
      .view-tabs {{
        align-self: stretch;
      }}

      .view-tab {{
        flex: 1;
      }}

      .user-card {{
        grid-template-columns: 38px 1fr;
      }}

      .open-link {{
        grid-column: 1 / -1;
      }}

      .actions {{
        grid-column: 1 / -1;
        justify-content: stretch;
      }}

      .actions a,
      .actions button {{
        flex: 1;
      }}
    }}
  </style>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f5f7;
      --bg-elevated: rgba(255, 255, 255, 0.78);
      --panel: rgba(255, 255, 255, 0.92);
      --panel-solid: #ffffff;
      --text: #1d1d1f;
      --muted: #6e6e73;
      --soft: #86868b;
      --border: rgba(0, 0, 0, 0.1);
      --border-strong: rgba(0, 0, 0, 0.16);
      --accent: #0071e3;
      --accent-strong: #0057b8;
      --done: #1d8f5f;
      --warning: #bf6a02;
      --shadow: 0 18px 55px rgba(0, 0, 0, 0.09);
      --shadow-soft: 0 8px 24px rgba(0, 0, 0, 0.06);
      --radius: 8px;
      --progress: {initial_progress}%;
    }}

    html {{
      background: var(--bg);
    }}

    body {{
      background:
        linear-gradient(180deg, #ffffff 0%, var(--bg) 260px),
        var(--bg);
      color: var(--text);
      text-rendering: optimizeLegibility;
      -webkit-font-smoothing: antialiased;
    }}

    main {{
      width: min(1180px, calc(100% - 32px));
      padding: 22px 0 54px;
    }}

    header {{
      gap: 22px;
      margin-bottom: 0;
      padding: 18px 0 12px;
    }}

    h1 {{
      max-width: 780px;
      font-size: clamp(2.45rem, 6vw, 5.4rem);
      line-height: 0.94;
    }}

    button,
    input,
    select {{
      font: inherit;
    }}

    button,
    a,
    input,
    select {{
      -webkit-tap-highlight-color: transparent;
    }}

    :focus-visible {{
      outline: 3px solid rgba(0, 113, 227, 0.32);
      outline-offset: 3px;
    }}

    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      color: var(--muted);
      font-size: 0.88rem;
      font-weight: 700;
    }}

    .brand {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }}

    .brand-mark {{
      width: 32px;
      height: 32px;
      display: grid;
      place-items: center;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--panel-solid);
      box-shadow: var(--shadow-soft);
    }}

    .brand-mark svg,
    .input-shell svg,
    .checkmark svg,
    .icon-button svg {{
      fill: none;
      stroke: currentColor;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}

    .brand-mark svg {{
      width: 18px;
      height: 18px;
      stroke-width: 1.8;
      color: var(--text);
    }}

    .generated {{
      white-space: nowrap;
    }}

    .hero-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
      gap: 24px;
      align-items: stretch;
    }}

    .hero-copy {{
      min-width: 0;
      display: grid;
      align-content: end;
      gap: 18px;
      padding: 22px 0;
    }}

    .eyebrow {{
      margin: 0;
      color: var(--accent);
      font-size: 0.82rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .subtitle {{
      max-width: 680px;
      color: var(--muted);
      font-size: clamp(1.02rem, 2vw, 1.24rem);
      line-height: 1.45;
    }}

    .source-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .source-pill {{
      display: inline-flex;
      align-items: center;
      min-height: 32px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 0 11px;
      background: var(--panel);
      color: var(--muted);
      font-size: 0.86rem;
      font-weight: 700;
      backdrop-filter: blur(18px);
    }}

    .progress-panel {{
      display: grid;
      gap: 18px;
      align-content: center;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 22px;
      background: var(--bg-elevated);
      box-shadow: var(--shadow);
      backdrop-filter: blur(28px) saturate(1.35);
    }}

    .progress-ring {{
      width: min(220px, 100%);
      aspect-ratio: 1;
      margin: 0 auto;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background:
        radial-gradient(circle at center, var(--panel-solid) 0 58%, transparent 59%),
        conic-gradient(var(--accent) var(--progress), rgba(0, 0, 0, 0.08) 0);
      box-shadow: inset 0 0 0 1px var(--border);
    }}

    .progress-ring strong {{
      display: block;
      font-size: clamp(2.1rem, 5vw, 3.2rem);
      line-height: 1;
      text-align: center;
    }}

    .progress-ring span {{
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 0.84rem;
      font-weight: 800;
      text-align: center;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .stats {{
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin: 8px 0 20px;
    }}

    .stat {{
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      background: var(--panel);
      box-shadow: var(--shadow-soft);
      backdrop-filter: blur(22px);
    }}

    .stat strong {{
      font-size: clamp(1.55rem, 3vw, 2.25rem);
      letter-spacing: 0;
    }}

    .stat span {{
      color: var(--muted);
      font-size: 0.88rem;
      font-weight: 700;
    }}

    .stat.pending strong {{
      color: var(--accent);
    }}

    .stat.done strong {{
      color: var(--done);
    }}

    .stat.unavailable strong {{
      color: var(--warning);
    }}

    .workbench {{
      display: grid;
      gap: 14px;
    }}

    .toolbar {{
      z-index: 10;
      grid-template-columns: minmax(240px, 1fr) minmax(150px, 190px);
      gap: 10px;
      align-items: end;
      padding: 14px 0;
      background: rgba(245, 245, 247, 0.84);
      backdrop-filter: blur(24px) saturate(1.3);
    }}

    label {{
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 7px;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }}

    .input-shell,
    select {{
      width: 100%;
      min-height: 48px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--panel-solid);
      box-shadow: var(--shadow-soft);
    }}

    .input-shell {{
      display: grid;
      grid-template-columns: 22px 1fr;
      gap: 10px;
      align-items: center;
      padding: 0 14px;
    }}

    .input-shell svg {{
      width: 18px;
      height: 18px;
      stroke-width: 2;
      color: var(--muted);
    }}

    input {{
      min-width: 0;
      width: 100%;
      min-height: auto;
      border: 0;
      padding: 0;
      background: transparent;
      color: var(--text);
      font-size: 1rem;
      outline: none;
    }}

    select {{
      appearance: none;
      padding: 0 34px 0 13px;
      color: var(--text);
      background-image:
        linear-gradient(45deg, transparent 50%, var(--muted) 50%),
        linear-gradient(135deg, var(--muted) 50%, transparent 50%);
      background-position:
        calc(100% - 18px) 20px,
        calc(100% - 12px) 20px;
      background-size: 6px 6px, 6px 6px;
      background-repeat: no-repeat;
      font-weight: 750;
      outline: none;
    }}

    .input-shell:focus-within,
    select:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.16);
    }}

    .filter-bar {{
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
    }}

    .view-tabs {{
      min-width: 0;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      min-height: 48px;
      padding: 4px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: rgba(232, 232, 237, 0.82);
      box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.05);
      backdrop-filter: blur(20px);
    }}

    .view-tab {{
      min-width: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      border: 0;
      border-radius: 7px;
      padding: 0 10px;
      background: transparent;
      color: var(--muted);
      font-weight: 850;
      cursor: pointer;
    }}

    .view-tab strong {{
      min-width: 24px;
      min-height: 22px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 0 7px;
      background: rgba(0, 0, 0, 0.07);
      color: inherit;
      font-size: 0.78rem;
      line-height: 1;
    }}

    .view-tab.active {{
      background: var(--panel-solid);
      color: var(--text);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.13);
    }}

    .visible-count {{
      align-self: stretch;
      min-height: 48px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      white-space: nowrap;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 0 14px;
      background: var(--panel-solid);
      color: var(--muted);
      font-weight: 800;
      box-shadow: var(--shadow-soft);
    }}

    .list-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      color: var(--muted);
      font-size: 0.9rem;
      font-weight: 750;
    }}

    .list-header span {{
      white-space: nowrap;
    }}

    .user-list {{
      margin: 0;
      gap: 8px;
    }}

    .user-card {{
      grid-template-columns: 34px 48px minmax(0, 1fr) auto;
      gap: 12px;
      min-height: 78px;
      padding: 13px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow-soft);
      backdrop-filter: blur(18px);
      transition: border-color 160ms ease, background 160ms ease, transform 160ms ease, opacity 160ms ease;
    }}

    .user-card:hover {{
      border-color: var(--border-strong);
      transform: translateY(-1px);
    }}

    .user-card[hidden] {{
      display: none;
    }}

    .user-card.done,
    .user-card.unavailable {{
      background: rgba(248, 248, 250, 0.84);
      opacity: 0.78;
    }}

    .done-check {{
      position: relative;
      width: 28px;
      height: 28px;
      display: grid;
      place-items: center;
      cursor: pointer;
    }}

    .done-check input {{
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
    }}

    .checkmark {{
      width: 28px;
      height: 28px;
      display: grid;
      place-items: center;
      border: 1.5px solid var(--border-strong);
      border-radius: 50%;
      background: var(--panel-solid);
      color: transparent;
      transition: all 160ms ease;
    }}

    .checkmark svg {{
      width: 18px;
      height: 18px;
      stroke-width: 2.5;
    }}

    .done-check input:checked + .checkmark {{
      border-color: var(--done);
      background: var(--done);
      color: #ffffff;
    }}

    .avatar {{
      width: 48px;
      height: 48px;
      display: grid;
      place-items: center;
      border: 1px solid hsla(var(--avatar-hue), 62%, 36%, 0.18);
      border-radius: 50%;
      background:
        linear-gradient(180deg, hsla(var(--avatar-hue), 85%, 94%, 1), hsla(var(--avatar-hue), 70%, 86%, 1));
      color: hsl(var(--avatar-hue), 58%, 30%);
      font-weight: 900;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78);
    }}

    .user-main {{
      gap: 6px;
    }}

    .username-row,
    .meta-row {{
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .user-main a {{
      min-width: 0;
      overflow-wrap: anywhere;
      color: var(--text);
      font-size: 1.04rem;
      font-weight: 850;
      text-decoration: none;
    }}

    .user-main a:hover,
    .user-main a:focus {{
      color: var(--accent);
      text-decoration: underline;
    }}

    .user-card.done .user-main a,
    .user-card.unavailable .user-main a {{
      color: var(--muted);
      text-decoration: line-through;
    }}

    .meta-row {{
      color: var(--muted);
      font-size: 0.88rem;
      font-weight: 650;
    }}

    .meta-dot {{
      width: 4px;
      height: 4px;
      flex: 0 0 auto;
      border-radius: 50%;
      background: var(--soft);
    }}

    .user-main .status-pill {{
      flex: 0 0 auto;
      min-height: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 0 9px;
      background: rgba(0, 113, 227, 0.1);
      color: var(--accent);
      font-size: 0.76rem;
      font-weight: 900;
    }}

    .user-card.done .user-main .status-pill {{
      background: rgba(29, 143, 95, 0.12);
      color: var(--done);
    }}

    .user-card.unavailable .user-main .status-pill {{
      background: rgba(191, 106, 2, 0.12);
      color: var(--warning);
    }}

    .actions {{
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }}

    .icon-button {{
      min-height: 40px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 0 12px;
      background: var(--panel-solid);
      color: var(--muted);
      font-weight: 850;
      text-decoration: none;
      cursor: pointer;
      white-space: nowrap;
      transition: transform 150ms ease, background 150ms ease, border-color 150ms ease, color 150ms ease;
    }}

    .icon-button svg {{
      width: 17px;
      height: 17px;
      stroke-width: 2;
    }}

    .icon-button:hover {{
      transform: translateY(-1px);
    }}

    .icon-button.primary {{
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
      box-shadow: 0 8px 18px rgba(0, 113, 227, 0.22);
    }}

    .icon-button.primary:hover,
    .icon-button.primary:focus {{
      background: var(--accent-strong);
      border-color: var(--accent-strong);
    }}

    .icon-button.ghost:hover,
    .icon-button.ghost:focus {{
      border-color: var(--accent);
      color: var(--accent);
    }}

    .user-card.unavailable .unavailable-button {{
      border-color: rgba(191, 106, 2, 0.3);
      background: rgba(255, 248, 230, 0.9);
      color: var(--warning);
    }}

    .empty {{
      padding: 28px;
      border: 1px dashed var(--border-strong);
      border-radius: var(--radius);
      background: var(--panel);
      color: var(--muted);
      font-weight: 750;
    }}

    .footnote {{
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 0.86rem;
      line-height: 1.45;
    }}

    @media (prefers-color-scheme: dark) {{
      :root {{
        color-scheme: dark;
        --bg: #101012;
        --bg-elevated: rgba(38, 38, 41, 0.72);
        --panel: rgba(30, 30, 32, 0.82);
        --panel-solid: #1f1f22;
        --text: #f5f5f7;
        --muted: #a1a1a6;
        --soft: #77777d;
        --border: rgba(255, 255, 255, 0.12);
        --border-strong: rgba(255, 255, 255, 0.22);
        --accent: #2997ff;
        --accent-strong: #0a84ff;
        --done: #32d583;
        --warning: #fdb022;
        --shadow: 0 18px 55px rgba(0, 0, 0, 0.38);
        --shadow-soft: 0 8px 24px rgba(0, 0, 0, 0.26);
      }}

      body {{
        background:
          linear-gradient(180deg, #1c1c1e 0%, var(--bg) 290px),
          var(--bg);
      }}

      .toolbar {{
        background: rgba(16, 16, 18, 0.82);
      }}

      .view-tabs {{
        background: rgba(45, 45, 48, 0.86);
      }}

      .progress-ring {{
        background:
          radial-gradient(circle at center, var(--panel-solid) 0 58%, transparent 59%),
          conic-gradient(var(--accent) var(--progress), rgba(255, 255, 255, 0.14) 0);
      }}

      .user-card.done,
      .user-card.unavailable {{
        background: rgba(33, 33, 36, 0.84);
      }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      *,
      *::before,
      *::after {{
        scroll-behavior: auto !important;
        transition-duration: 0.001ms !important;
        animation-duration: 0.001ms !important;
      }}
    }}

    @media (max-width: 940px) {{
      .hero-grid {{
        grid-template-columns: 1fr;
      }}

      .progress-panel {{
        grid-template-columns: auto 1fr;
        align-items: center;
      }}

      .progress-ring {{
        width: 150px;
      }}

      .stats {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}
    }}

    @media (max-width: 720px) {{
      main {{
        width: min(100% - 22px, 1180px);
        padding-top: 12px;
      }}

      .topbar {{
        align-items: flex-start;
        flex-direction: column;
      }}

      .hero-copy {{
        padding: 8px 0;
      }}

      .progress-panel {{
        grid-template-columns: 1fr;
      }}

      .stats {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .toolbar {{
        grid-template-columns: 1fr;
        padding-top: 10px;
      }}

      .filter-bar {{
        grid-template-columns: 1fr;
      }}

      .view-tabs {{
        overflow-x: auto;
        grid-template-columns: repeat(4, minmax(116px, 1fr));
      }}

      .user-card {{
        grid-template-columns: 34px 44px minmax(0, 1fr);
        align-items: start;
      }}

      .actions {{
        grid-column: 1 / -1;
        display: grid;
        grid-template-columns: 1fr 1fr;
      }}

      .icon-button {{
        width: 100%;
      }}

      .meta-row {{
        flex-wrap: wrap;
      }}
    }}

    @media (max-width: 430px) {{
      .stats {{
        grid-template-columns: 1fr;
      }}

      .user-card {{
        grid-template-columns: 32px 1fr;
      }}

      .avatar {{
        display: none;
      }}

      .user-main {{
        grid-column: 2;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="topbar">
        <div class="brand">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" focusable="false">
              <rect x="4" y="4" width="16" height="16" rx="5" />
              <circle cx="12" cy="12" r="4" />
              <path d="M17.2 6.8h.01" />
            </svg>
          </span>
          <span>Instagram follow audit</span>
        </div>
        <span class="generated">Gerado em {html.escape(generated_at)}</span>
      </div>

      <section class="hero-grid" aria-label="Resumo principal">
        <div class="hero-copy">
          <p class="eyebrow">Seguimentos por resolver</p>
          <h1>Nao me seguem de volta</h1>
          <p class="subtitle">Uma lista local, pesquisavel e marcada por estado, feita a partir dos dados exportados do Instagram.</p>
          <div class="source-strip" aria-label="Ficheiros usados">
            <span class="source-pill">following.json</span>
            <span class="source-pill">followers_*.json</span>
            <span class="source-pill">{skipped_unavailable_count} apagadas removidas</span>
          </div>
        </div>

        <aside class="progress-panel" aria-label="Progresso">
          <div class="progress-ring" aria-hidden="true">
            <div>
              <strong id="progressPercent">{initial_progress}%</strong>
              <span>feito</span>
            </div>
          </div>
          <p class="subtitle" id="progressText">Ainda tens {result_count} perfis pendentes.</p>
        </aside>
      </section>
    </header>

    <section class="stats" aria-label="Resumo">
      <div class="stat">
        <strong>{followers_count}</strong>
        <span>Seguidores</span>
      </div>
      <div class="stat">
        <strong>{following_count}</strong>
        <span>Pessoas que segues</span>
      </div>
      <div class="stat">
        <strong>{result_count}</strong>
        <span>Nao seguem de volta</span>
      </div>
      <div class="stat pending">
        <strong id="pendingCount">{result_count}</strong>
        <span>Pendentes</span>
      </div>
      <div class="stat done">
        <strong id="doneCount">0</strong>
        <span>Retirados</span>
      </div>
      <div class="stat unavailable">
        <strong id="unavailableCount">0</strong>
        <span>Indisponiveis</span>
      </div>
    </section>

    <section class="workbench" aria-label="Lista de perfis">
      <div class="toolbar">
        <label for="search">
          Pesquisar
          <span class="input-shell">
            <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
              <circle cx="9" cy="9" r="5.7" />
              <path d="m13.2 13.2 3.4 3.4" />
            </svg>
            <input id="search" type="search" placeholder="username" autocomplete="off">
          </span>
        </label>

        <label for="sort">
          Ordenar
          <select id="sort">
            <option value="username">A-Z</option>
            <option value="recent">Mais recentes</option>
            <option value="oldest">Mais antigos</option>
          </select>
        </label>

        <div class="filter-bar">
          <div class="view-tabs" role="tablist" aria-label="Filtro de estado">
            <button class="view-tab active" type="button" role="tab" aria-selected="true" data-filter="pending">
              <span>Pendentes</span>
              <strong id="filterPendingCount">{result_count}</strong>
            </button>
            <button class="view-tab" type="button" role="tab" aria-selected="false" data-filter="all">
              <span>Todos</span>
              <strong id="filterAllCount">{result_count}</strong>
            </button>
            <button class="view-tab" type="button" role="tab" aria-selected="false" data-filter="done">
              <span>Retirados</span>
              <strong id="filterDoneCount">0</strong>
            </button>
            <button class="view-tab" type="button" role="tab" aria-selected="false" data-filter="unavailable">
              <span>Indisponiveis</span>
              <strong id="filterUnavailableCount">0</strong>
            </button>
          </div>
          <div class="visible-count" aria-live="polite"><span id="visibleCount">{result_count}</span> visiveis</div>
        </div>
      </div>

      <div class="list-header">
        <span>Perfil</span>
        <span>Estado guardado no Safari</span>
      </div>

      <ol class="user-list" id="userList">
        {rows}
      </ol>

      <p class="empty" id="emptyState">Nao ha resultados para essa pesquisa ou filtro.</p>
      <p class="footnote">Contas apagadas removidas automaticamente antes de gerar a pagina: {skipped_unavailable_count}.</p>
    </section>
  </main>

  <script>
    const storageKey = "naoMeSeguemEstados:v2";
    const search = document.getElementById("search");
    const sortSelect = document.getElementById("sort");
    const list = document.getElementById("userList");
    const cards = Array.from(document.querySelectorAll(".user-card"));
    const tabs = Array.from(document.querySelectorAll(".view-tab"));
    const visibleCount = document.getElementById("visibleCount");
    const pendingCount = document.getElementById("pendingCount");
    const doneCount = document.getElementById("doneCount");
    const unavailableCount = document.getElementById("unavailableCount");
    const filterPendingCount = document.getElementById("filterPendingCount");
    const filterAllCount = document.getElementById("filterAllCount");
    const filterDoneCount = document.getElementById("filterDoneCount");
    const filterUnavailableCount = document.getElementById("filterUnavailableCount");
    const progressPercent = document.getElementById("progressPercent");
    const progressText = document.getElementById("progressText");
    const emptyState = document.getElementById("emptyState");
    const root = document.documentElement;
    const totalCount = cards.length;
    let activeFilter = "pending";
    let savedState = readState();

    function readState() {{
      try {{
        return JSON.parse(localStorage.getItem(storageKey)) || {{}};
      }} catch {{
        return {{}};
      }}
    }}

    function writeState(state) {{
      try {{
        localStorage.setItem(storageKey, JSON.stringify(state));
      }} catch {{
        return;
      }}
    }}

    function stateFor(card) {{
      return savedState[card.dataset.username] || "pending";
    }}

    function setCardState(card, nextState) {{
      const username = card.dataset.username;

      if (nextState === "pending") {{
        delete savedState[username];
      }} else {{
        savedState[username] = nextState;
      }}

      writeState(savedState);
      applyCardState(card, nextState);
      filterUsers();
    }}

    function applyCardState(card, cardState) {{
      card.classList.toggle("done", cardState === "done");
      card.classList.toggle("unavailable", cardState === "unavailable");

      const doneCheckbox = card.querySelector('[data-action="done"]');
      const unavailableButton = card.querySelector('[data-action="unavailable"]');
      const statusPill = card.querySelector(".status-pill");

      doneCheckbox.checked = cardState === "done";
      unavailableButton.querySelector("span").textContent = cardState === "unavailable" ? "Pendente" : "Erro";
      unavailableButton.setAttribute("aria-pressed", cardState === "unavailable");

      if (cardState === "done") {{
        statusPill.textContent = "Retirado";
      }} else if (cardState === "unavailable") {{
        statusPill.textContent = "Indisponivel";
      }} else {{
        statusPill.textContent = "Pendente";
      }}
    }}

    function hydrateState() {{
      for (const card of cards) {{
        applyCardState(card, stateFor(card));
      }}
    }}

    function counts() {{
      let pending = 0;
      let done = 0;
      let unavailable = 0;

      for (const card of cards) {{
        const cardState = stateFor(card);
        if (cardState === "done") {{
          done += 1;
        }} else if (cardState === "unavailable") {{
          unavailable += 1;
        }} else {{
          pending += 1;
        }}
      }}

      return {{ pending, done, unavailable }};
    }}

    function updateSummary() {{
      const current = counts();
      const finished = current.done + current.unavailable;
      const progress = totalCount === 0 ? 100 : Math.round((finished / totalCount) * 100);

      pendingCount.textContent = current.pending;
      doneCount.textContent = current.done;
      unavailableCount.textContent = current.unavailable;
      filterPendingCount.textContent = current.pending;
      filterAllCount.textContent = totalCount;
      filterDoneCount.textContent = current.done;
      filterUnavailableCount.textContent = current.unavailable;
      progressPercent.textContent = progress + "%";
      progressText.textContent = current.pending === 1
        ? "Ainda tens 1 perfil pendente."
        : "Ainda tens " + current.pending + " perfis pendentes.";
      root.style.setProperty("--progress", progress + "%");
    }}

    function sortUsers() {{
      const mode = sortSelect.value;
      const ordered = cards.slice().sort((a, b) => {{
        if (mode === "recent") {{
          return Number(b.dataset.timestamp) - Number(a.dataset.timestamp);
        }}

        if (mode === "oldest") {{
          return Number(a.dataset.timestamp) - Number(b.dataset.timestamp);
        }}

        return a.dataset.username.localeCompare(b.dataset.username);
      }});

      for (const card of ordered) {{
        list.appendChild(card);
      }}
    }}

    function filterUsers() {{
      const query = search.value.trim().toLowerCase();
      let visible = 0;

      for (const card of cards) {{
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
        if (isVisible) visible += 1;
      }}

      visibleCount.textContent = visible;
      emptyState.style.display = visible === 0 ? "block" : "none";
      updateSummary();
    }}

    for (const card of cards) {{
      card.addEventListener("click", (event) => {{
        const unavailableButton = event.target.closest("button[data-action='unavailable']");
        if (!unavailableButton) return;

        const nextState = stateFor(card) === "unavailable" ? "pending" : "unavailable";
        setCardState(card, nextState);
      }});

      card.querySelector("[data-action='done']").addEventListener("change", (event) => {{
        setCardState(card, event.target.checked ? "done" : "pending");
      }});
    }}

    for (const tab of tabs) {{
      tab.addEventListener("click", () => {{
        activeFilter = tab.dataset.filter;
        tabs.forEach((item) => {{
          const isActive = item === tab;
          item.classList.toggle("active", isActive);
          item.setAttribute("aria-selected", isActive);
        }});
        filterUsers();
      }});
    }}

    search.addEventListener("input", filterUsers);
    sortSelect.addEventListener("change", () => {{
      sortUsers();
      filterUsers();
    }});

    hydrateState();
    sortUsers();
    filterUsers();
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Descobre quem nao te segue de volta no Instagram.")
    parser.add_argument(
        "--path",
        type=Path,
        default=DATA_PATH,
        help="Pasta followers_and_following extraida do Instagram.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_HTML,
        help="Ficheiro HTML de saida.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = args.path.expanduser()
    output_html = args.output.expanduser()

    if not data_path.exists():
        raise SystemExit(f"Erro: a pasta nao existe: {data_path}")

    if not (data_path / "following.json").exists():
        raise SystemExit(f"Erro: nao encontrei following.json em: {data_path}")

    followers = load_followers(data_path)
    following = load_following(data_path)
    raw_not_following_back_usernames = sorted(set(following) - set(followers))
    not_following_back_usernames = [
        username for username in raw_not_following_back_usernames if not is_probably_unavailable(username)
    ]
    skipped_unavailable_count = len(raw_not_following_back_usernames) - len(not_following_back_usernames)
    not_following_back = [following[username] for username in not_following_back_usernames]

    output_html.write_text(
        build_html(
            followers_count=len(followers),
            following_count=len(following),
            not_following_back=not_following_back,
            skipped_unavailable_count=skipped_unavailable_count,
        ),
        encoding="utf-8",
    )

    print(f"Total followers (quem te segue): {len(followers)}")
    print(f"Total following (quem TU segues): {len(following)}")
    print(f"Nao te seguem de volta: {len(not_following_back)}")
    print(f"Contas apagadas removidas da lista: {skipped_unavailable_count}")
    print(f"Pagina HTML criada em: {output_html}")

    print("\n==============================")
    print("NAO ME SEGUEM DE VOLTA")
    print("==============================")
    for user in not_following_back:
        print(" -", user.username)

    print("\nFeito!")


if __name__ == "__main__":
    main()
