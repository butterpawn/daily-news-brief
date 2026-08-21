"""
cleanup.py

Deletes any Daily Brief EPUB in docs/briefs/ older than RETENTION_DAYS.
Only touches files matching the Daily-Brief-YYYY-MM-DD.epub pattern --
nothing else in the repo is ever affected.

Uses Malaysia local date (UTC+8) as "today", matching the date labels
used when briefs are generated, so retention lines up with what you
actually see on the filenames.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("cleanup")

BRIEFS_DIR = Path(__file__).parent.parent / "docs" / "briefs"
FILENAME_PATTERN = re.compile(r"Daily-Brief-(\d{4}-\d{2}-\d{2})\.epub$")

RETENTION_DAYS = 7
MYT_OFFSET = timezone(timedelta(hours=8))


def today_myt():
    return datetime.now(MYT_OFFSET).replace(hour=0, minute=0, second=0, microsecond=0)


def main():
    if not BRIEFS_DIR.exists():
        log.info(str(BRIEFS_DIR) + " does not exist yet - nothing to clean up")
        return

    cutoff = today_myt() - timedelta(days=RETENTION_DAYS - 1)
    log.info("Retention cutoff: keeping briefs from " + str(cutoff.date()) + " onward")

    kept = 0
    deleted = 0

    for path in sorted(BRIEFS_DIR.glob("*.epub")):
        match = FILENAME_PATTERN.search(path.name)
        if not match:
            log.warning("Skipping unrecognized filename (not touching it): " + path.name)
            continue

        date_str = match.group(1)
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=MYT_OFFSET)
        except ValueError:
            log.warning("Skipping unparseable date in filename: " + path.name)
            continue

        if file_date < cutoff:
            path.unlink()
            log.info("Deleted (older than " + str(RETENTION_DAYS) + " days): " + path.name)
            deleted += 1
        else:
            kept += 1

    log.info("Cleanup done: kept " + str(kept) + ", deleted " + str(deleted))


if __name__ == "__main__":
    main()
