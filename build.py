#!/usr/bin/env python3
"""Generate the static site in ./site from the markdown posts in ./content/blog.

Usage:  pip install markdown && python3 build.py

Each post lives at content/blog/<slug>/index.md with front matter like:

    +++
    title = "My post"
    date = "2026-11-13"
    +++

Add `private = true` or `draft = true` to keep a post off the site.
Hand-written assets (site/css, site/js, favicon, CNAME, notes/) are never touched.
"""
import html
import json
import math
import re
import zlib
from datetime import datetime, timezone
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "content" / "blog"
OUT = ROOT / "site"

SITE = {
    "title": "valstechblog",
    "url": "https://valstech.blog",
    "tagline": "tech, media, culture",
    "twitter": "https://x.com/valstechblog",
    "github": "https://github.com/valstechblog",
}

GISCUS = """<script src="https://giscus.app/client.js"
    data-repo="valstechblog/valstechblog.github.io"
    data-repo-id="R_kgDOPJSioQ"
    data-category="General"
    data-category-id="DIC_kwDOPJSioc4DFdyu"
    data-mapping="pathname"
    data-strict="0"
    data-reactions-enabled="1"
    data-emit-metadata="0"
    data-input-position="bottom"
    data-theme="light"
    data-lang="en"
    crossorigin="anonymous"
    async></script>"""

e = html.escape


# ---------------------------------------------------------------- posts

def parse_front_matter(text):
    m = re.match(r"^(\+\+\+|---)\s*\n(.*?)\n\1\s*\n", text, re.S)
    meta = {}
    if not m:
        return meta, text
    for line in m.group(2).splitlines():
        kv = re.match(r"^\s*([A-Za-z_]+)\s*[=:]\s*(.+?)\s*$", line)
        if not kv:
            continue
        key, val = kv.groups()
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1].replace('\\"', '"')
        elif val in ("true", "false"):
            val = val == "true"
        meta[key] = val
    return meta, text[m.end():]


def parse_date(val):
    val = str(val).strip()
    for candidate in (val, val[:19], val[:10]):
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            continue
    raise ValueError(f"can't read date {val!r}")


def nice_date(d):
    return f"{d:%b} {d.day}, {d.year}"


def quest_length(words):
    if words < 1500:
        return "Short"
    if words < 2200:
        return "Medium"
    if words < 3000:
        return "Long"
    return "Very long"


def render_markdown(body, slugs):
    # Substack exports escape blockquote markers as "\>"; turn them back into quotes.
    body = re.sub(r"(?m)^\\>", ">", body)
    # Old Substack links to our own posts -> new URLs.
    def relink(m):
        slug = m.group(1)
        return f"/blog/{slug}/" if slug in slugs else m.group(0)
    body = re.sub(r"https?://(?:www\.)?valstech\.blog/p/([a-z0-9-]+)/?", relink, body)

    md = markdown.Markdown(extensions=["extra", "sane_lists", "toc"])
    out = md.convert(body)
    out = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', out)
    out = out.replace("<img ", '<img loading="lazy" ')
    return out


def load_posts():
    posts = []
    raw = []
    for path in sorted(SRC.glob("*/index.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        if meta.get("private") is True or meta.get("draft") is True:
            continue
        raw.append((path.parent.name, meta, body))
    slugs = {slug for slug, _, _ in raw}
    for slug, meta, body in raw:
        content = render_markdown(body, slugs)
        text = re.sub(r"<[^>]+>", " ", content)
        words = len(text.split())
        paras = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m)).strip()
                 for m in re.findall(r"<p>(.*?)</p>", content, re.S)]
        summary = next((t for t in paras if len(t) >= 80), paras[0] if paras else "")
        if len(summary) > 220:
            summary = summary[:217].rsplit(" ", 1)[0] + "…"
        d = parse_date(meta.get("date", "1970-01-01"))
        posts.append({
            "slug": slug,
            "title": meta.get("title", slug.replace("-", " ").title()),
            "date": d,
            "url": f"/blog/{slug}/",
            "content": content,
            "words": words,
            "minutes": max(1, math.ceil(words / 230)),
            "length": quest_length(words),
            "summary": html.unescape(summary),
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


# ---------------------------------------------------------------- icons

def px(rects, size=16):
    """Tiny pixel-art icon from (x, y, w, h, colour) rects."""
    body = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>' for x, y, w, h, c in rects)
    return f'<svg class="px" viewBox="0 0 {size} {size}" aria-hidden="true" shape-rendering="crispEdges">{body}</svg>'

ICON_QUESTS = px([(3, 2, 10, 12, "#e4d19c"), (2, 1, 12, 2, "#9c7a3c"), (2, 13, 12, 2, "#9c7a3c"),
                  (1, 1, 1, 2, "#5a4220"), (14, 1, 1, 2, "#5a4220"), (1, 13, 1, 2, "#5a4220"), (14, 13, 1, 2, "#5a4220"),
                  (5, 5, 6, 1, "#6b4a1e"), (5, 7, 6, 1, "#6b4a1e"), (5, 9, 6, 1, "#6b4a1e"), (5, 11, 3, 1, "#6b4a1e")])
ICON_HOME = px([(7, 1, 2, 1, "#8b2a1a"), (5, 2, 6, 1, "#8b2a1a"), (3, 3, 10, 1, "#8b2a1a"), (1, 4, 14, 2, "#a8341f"),
                (3, 6, 10, 8, "#cdb48a"), (7, 9, 3, 5, "#5a3a1a"), (4, 8, 2, 2, "#6aa0d8"), (1, 14, 14, 1, "#1a1410")])
ICON_X = px([(2, 2, 2, 2, "#f0f0f0"), (4, 4, 2, 2, "#f0f0f0"), (6, 6, 4, 4, "#f0f0f0"), (10, 10, 2, 2, "#f0f0f0"),
             (12, 12, 2, 2, "#f0f0f0"), (12, 2, 2, 2, "#f0f0f0"), (10, 4, 2, 2, "#f0f0f0"), (4, 10, 2, 2, "#f0f0f0"),
             (2, 12, 2, 2, "#f0f0f0")])
ICON_GITHUB = px([(4, 0, 8, 1, "#f0f0f0"), (2, 1, 12, 1, "#f0f0f0"), (1, 2, 2, 1, "#f0f0f0"), (4, 2, 8, 1, "#f0f0f0"), (13, 2, 2, 1, "#f0f0f0"), (1, 3, 2, 1, "#f0f0f0"), (5, 3, 6, 1, "#f0f0f0"), (13, 3, 2, 1, "#f0f0f0"), (0, 4, 2, 1, "#f0f0f0"), (14, 4, 2, 1, "#f0f0f0"), (0, 5, 2, 1, "#f0f0f0"), (14, 5, 2, 1, "#f0f0f0"), (0, 6, 2, 1, "#f0f0f0"), (14, 6, 2, 1, "#f0f0f0"), (0, 7, 2, 1, "#f0f0f0"), (14, 7, 2, 1, "#f0f0f0"), (0, 8, 2, 1, "#f0f0f0"), (14, 8, 2, 1, "#f0f0f0"), (0, 9, 3, 1, "#f0f0f0"), (13, 9, 3, 1, "#f0f0f0"), (1, 10, 3, 1, "#f0f0f0"), (12, 10, 3, 1, "#f0f0f0"), (1, 11, 1, 1, "#f0f0f0"), (3, 11, 2, 1, "#f0f0f0"), (11, 11, 4, 1, "#f0f0f0"), (1, 12, 2, 1, "#f0f0f0"), (4, 12, 1, 1, "#f0f0f0"), (11, 12, 4, 1, "#f0f0f0"), (2, 13, 3, 1, "#f0f0f0"), (11, 13, 3, 1, "#f0f0f0"), (3, 14, 2, 1, "#f0f0f0"), (11, 14, 2, 1, "#f0f0f0"), (5, 15, 6, 1, "#f0f0f0")])
ICON_FILM = px([(1, 6, 14, 9, "#2b2b2b"), (1, 6, 14, 1, "#555"), (3, 8, 10, 1, "#777"), (3, 10, 10, 1, "#777"),
                (3, 12, 10, 1, "#777"), (1, 2, 14, 3, "#f2f2f2"), (1, 2, 1, 3, "#1a1410"), (4, 2, 2, 3, "#1a1410"),
                (8, 2, 2, 3, "#1a1410"), (12, 2, 2, 3, "#1a1410"), (1, 5, 14, 1, "#1a1410"), (0, 2, 1, 13, "#1a1410"),
                (15, 2, 1, 13, "#1a1410"), (0, 15, 16, 1, "#1a1410")])
ICON_MUSIC = px([(4, 0, 8, 1, "#1a1410"), (2, 1, 12, 1, "#1a1410"), (1, 2, 4, 1, "#1a1410"), (5, 2, 5, 1, "#4d4d4d"), (10, 2, 2, 1, "#1a1410"), (12, 2, 1, 1, "#9a9a9a"), (13, 2, 2, 1, "#1a1410"), (1, 3, 2, 1, "#1a1410"), (3, 3, 2, 1, "#4d4d4d"), (5, 3, 6, 1, "#1a1410"), (11, 3, 1, 1, "#4d4d4d"), (12, 3, 1, 1, "#9a9a9a"), (13, 3, 2, 1, "#1a1410"), (0, 4, 3, 1, "#1a1410"), (3, 4, 1, 1, "#4d4d4d"), (4, 4, 8, 1, "#1a1410"), (12, 4, 1, 1, "#4d4d4d"), (13, 4, 3, 1, "#1a1410"), (0, 5, 2, 1, "#1a1410"), (2, 5, 1, 1, "#4d4d4d"), (3, 5, 3, 1, "#1a1410"), (6, 5, 4, 1, "#c4271a"), (10, 5, 3, 1, "#1a1410"), (13, 5, 1, 1, "#4d4d4d"), (14, 5, 2, 1, "#1a1410"), (0, 6, 2, 1, "#1a1410"), (2, 6, 1, 1, "#4d4d4d"), (3, 6, 2, 1, "#1a1410"), (5, 6, 6, 1, "#c4271a"), (11, 6, 2, 1, "#1a1410"), (13, 6, 1, 1, "#4d4d4d"), (14, 6, 2, 1, "#1a1410"), (0, 7, 2, 1, "#1a1410"), (2, 7, 1, 1, "#4d4d4d"), (3, 7, 2, 1, "#1a1410"), (5, 7, 2, 1, "#c4271a"), (7, 7, 2, 1, "#f0e6cf"), (9, 7, 2, 1, "#c4271a"), (11, 7, 2, 1, "#1a1410"), (13, 7, 1, 1, "#4d4d4d"), (14, 7, 2, 1, "#1a1410"), (0, 8, 2, 1, "#1a1410"), (2, 8, 1, 1, "#4d4d4d"), (3, 8, 2, 1, "#1a1410"), (5, 8, 2, 1, "#c4271a"), (7, 8, 2, 1, "#f0e6cf"), (9, 8, 2, 1, "#c4271a"), (11, 8, 2, 1, "#1a1410"), (13, 8, 1, 1, "#4d4d4d"), (14, 8, 2, 1, "#1a1410"), (0, 9, 2, 1, "#1a1410"), (2, 9, 1, 1, "#4d4d4d"), (3, 9, 2, 1, "#1a1410"), (5, 9, 6, 1, "#c4271a"), (11, 9, 2, 1, "#1a1410"), (13, 9, 1, 1, "#4d4d4d"), (14, 9, 2, 1, "#1a1410"), (0, 10, 2, 1, "#1a1410"), (2, 10, 1, 1, "#4d4d4d"), (3, 10, 3, 1, "#1a1410"), (6, 10, 4, 1, "#c4271a"), (10, 10, 3, 1, "#1a1410"), (13, 10, 1, 1, "#4d4d4d"), (14, 10, 2, 1, "#1a1410"), (0, 11, 3, 1, "#1a1410"), (3, 11, 1, 1, "#4d4d4d"), (4, 11, 8, 1, "#1a1410"), (12, 11, 1, 1, "#4d4d4d"), (13, 11, 3, 1, "#1a1410"), (1, 12, 2, 1, "#1a1410"), (3, 12, 1, 1, "#9a9a9a"), (4, 12, 1, 1, "#4d4d4d"), (5, 12, 6, 1, "#1a1410"), (11, 12, 2, 1, "#4d4d4d"), (13, 12, 2, 1, "#1a1410"), (1, 13, 2, 1, "#1a1410"), (3, 13, 1, 1, "#9a9a9a"), (4, 13, 1, 1, "#1a1410"), (5, 13, 5, 1, "#4d4d4d"), (10, 13, 5, 1, "#1a1410"), (2, 14, 12, 1, "#1a1410"), (4, 15, 8, 1, "#1a1410")])
ICON_BOOKS = px([(2, 2, 11, 12, "#7b2617"), (3, 3, 9, 10, "#a8341f"), (12, 3, 2, 12, "#efe6cf"),
                 (3, 14, 11, 1, "#efe6cf"), (2, 14, 1, 1, "#4a160c"), (5, 5, 5, 1, "#e3b341"), (5, 7, 5, 1, "#e3b341"),
                 (1, 2, 1, 13, "#4a160c"), (14, 3, 1, 12, "#4a160c"), (2, 15, 13, 1, "#1a1410")])
ICON_INVENTORY = px([(6, 1, 4, 2, "#5a3a1a"), (5, 3, 6, 1, "#3d2610"), (4, 4, 8, 1, "#8a5a2b"), (3, 5, 10, 1, "#8a5a2b"),
                     (2, 6, 12, 7, "#9c6a33"), (3, 13, 10, 1, "#9c6a33"), (4, 14, 8, 1, "#5a3a1a"), (4, 7, 2, 4, "#b8823f"),
                     (1, 7, 1, 6, "#3d2610"), (14, 7, 1, 6, "#3d2610")])
ICON_QUILL = px([(11, 1, 3, 1, "#f2efe6"), (9, 2, 5, 1, "#f2efe6"), (8, 3, 5, 1, "#dcd6c8"), (7, 4, 5, 1, "#f2efe6"),
                 (6, 5, 5, 1, "#dcd6c8"), (5, 6, 5, 1, "#f2efe6"), (5, 7, 4, 1, "#dcd6c8"), (4, 8, 4, 1, "#f2efe6"),
                 (4, 9, 3, 1, "#dcd6c8"), (3, 10, 2, 1, "#6b4a1e"), (2, 11, 2, 1, "#6b4a1e"), (1, 12, 2, 2, "#1a1410"),
                 (8, 13, 7, 1, "#1a1410"), (5, 14, 4, 1, "#1a1410")])



# Inventory tab items: content/inventory/items.txt
STASH_KINDS = {
    "film": ("Watch", ICON_FILM), "films": ("Watch", ICON_FILM), "movie": ("Watch", ICON_FILM), "tv": ("Watch", ICON_FILM),
    "music": ("Listen to", ICON_MUSIC), "album": ("Listen to", ICON_MUSIC), "song": ("Listen to", ICON_MUSIC),
    "book": ("Read", ICON_BOOKS), "books": ("Read", ICON_BOOKS),
}


_stash = None


def load_stash():
    global _stash
    if _stash is not None:
        return _stash
    path = ROOT / "content" / "inventory" / "items.txt"
    out = _stash = []
    if not path.exists():
        return out
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split("|")] + ["", ""]
        kind, title, link = parts[0].lower(), parts[1], parts[2]
        if not title or not link:
            print(f"  items.txt line {n}: skipped (needs at least: category | title | link)")
            continue
        verb, icon = STASH_KINDS.get(kind, ("Use", ICON_INVENTORY))
        out.append({"title": title, "url": link,
                    "verb": verb, "icon": icon, "external": bool(re.match(r"https?://", link))})
    return out

# ---------------------------------------------------------------- page chrome

def sidebar(posts, items, tab="quests"):
    quests = "".join(
        f'<li><a href="{p["url"]}" data-quest="{p["slug"]}">{e(p["title"])}</a></li>' for p in posts
    )
    stash = load_stash()
    slot_html = []
    for i in stash:
        new_tab = ' target="_blank" rel="noopener"' if i["external"] else ""
        slot_html.append(
            '<li><a class="item" href="%s"%s data-item data-verb="%s" data-name="%s" data-examine="%s">%s<span class="item-name">%s</span></a></li>'
            % (e(i["url"]), new_tab, i["verb"], e(i["title"]), e(i["title"]), i["icon"], e(i["title"])))
    slots = "".join(slot_html)

    def tab_btn(name, label, icon):
        on = name == tab
        return (f'<button class="tab{" active" if on else ""}" role="tab" aria-selected="{"true" if on else "false"}" '
                f'aria-controls="panel-{name}" data-tab="{name}" title="{label}">{icon}</button>')

    return f"""
  <aside class="sidepanel stone" aria-label="Side panel">
    <div class="hud">
      <div class="orbs">
        <a class="orb orb-hp" href="/blog/"><span class="orb-val">{len(posts)}</span><span class="orb-ball"></span></a>
        <div class="orb orb-pray" title="Quest points: posts you've finished reading"><span class="orb-val" data-qp>0</span><span class="orb-ball"></span></div>
        <div class="orb orb-run" title="Run energy: drains as you read"><span class="orb-val" id="run-val">100</span><span class="orb-ball"></span></div>
      </div>
      <nav class="minimap" aria-label="World map">
        <span class="mm-land"></span>
        <a class="mm-you" href="/" data-verb="Walk" data-name="home" aria-label="Home"></a>
      </nav>
      <a class="compass" href="/" title="Home" data-verb="Walk" data-name="home" aria-label="Home">N</a>
    </div>
    <div class="tabs" role="tablist" aria-label="Side panel tabs">
      {tab_btn("quests", "Quest List", ICON_QUESTS)}
      {tab_btn("inventory", "Inventory", ICON_INVENTORY)}
    </div>
    <div class="tab-body">
      <section class="panel" id="panel-quests" data-panel="quests" role="tabpanel"{"" if tab == "quests" else " hidden"}>
        <h2 class="panel-title">Quest List</h2>
        <p class="panel-sub">Quest Points: <span data-qp>0</span>/{len(posts)}</p>
        <ol class="quest-list">{quests}</ol>
        <p class="legend"><span class="q-new">Not started</span> <span class="q-prog">In progress</span> <span class="q-done">Completed</span></p>
      </section>
      <section class="panel" id="panel-inventory" data-panel="inventory" role="tabpanel"{"" if tab == "inventory" else " hidden"}>
        <h2 class="panel-title">Inventory</h2>
        <ul class="inventory">{slots}</ul>
      </section>
    </div>
    <nav class="tabs tabs-bottom" aria-label="Links">
      <a class="tab" href="/" title="Home">{ICON_HOME}</a>
      <a class="tab" href="/blog/" title="All quests">{ICON_QUESTS}</a>
      <a class="tab" href="{SITE['twitter']}" target="_blank" rel="noopener" title="valstechblog on X">{ICON_X}</a>
      <a class="tab" href="{SITE['github']}" target="_blank" rel="noopener" title="valstechblog on GitHub">{ICON_GITHUB}</a>
    </nav>
  </aside>"""


def page(posts, *, title, body, path, description="", slug="", extra_head="", items=(), tab="quests"):
    full_title = SITE["title"] if path == "/" else f"{title} | {SITE['title']}"
    desc = description or SITE["tagline"]
    data = json.dumps({
        "posts": [{"slug": p["slug"], "title": p["title"], "url": p["url"], "date": nice_date(p["date"]),
                   "words": p["words"], "length": p["length"]} for p in posts],
    }).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE['url']}{path}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="{'article' if slug else 'website'}">
<meta property="og:url" content="{SITE['url']}{path}">
<meta property="og:site_name" content="{SITE['title']}">
<meta name="twitter:card" content="summary">
<meta name="twitter:site" content="@valstechblog">
<meta name="theme-color" content="#3e3529">
<link rel="icon" href="/favicon.png">
<link rel="preload" href="/fonts/pixelify-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/crimson-pro-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/css/osrs.css">
{extra_head}</head>
<body data-slug="{slug}">
<a class="skip" href="#main">Skip to content</a>
<div class="client">
  <main class="viewport stone" id="main">
    <div class="mouseover" id="mouseover" aria-hidden="true">Walk here</div>
    <div class="xp-drops" id="xp-drops" aria-hidden="true"></div>
    <div class="world" id="world">
      <header class="banner">
        <a class="logo" href="/">{SITE['title']}</a>
        <p class="tagline">{SITE['tagline']}</p>
      </header>
{body}
    </div>
  </main>
{sidebar(posts, items, tab)}
</div>

<div class="ctx-menu" id="ctx-menu" hidden role="menu"></div>

<div class="qc" id="quest-complete" hidden role="dialog" aria-modal="true" aria-labelledby="qc-title">
  <div class="qc-scroll">
    <p class="qc-congrats">Congratulations!</p>
    <h2 id="qc-title">You have completed<br><span id="qc-name"></span>!</h2>
    <div class="qc-body">
      <div class="qc-icon">{ICON_QUILL}</div>
      <div class="qc-rewards">
        <p>You are awarded:</p>
        <ul>
          <li>1 Quest Point</li>
          <li><span id="qc-xp">0</span> Reading XP</li>
          <li>Something to think about</li>
        </ul>
      </div>
    </div>
    <p class="qc-qp">Quest Points: <span data-qp>0</span></p>
    <button class="btn" id="qc-close" type="button">Close</button>
  </div>
</div>

<script type="application/json" id="site-data">{data}</script>
<script src="/js/osrs.js" defer></script>
</body>
</html>
"""


def quest_entries(posts):
    rows = []
    for p in posts:
        rows.append(f"""
        <li class="quest-entry">
          <a class="quest-title" href="{p['url']}" data-quest="{p['slug']}">{e(p['title'])}</a>
          <p class="quest-meta"><span>Published: <b>{nice_date(p['date'])}</b></span><span>Length: <b>{p['length']}</b></span><span><b>{p['minutes']}</b> min</span></p>
          <p class="quest-summary">{e(p['summary'])}</p>
        </li>""")
    return "".join(rows)


def write(rel, text):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    posts = load_posts()
    items = ()

    # Home: content/home.md (title in front matter, body shown above the quest list)
    home_meta, home_body = parse_front_matter((ROOT / "content" / "home.md").read_text(encoding="utf-8")) \
        if (ROOT / "content" / "home.md").exists() else ({}, "")
    home_title = home_meta.get("title", f"Welcome to {SITE['title']}")
    home_list_title = home_meta.get("list_title", "Latest quests")
    home_intro = render_markdown(home_body, {p["slug"] for p in posts}) if home_body.strip() else ""
    home = f"""
      <section class="scroll">
        <h2 class="section-title">{e(home_list_title)}</h2>
        <ol class="quest-log">{quest_entries(posts[:10])}</ol>
        <p class="more"><a href="/blog/">View the full quest journal &rarr;</a></p>
      </section>"""
    write("index.html", page(posts, items=items, title=SITE["title"], body=home, path="/"))

    # Blog index
    blog = f"""
      <section class="scroll">
        <h1 class="scroll-title">Quest Journal</h1>
        <p class="scroll-lede">Completed quests turn green in your Quest List.</p>
        <div class="divider" aria-hidden="true"></div>
        <ol class="quest-log">{quest_entries(posts)}</ol>
      </section>"""
    write("blog/index.html", page(posts, items=items, title="Quest Journal", body=blog, path="/blog/"))

    # Posts
    for p in posts:
        body = f"""
      <article class="scroll post">
        <p class="kicker">Quest journal</p>
        <h1 class="scroll-title">{e(p['title'])}</h1>
        <p class="post-meta"><span>Published <time datetime="{p['date']:%Y-%m-%d}">{nice_date(p['date'])}</time></span><span>Length: {p['length']}</span><span>{p['minutes']} min read</span></p>
        <div class="divider" aria-hidden="true"></div>
        <div class="prose">
{p['content']}
        </div>
        <div class="fin" id="quest-end" aria-hidden="true">~ quest complete ~</div>
        <div class="comments">
{GISCUS}
        </div>
      </article>"""
        write(f"blog/{p['slug']}/index.html",
              page(posts, items=items, title=p["title"], body=body, path=p["url"], description=p["summary"], slug=p["slug"]))
        # Old Substack-style URL -> new URL
        write(f"p/{p['slug']}/index.html",
              f'<!DOCTYPE html><meta charset="utf-8"><title>Redirecting…</title>'
              f'<link rel="canonical" href="{SITE["url"]}{p["url"]}">'
              f'<meta http-equiv="refresh" content="0; url={p["url"]}">'
              f'<a href="{p["url"]}">{e(p["title"])}</a>\n')

    # 404
    nf = """
      <section class="scroll">
        <h1 class="scroll-title">Nothing interesting happens.</h1>
        <p class="scroll-lede">You can't reach that. The page you were looking for isn't here.</p>
        <p class="more"><a href="/">Teleport home &rarr;</a></p>
      </section>"""
    redirect = """<script>(function(){var m=location.pathname.match(/^\\/p\\/([a-z0-9-]+)/);if(m){location.replace('/blog/'+m[1]+'/');}})();</script>
"""
    write("404.html", page(posts, items=items, title="Page not found", body=nf, path="/404.html", extra_head=redirect))

    # Sitemap
    urls = ["/", "/blog/"] + [p["url"] for p in posts]
    sitemap = "\n".join(f"  <url><loc>{SITE['url']}{u}</loc></url>" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sitemap}\n</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n")

    print(f"Built {len(posts)} posts into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
