"""
build_epub.py

Turns data/brief.json into a reader-friendly EPUB for e-ink devices:
simple typography, no images, clear headings, a working table of
contents. Output: docs/briefs/Daily-Brief-YYYY-MM-DD.epub
"""

import json
import logging
import sys
from pathlib import Path

from ebooklib import epub

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("build_epub")

BRIEF_PATH = Path(__file__).parent.parent / "data" / "brief.json"
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "briefs"

SECTION_META = {
    "malaysia": ("🇲🇾 Malaysia", "Malaysia"),
    "world": ("🌏 World", "World"),
    "technology": ("💻 Technology", "Technology"),
    "environment": ("🌱 Environment & Climate", "Environment"),
    "cities": ("🏙️ Cities / Urban Development", "Cities"),
    "design": ("🎨 Design / Architecture", "Design"),
    "business": ("💼 Business / Economy", "Business"),
}

CSS = """
body {
    font-family: serif;
    line-height: 1.5;
    margin: 0 1em;
}
h1 {
    font-size: 1.4em;
    border-bottom: 1px solid #000;
    padding-bottom: 0.2em;
}
h2 {
    font-size: 1.15em;
    margin-top: 1.4em;
    margin-bottom: 0.3em;
}
p {
    margin: 0.4em 0;
    text-align: left;
}
.sources {
    font-size: 0.8em;
    color: #444;
    font-style: italic;
    margin-top: 0.2em;
    margin-bottom: 1.2em;
}
.quick-item {
    margin-bottom: 0.8em;
}
.date-header {
    font-size: 0.9em;
    color: #555;
    margin-bottom: 1.5em;
}
"""


def render_story_html(story):
    headline = story.get("headline", "")
    summary = story.get("summary", "")
    sources = ", ".join(story.get("sources", []))
    return (
        "<h2>" + headline + "</h2>"
        "<p>" + summary + "</p>"
        "<p class=\"sources\">Sources: " + sources + "</p>"
    )


def render_quick_item_html(item):
    text = item.get("text", "")
    sources = ", ".join(item.get("sources", []))
    return (
        "<p class=\"quick-item\">" + text + " "
        "<span class=\"sources\">(Sources: " + sources + ")</span></p>"
    )


def build_epub(brief):
    date_str = brief.get("date", "unknown-date")

    book = epub.EpubBook()
    book.set_identifier("daily-brief-" + date_str)
    book.set_title("Daily Brief - " + date_str)
    book.set_language("en")
    book.add_author("Daily Brief Bot")

    style = epub.EpubItem(
        uid="style",
        file_name="style/style.css",
        media_type="text/css",
        content=CSS,
    )
    book.add_item(style)

    chapters = []
    toc = []

    sections = brief.get("sections", {})

    for key, meta in SECTION_META.items():
        title, short_title = meta
        stories = sections.get(key, [])
        if not stories:
            continue

        html = "<h1>" + title + "</h1>"
        for story in stories:
            html += render_story_html(story)

        chapter = epub.EpubHtml(
            title=short_title,
            file_name=key + ".xhtml",
            lang="en",
        )
        chapter.content = html
        chapter.add_item(style)
        book.add_item(chapter)
        chapters.append(chapter)
        toc.append(chapter)

    quick_items = sections.get("quick_brief", [])
    if quick_items:
        html = "<h1>⚡ Quick Brief</h1>"
        for item in quick_items:
            html += render_quick_item_html(item)

        chapter = epub.EpubHtml(
            title="Quick Brief",
            file_name="quick_brief.xhtml",
            lang="en",
        )
        chapter.content = html
        chapter.add_item(style)
        book.add_item(chapter)
        chapters.append(chapter)
        toc.append(chapter)

    cover_html = (
        "<h1>DAILY BRIEF</h1>"
        "<p class=\"date-header\">" + date_str + "</p>"
    )
    cover = epub.EpubHtml(title="Daily Brief", file_name="cover.xhtml", lang="en")
    cover.content = cover_html
    cover.add_item(style)
    book.add_item(cover)

    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    book.spine = ["nav", cover] + chapters

    return book


def main():
    if not BRIEF_PATH.exists():
        log.error(str(BRIEF_PATH) + " not found - run summarize.py first")
        sys.exit(1)

    with open(BRIEF_PATH, "r") as f:
        brief = json.load(f)

    total_stories = sum(len(v) for v in brief.get("sections", {}).values())
    if total_stories == 0:
        log.error("Brief has zero stories - aborting EPUB build")
        sys.exit(1)

    book = build_epub(brief)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = brief.get("date", "unknown-date")
    output_path = OUTPUT_DIR / ("Daily-Brief-" + date_str + ".epub")

    epub.write_epub(str(output_path), book)

    log.info("EPUB written: " + str(output_path) + " (" + str(total_stories) + " stories)")


if __name__ == "__main__":
    main()
