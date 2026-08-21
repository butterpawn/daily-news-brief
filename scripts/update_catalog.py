"""
update_catalog.py

Scans docs/briefs/ for EPUB files and rebuilds docs/catalog.xml, a
valid OPDS 1.2 (Atom-based) catalog feed. CrossInk reads this file to
list and download available Daily Brief editions, newest first.

Uses absolute URLs throughout (not relative paths), since some OPDS
clients -- including some CrossInk/CrossPoint firmware versions --
don't reliably resolve relative acquisition links.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("update_catalog")

DOCS_DIR = Path(__file__).parent.parent / "docs"
BRIEFS_DIR = DOCS_DIR / "briefs"
CATALOG_PATH = DOCS_DIR / "catalog.xml"

# Absolute base URL for this GitHub Pages site.
BASE_URL = "https://butterpawn.github.io/daily-news-brief"

FILENAME_PATTERN = re.compile(r"Daily-Brief-(\d{4}-\d{2}-\d{2})\.epub$")


def find_briefs():
    briefs = []
    if not BRIEFS_DIR.exists():
        return briefs

    for path in BRIEFS_DIR.glob("*.epub"):
        match = FILENAME_PATTERN.search(path.name)
        if not match:
            log.warning("Skipping unrecognized filename: " + path.name)
            continue

        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            log.warning("Skipping unparseable date in filename: " + path.name)
            continue

        briefs.append({
            "filename": path.name,
            "date_str": date_str,
            "date_obj": date_obj,
            "display_date": date_obj.strftime("%-d %b %Y"),
        })

    briefs.sort(key=lambda b: b["date_obj"], reverse=True)
    return briefs


def build_catalog_xml(briefs):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entries = []
    for b in briefs:
        title = escape("Daily Brief \u2014 " + b["display_date"])
        entry_id = "daily-brief-" + b["date_str"]
        link_href = escape(BASE_URL + "/briefs/" + b["filename"])
        updated = b["date_obj"].strftime("%Y-%m-%dT00:00:00Z")

        entries.append(
            "  <entry>\n"
            "    <title>" + title + "</title>\n"
            "    <id>urn:uuid:" + entry_id + "</id>\n"
            "    <updated>" + updated + "</updated>\n"
            "    <content type=\"text\">Daily news brief for " + escape(b["display_date"]) + ".</content>\n"
            "    <link rel=\"http://opds-spec.org/acquisition\"\n"
            "          href=\"" + link_href + "\"\n"
            "          type=\"application/epub+zip\"/>\n"
            "  </entry>"
        )

    entries_xml = "\n".join(entries)
    self_url = escape(BASE_URL + "/catalog.xml")

    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<feed xmlns=\"http://www.w3.org/2005/Atom\"\n"
        "      xmlns:opds=\"http://opds-spec.org/2010/catalog\">\n"
        "  <id>urn:uuid:daily-brief-catalog</id>\n"
        "  <title>Daily Brief Library</title>\n"
        "  <updated>" + now + "</updated>\n"
        "  <author>\n"
        "    <name>Daily Brief Bot</name>\n"
        "  </author>\n"
        "  <link rel=\"self\"\n"
        "        href=\"" + self_url + "\"\n"
        "        type=\"application/atom+xml;profile=opds-catalog;kind=acquisition\"/>\n"
        "  <link rel=\"start\"\n"
        "        href=\"" + self_url + "\"\n"
        "        type=\"application/atom+xml;profile=opds-catalog;kind=acquisition\"/>\n"
        + entries_xml + "\n"
        "</feed>\n"
    )


def main():
    briefs = find_briefs()
    log.info("Found " + str(len(briefs)) + " brief(s) in " + str(BRIEFS_DIR))

    xml_content = build_catalog_xml(briefs)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w") as f:
        f.write(xml_content)

    log.info("Catalog written: " + str(CATALOG_PATH) + " (" + str(len(briefs)) + " entries)")


if __name__ == "__main__":
    main()
