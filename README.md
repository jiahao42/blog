# blog

This repo contains my personal blog, and a simple/stupid "framework" (nope) to help me manage it.

## Usage

- write your posts in Markdown under `blog/posts/src`
- run `make` to generate HTML from Markdown
- run `make rss` to generate RSS Feed, `blog/atom.xml`
- run `make sitemap` to generate sitemap, `blog/sitemap.xml`
- run `make sync` to sync the blog to server

## Misc

Markdown-to-HTML transformation relies on Pandoc, template and metadata of generated HTML can be found at `blog/posts/templates` 

Enjoy

---

P.S. visit my blog at http://idle.systems (mostly in Chinese)
