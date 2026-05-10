import feedparser
import yaml
import sqlite3
from pathlib import Path

DB_PATH = Path("data/db/news.db")
SOURCES_PATH = Path("config/sources.yaml")

def load_sources():
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["rss_sources"]

def save_article(article):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT OR IGNORE INTO articles (
            source_name,
            category,
            title,
            url,
            published_at,
            summary,
            content
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            article["source_name"],
            article["category"],
            article["title"],
            article["url"],
            article["published_at"],
            article["summary"],
            article["content"],
        ))

        conn.commit()
    finally:
        conn.close()

def collect_rss():
    sources = load_sources()
    total_seen = 0
    total_saved_or_ignored = 0

    for source in sources:
        print(f"Fetching: {source['name']}")

        feed = feedparser.parse(source["url"])

        if feed.bozo:
            print(f"Warning: feed parse issue for {source['name']}: {feed.bozo_exception}")

        entries = feed.entries
        print(f"  Entries found: {len(entries)}")

        for entry in entries:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            published_at = entry.get("published", "")
            summary = entry.get("summary", "")

            if not title or not url:
                continue

            article = {
                "source_name": source["name"],
                "category": source["category"],
                "title": title,
                "url": url,
                "published_at": published_at,
                "summary": summary,
                "content": summary,
            }

            save_article(article)
            total_seen += 1
            total_saved_or_ignored += 1

    print(f"RSS collection finished. Parsed valid entries: {total_seen}")

if __name__ == "__main__":
    collect_rss()
