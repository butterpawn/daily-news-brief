"""Prints a quick summary of how many articles were collected per section."""

import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "articles.json"


def main():
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    print("Fetched at: " + data["fetched_at"])
    print("-" * 40)
    for section, articles in data["sections"].items():
        print(section + ": " + str(len(articles)) + " articles")


if __name__ == "__main__":
    main()
