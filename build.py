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
    "tagline": "Essays on technology, media and culture",
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
ICON_STATS = px([(2, 9, 3, 5, "#d33a2c"), (6, 5, 3, 9, "#e8c31c"), (10, 2, 3, 12, "#3fae2a"),
                 (1, 14, 14, 1, "#1a1410")])
ICON_FRIENDS = px([(4, 2, 8, 1, "#1a1410"), (3, 3, 10, 10, "#e8c31c"), (2, 4, 1, 8, "#1a1410"), (13, 4, 1, 8, "#1a1410"),
                   (4, 13, 8, 1, "#1a1410"), (3, 3, 1, 1, "#1a1410"), (12, 3, 1, 1, "#1a1410"), (3, 12, 1, 1, "#1a1410"),
                   (12, 12, 1, 1, "#1a1410"), (5, 6, 2, 2, "#1a1410"), (9, 6, 2, 2, "#1a1410"), (5, 10, 6, 1, "#1a1410"),
                   (4, 9, 1, 1, "#1a1410"), (11, 9, 1, 1, "#1a1410")])
ICON_HOME = px([(7, 1, 2, 1, "#8b2a1a"), (5, 2, 6, 1, "#8b2a1a"), (3, 3, 10, 1, "#8b2a1a"), (1, 4, 14, 2, "#a8341f"),
                (3, 6, 10, 8, "#cdb48a"), (7, 9, 3, 5, "#5a3a1a"), (4, 8, 2, 2, "#6aa0d8"), (1, 14, 14, 1, "#1a1410")])
ICON_X = px([(2, 2, 2, 2, "#f0f0f0"), (4, 4, 2, 2, "#f0f0f0"), (6, 6, 4, 4, "#f0f0f0"), (10, 10, 2, 2, "#f0f0f0"),
             (12, 12, 2, 2, "#f0f0f0"), (12, 2, 2, 2, "#f0f0f0"), (10, 4, 2, 2, "#f0f0f0"), (4, 10, 2, 2, "#f0f0f0"),
             (2, 12, 2, 2, "#f0f0f0")])
ICON_CAL = px([(2, 3, 12, 11, "#e9e1cc"), (2, 3, 12, 3, "#c4271a"), (4, 1, 2, 4, "#1a1410"), (10, 1, 2, 4, "#1a1410"),
                (4, 8, 2, 2, "#5a4126"), (7, 8, 2, 2, "#5a4126"), (10, 8, 2, 2, "#5a4126"), (4, 11, 2, 2, "#5a4126"),
                (7, 11, 2, 2, "#c4271a"), (1, 14, 14, 1, "#1a1410")])
ICON_QUILL = px([(11, 1, 3, 1, "#f2efe6"), (9, 2, 5, 1, "#f2efe6"), (8, 3, 5, 1, "#dcd6c8"), (7, 4, 5, 1, "#f2efe6"),
                 (6, 5, 5, 1, "#dcd6c8"), (5, 6, 5, 1, "#f2efe6"), (5, 7, 4, 1, "#dcd6c8"), (4, 8, 4, 1, "#f2efe6"),
                 (4, 9, 3, 1, "#dcd6c8"), (3, 10, 2, 1, "#6b4a1e"), (2, 11, 2, 1, "#6b4a1e"), (1, 12, 2, 2, "#1a1410"),
                 (8, 13, 7, 1, "#1a1410"), (5, 14, 4, 1, "#1a1410")])


# ---------------------------------------------------------------- page chrome

def minimap_dots(posts):
    dots = []
    for p in posts:
        h = zlib.crc32(p["slug"].encode())
        angle = (h % 360) * math.pi / 180
        radius = 18 + (h >> 9) % 22
        x = 50 + radius * math.cos(angle)
        y = 50 + radius * math.sin(angle)
        dots.append(f'<span class="mm-dot" style="left:{x:.1f}%;top:{y:.1f}%" title="{e(p["title"])}"></span>')
    return "".join(dots)


def sidebar(posts):
    quests = "".join(
        f'<li><a href="{p["url"]}" data-quest="{p["slug"]}">{e(p["title"])}</a></li>' for p in posts
    )
    total_words = sum(p["words"] for p in posts)
    total_minutes = sum(p["minutes"] for p in posts)
    first = min(p["date"] for p in posts) if posts else None
    latest = posts[0]["date"] if posts else None
    tiles = [
        (ICON_QUILL, "Essays", f'{len(posts)}', "Quests released"),
        (ICON_QUESTS, "Words", f'{total_words / 1000:.1f}k', f"{total_words:,} words written"),
        (ICON_STATS, "Minutes", f'{total_minutes}', "Minutes to read everything"),
        (ICON_HOME, "Since", f'{first.year}' if first else "-", "Year of the first post"),
        (ICON_CAL, "Latest", f'{latest:%b %y}' if latest else "-", "Most recent post"),
        (ICON_FRIENDS, "QP", '<span data-qp>0</span>', "Quest points: posts you've finished reading"),
    ]
    tile_html = "".join(
        f'<div class="skill" title="{e(tip)}">{icon}<span class="skill-name">{name}</span><span class="skill-lvl">{val}</span></div>'
        for icon, name, val, tip in tiles
    )
    return f"""
  <aside class="sidepanel stone" aria-label="Side panel">
    <div class="hud">
      <div class="orbs">
        <a class="orb orb-hp" href="/blog/" title="Quests released"><span class="orb-val">{len(posts)}</span><span class="orb-ball"></span></a>
        <div class="orb orb-pray" title="Quest points: posts you've finished reading"><span class="orb-val" data-qp>0</span><span class="orb-ball"></span></div>
        <div class="orb orb-run" title="Run energy: drains as you read"><span class="orb-val" id="run-val">100</span><span class="orb-ball"></span></div>
      </div>
      <a class="minimap" href="/" aria-label="valstechblog home" title="Home">
        <span class="mm-land"></span>{minimap_dots(posts)}<span class="mm-you"></span>
      </a>
      <span class="compass" aria-hidden="true">N</span>
    </div>
    <div class="tabs" role="tablist" aria-label="Side panel tabs">
      <button class="tab active" role="tab" aria-selected="true" aria-controls="panel-quests" data-tab="quests" title="Quest List">{ICON_QUESTS}</button>
      <button class="tab" role="tab" aria-selected="false" aria-controls="panel-stats" data-tab="stats" title="Stats">{ICON_STATS}</button>
      <button class="tab" role="tab" aria-selected="false" aria-controls="panel-friends" data-tab="friends" title="Friends">{ICON_FRIENDS}</button>
    </div>
    <div class="tab-body">
      <section class="panel" id="panel-quests" data-panel="quests" role="tabpanel">
        <h2 class="panel-title">Quest List</h2>
        <p class="panel-sub">Quest Points: <span data-qp>0</span>/{len(posts)}</p>
        <ol class="quest-list">{quests}</ol>
        <p class="legend"><span class="q-new">Not started</span> <span class="q-prog">In progress</span> <span class="q-done">Completed</span></p>
      </section>
      <section class="panel" id="panel-stats" data-panel="stats" role="tabpanel" hidden>
        <h2 class="panel-title">Stats</h2>
        <div class="skills">{tile_html}</div>
        <p class="total-level">Total words: {total_words:,}</p>
      </section>
      <section class="panel" id="panel-friends" data-panel="friends" role="tabpanel" hidden>
        <h2 class="panel-title">Friends List</h2>
        <ul class="friends">
          <li><a href="{SITE['twitter']}" target="_blank" rel="noopener"><span>@valstechblog</span><span class="world">X</span></a></li>
          <li><a href="{SITE['github']}" target="_blank" rel="noopener"><span>valstechblog</span><span class="world">GitHub</span></a></li>
        </ul>
      </section>
    </div>
    <nav class="tabs tabs-bottom" aria-label="Links">
      <a class="tab" href="/" title="Home">{ICON_HOME}</a>
      <a class="tab" href="/blog/" title="All quests">{ICON_QUESTS}</a>
      <a class="tab" href="{SITE['twitter']}" target="_blank" rel="noopener" title="valstechblog on X">{ICON_X}</a>
    </nav>
  </aside>"""


def page(posts, *, title, body, path, description="", slug="", extra_head=""):
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
{sidebar(posts)}
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
          <p class="quest-meta"><span>Released: <b>{nice_date(p['date'])}</b></span><span>Length: <b>{p['length']}</b></span><span><b>{p['minutes']}</b> min</span></p>
          <p class="quest-summary">{e(p['summary'])}</p>
        </li>""")
    return "".join(rows)


def write(rel, text):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    posts = load_posts()

    # Home
    home = f"""
      <section class="scroll">
        <h1 class="scroll-title">Welcome to {SITE['title']}</h1>
        <p class="scroll-lede">Pull up a chair by the fire, adventurer. Pick a quest below to begin.</p>
        <div class="divider" aria-hidden="true"></div>
        <h2 class="section-title">Latest quests</h2>
        <ol class="quest-log">{quest_entries(posts[:10])}</ol>
        <p class="more"><a href="/blog/">View the full quest journal &rarr;</a></p>
      </section>"""
    write("index.html", page(posts, title=SITE["title"], body=home, path="/"))

    # Blog index
    blog = f"""
      <section class="scroll">
        <h1 class="scroll-title">Quest Journal</h1>
        <p class="scroll-lede">{len(posts)} quests released. Completed quests turn green in your Quest List.</p>
        <div class="divider" aria-hidden="true"></div>
        <ol class="quest-log">{quest_entries(posts)}</ol>
      </section>"""
    write("blog/index.html", page(posts, title="Quest Journal", body=blog, path="/blog/"))

    # Posts
    for p in posts:
        body = f"""
      <article class="scroll post">
        <p class="kicker">Quest journal</p>
        <h1 class="scroll-title">{e(p['title'])}</h1>
        <p class="post-meta"><span>Released <time datetime="{p['date']:%Y-%m-%d}">{nice_date(p['date'])}</time></span><span>Length: {p['length']}</span><span>{p['minutes']} min read</span></p>
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
              page(posts, title=p["title"], body=body, path=p["url"], description=p["summary"], slug=p["slug"]))
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
    write("404.html", page(posts, title="Page not found", body=nf, path="/404.html", extra_head=redirect))

    # Sitemap
    urls = ["/", "/blog/"] + [p["url"] for p in posts]
    sitemap = "\n".join(f"  <url><loc>{SITE['url']}{u}</loc></url>" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sitemap}\n</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n")

    print(f"Built {len(posts)} posts into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
