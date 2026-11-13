# valstechblog

Static site for [valstech.blog](https://valstech.blog), styled like an old-school fantasy MMO interface.
No Hugo, no framework: plain HTML, CSS and JavaScript in `site/`.

## Layout

- `content/blog/<slug>/index.md` — posts in Markdown (front matter: `title`, `date`, optional `private = true`)
- `build.py` — renders the posts into `site/` (pages, RSS, sitemap)
- `site/css/osrs.css`, `site/js/osrs.js` — the theme (hand-edited)
- `site/` — the deployed website

## Writing a post

1. Add `content/blog/my-post/index.md`
2. Optionally preview: `pip install markdown && python3 build.py && python3 -m http.server -d site`
3. Push to `master`. The GitHub Actions workflow re-renders and deploys `site/`.

In the repo's **Settings → Pages**, the source should be **GitHub Actions**.
