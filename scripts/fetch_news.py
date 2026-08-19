"""
fetch_news.py

Pulls articles from every RSS feed listed in config/sources.yaml,
grouped by section. If a feed fails (timeout, bad XML, 404, etc.),
it's logged and skipped -- the rest of the run continues normally.

Output: a single JSON file (data/articles.json) with all collected
articles, tagged by section, ready for summarize.py to process.
"""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("fetch_news")

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "articles.json"

MAX_ARTICLE_AGE_HOURS = 36


def load_sources():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def parse_entry_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def fetch_feed(name, url):
    articles = []
    try:
        parsed = feedparser.parse(url)

        if parsed.bozo and not parsed.entries:
            raise ValueError("feed unparseable: " + str(parsed.bozo_exception))

        if not parsed.entries:
            log.warning("[" + name + "] returned 0 entries")
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_ARTICLE_AGE_HOURS)

        for entry in parsed.entries:
            pub_date = parse_entry_date(entry)
            if pub_date and pub_date < cutoff:
                continue

            articles.append({
                "source": name,
                "title": entry.get("title", "").strip(),
                "summary": entry.get("summary", "").strip(),
                "link": entry.get("link", ""),
                "published": pub_date.isoformat() if pub_date else None,
            })

        log.info("[" + name + "] OK - " + str(len(articles)) + " recent articles")
        return articles

    except Exception as e:
        log.error("[" + name + "] FAILED - " + str(e))
        return []


def main():
    sources = load_sources()
    all_articles = {}
    total = 0
    failures = 0
    feed_count = 0

    for section, feeds in sources.items():
        section_articles = []
        for feed in feeds:
            feed_count += 1
            items = fetch_feed(feed["name"], feed["url"])
            if not items:
                failures += 1
            section_articles.extend(items)
            total += len(items)
        all_articles[section] = section_articles

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(
            {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "sections": all_articles,
            },
            f,
            indent=2,
        )

    log.info("Done: " + str(total) + " articles from " + str(feed_count - failures) + "/" + str(feed_count) + " feeds")

    if total == 0:
        log.error("No articles collected from any feed - aborting")
        sys.exit(1)


if __name__ == "__main__":
    main()
