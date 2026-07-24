# blog

This repo contains my personal blog, and a simple/stupid "framework" (nope) to help me manage it.

## Setup

Requires [Pandoc](https://pandoc.org/) and [uv](https://docs.astral.sh/uv/).

The Python scripts run through `uv run`, which creates the virtualenv and
installs dependencies on first use — no manual venv or `pip install` needed.
To prepare it ahead of time:

    uv sync

Generated output (`posts/*.html`, `atom.xml`, `sitemap.xml`) is not kept in the
repo. After a fresh clone, rebuild it with:

    make && make rss && make sitemap

## Usage

- write your posts in Markdown under `blog/posts/src`
- run `make` to generate HTML from Markdown
- run `make rss` to generate RSS Feed, `blog/atom.xml`
- run `make sitemap` to generate sitemap, `blog/sitemap.xml`
- run `make ga` to refresh Google Analytics pageviews and `geo.json`
- run `make sync` to sync the blog to server

## Misc

Markdown-to-HTML transformation relies on Pandoc, template and metadata of generated HTML can be found at `blog/posts/templates` 

Python dependencies live in `pyproject.toml`, pinned by `uv.lock`. `make ga`
additionally needs `ga.config`, a Google service-account key that is
deliberately not in the repo.

Enjoy

---

P.S. visit my blog at http://idle.systems (mostly in Chinese)
