# Daily Brief

Automated daily news briefing, delivered as an EPUB via OPDS to a Xteink X3
running CrossInk 1.5.0.

## How it works

1. GitHub Actions runs every morning (see `.github/workflows/daily-brief.yml`)
2. `scripts/fetch_news.py` pulls articles from the RSS feeds in `config/sources.yaml`
3. `scripts/summarize.py` sends the collected headlines to Gemini, which
   dedupes, ranks, and writes the brief
4. `scripts/build_epub.py` turns that into `docs/briefs/Daily-Brief-YYYY-MM-DD.epub`
5. `scripts/update_catalog.py` rebuilds `docs/catalog.xml`, the OPDS feed
6. `scripts/cleanup.py` deletes any brief older than 7 days
7. Everything is committed back to the repo, and GitHub Pages serves
   `docs/` as the live site

## OPDS URL

Once GitHub Pages is enabled: `https://<your-username>.github.io/<repo-name>/catalog.xml`

Point CrossInk's OPDS catalog setting at that URL.

## Status

🚧 Under construction — see project steps in the build conversation.
