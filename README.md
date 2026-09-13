# GENVID website

GENVID is a Malaysian AI-video service. Tagline: Ideas into video.

It turns a plain text idea, or one product photo, into a short AI video. Customers order through the Telegram bot [t.me/ZhongZena_bot](https://t.me/ZhongZena_bot).

This repository is the marketing site: static HTML and CSS, no frameworks, no build step, no JavaScript libraries. GitHub Pages publishes the `/docs` folder to [https://raffieeey.github.io/genvid-website/](https://raffieeey.github.io/genvid-website/).

## File map

- `README.md` - this file
- `docs/` - published site
  - `index.html` - home and clip gallery
  - `pricing.html` - packs and credits
  - `business.html` - for business
  - `trust.html` - labels, use, payments, privacy, support
  - `404.html` - not found
  - `robots.txt`
  - `sitemap.xml`
  - SEO: canonical, Open Graph, Twitter cards and JSON-LD on every page head
  - `favicon.png`
  - `logo.jpg`
  - `og-image.jpg`
  - `css/styles.css` - shared shell
  - `css/pages.css` - extra page rules when present
  - `clips/<slug>.mp4` - sample videos
  - `clips/posters/<slug>.jpg` - posters
  - `README.md` - notes for the published folder

## Edit copy

Open the HTML file in `docs/` and change the text. Save and refresh. There is no compile step.

Shared header, footer, type and colour live in `docs/css/styles.css`. Extra page rules may live in `docs/css/pages.css`. Both files are plain CSS.

## Swap a clip

Keep the slug. Replace both files:

- `docs/clips/<slug>.mp4`
- `docs/clips/posters/<slug>.jpg`

Slugs in use: `laundry-rain`, `tng-balance`, `lima-minit`, `lift-nasihat`, `haze-sacrifice`, `senang-je`, `balik-jam`, `duduk-dulu`, `aku-tau-jalan`.

If the title or hook changes, update the gallery markup in `docs/index.html`.

All sample clips on this site are AI-generated and labelled AI-generated.
