"""
summarize.py

Sends the collected articles (data/articles.json) to Gemini, which
dedupes overlapping coverage, picks the most significant stories per
section, and writes concise, neutral summaries.

Output: data/brief.json, a structured document ready for build_epub.py.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import types

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("summarize")

ARTICLES_PATH = Path(__file__).parent.parent / "data" / "articles.json"
BRIEF_PATH = Path(__file__).parent.parent / "data" / "brief.json"

MODEL_NAME = "gemini-flash-latest"

SECTION_TARGETS = {
    "malaysia": {"count": "3-5", "length": "2-4 sentences"},
    "world": {"count": "3-5", "length": "2-4 sentences"},
    "technology": {"count": "2-4", "length": "2-4 sentences"},
    "environment": {"count": "2-4", "length": "2-4 sentences"},
    "cities": {"count": "1-3", "length": "2-4 sentences"},
    "design": {"count": "1-3", "length": "2-4 sentences"},
    "business": {"count": "2-3", "length": "2-4 sentences"},
}
QUICK_BRIEF_COUNT = 5


def load_articles():
    with open(ARTICLES_PATH, "r") as f:
        return json.load(f)


def build_prompt(sections):
    lines = []
    lines.append(
        "You are writing a concise daily news brief for someone reading on an "
        "e-ink device. You will be given raw article title/summary/source data "
        "collected from RSS feeds, grouped by section.\n"
    )
    lines.append(
        "STRICT RULES:\n"
        "- Only use information present in the provided articles. Never invent facts, "
        "quotes, numbers, or context not stated in the source material.\n"
        "- If sources disagree, say so plainly rather than picking one version as fact.\n"
        "- Write in clear, neutral English. No clickbait phrasing, no excessive adjectives, "
        "no opinion presented as fact.\n"
        "- Remove duplicate coverage of the same event across sources; combine into ONE "
        "story citing all sources that covered it.\n"
        "- Favor substantive news (politics, policy, economy, infrastructure, technology, "
        "environment, urban development) over celebrity/gossip/viral content.\n"
        "- For each section, select ONLY the most significant stories -- do not pad with "
        "low-value filler.\n"
    )
    lines.append("SECTION TARGETS:")
    for section, spec in SECTION_TARGETS.items():
        lines.append("- " + section + ": " + spec["count"] + " stories, " + spec["length"] + " each")
    lines.append(
        "- quick_brief: " + str(QUICK_BRIEF_COUNT) + " additional noteworthy stories from ANY "
        "section that didn't make the main cut, ONE sentence each"
    )

    lines.append(
        "\nOUTPUT FORMAT: respond with ONLY valid JSON, no markdown fences, no preamble, "
        "matching this exact structure:\n"
        '{\n'
        '  "sections": {\n'
        '    "malaysia": [\n'
        '      {"headline": "...", "summary": "...", "sources": ["Source A", "Source B"]}\n'
        '    ],\n'
        '    "world": [...],\n'
        '    "technology": [...],\n'
        '    "environment": [...],\n'
        '    "cities": [...],\n'
        '    "design": [...],\n'
        '    "business": [...],\n'
        '    "quick_brief": [\n'
        '      {"text": "...", "sources": ["Source A"]}\n'
        '    ]\n'
        '  }\n'
        '}\n'
        "If a section has no substantive articles available, return an empty list for it "
        "-- do not fabricate content to fill it.\n"
    )

    lines.append("\nRAW ARTICLES BY SECTION:\n")
    for section, articles in sections.items():
        lines.append("\n=== " + section.upper() + " (" + str(len(articles)) + " articles) ===")
        for a in articles:
            lines.append("- [" + a["source"] + "] " + a["title"] + ": " + a["summary"][:300])

    return "\n".join(lines)


MAX_RETRIES = 4
RETRY_DELAYS = [5, 15, 45, 90]  # seconds, exponential-ish backoff


def call_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY not set in environment")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            text = response.text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            return json.loads(text)

        except Exception as e:
            last_error = e
            is_last_attempt = attempt == MAX_RETRIES
            if is_last_attempt:
                break
            delay = RETRY_DELAYS[attempt - 1]
            log.warning(
                "Attempt " + str(attempt) + "/" + str(MAX_RETRIES) + " failed (" + str(e) + "). "
                "Retrying in " + str(delay) + "s..."
            )
            time.sleep(delay)

    raise last_error


def main():
    data = load_articles()
    sections = data.get("sections", {})

    total_articles = sum(len(v) for v in sections.values())
    if total_articles == 0:
        log.error("No articles to summarize - aborting")
        sys.exit(1)

    log.info("Summarizing " + str(total_articles) + " articles across " + str(len(sections)) + " sections")

    prompt = build_prompt(sections)

    try:
        result = call_gemini(prompt)
    except json.JSONDecodeError as e:
        log.error("Gemini returned invalid JSON: " + str(e))
        sys.exit(1)
    except Exception as e:
        log.error("Gemini call failed: " + str(e))
        sys.exit(1)

    brief = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": result.get("sections", {}),
    }

    BRIEF_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BRIEF_PATH, "w") as f:
        json.dump(brief, f, indent=2)

    story_count = sum(len(v) for v in brief["sections"].values())
    log.info("Done: brief written with " + str(story_count) + " stories total -> " + str(BRIEF_PATH))


if __name__ == "__main__":
    main()
