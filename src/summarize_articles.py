import argparse
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from llm_client import ask_llm


DEFAULT_DB_PATH = "data/db/news.db"


def connect_db(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Database not found: {db_path}. Please run init_db.py and rss_collector.py first."
        )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] for row in rows]


def ensure_ai_columns(conn: sqlite3.Connection) -> None:
    columns = get_table_columns(conn, "articles")

    if "ai_summary" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN ai_summary TEXT")

    if "ai_analysis" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN ai_analysis TEXT")

    if "ai_summarized_at" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN ai_summarized_at TEXT")

    conn.commit()


def pick_first_available(row: sqlite3.Row, candidate_columns: List[str]) -> str:
    keys = row.keys()

    for col in candidate_columns:
        if col in keys and row[col]:
            return str(row[col]).strip()

    return ""


def fetch_unsummarized_articles(conn: sqlite3.Connection, limit: int) -> List[sqlite3.Row]:
    columns = get_table_columns(conn, "articles")

    order_column = "id"
    if "published_at" in columns:
        order_column = "published_at"
    elif "created_at" in columns:
        order_column = "created_at"

    query = f"""
    SELECT *
    FROM articles
    WHERE ai_summary IS NULL
       OR TRIM(ai_summary) = ''
    ORDER BY {order_column} DESC
    LIMIT ?
    """

    return conn.execute(query, (limit,)).fetchall()


def build_article_text(row: sqlite3.Row) -> Dict[str, str]:
    title = pick_first_available(row, ["title", "headline", "name"])
    source = pick_first_available(row, ["source", "publisher", "feed_name"])
    url = pick_first_available(row, ["url", "link"])
    published_at = pick_first_available(row, ["published_at", "published", "created_at"])

    body = pick_first_available(
        row,
        [
            "content",
            "article_text",
            "full_text",
            "description",
            "summary",
            "excerpt",
        ],
    )

    # Avoid sending extremely long text to local model.
    max_chars = 8000
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n[文章内容过长，已截断]"

    return {
        "title": title,
        "source": source,
        "url": url,
        "published_at": published_at,
        "body": body,
    }


def build_prompt(article: Dict[str, str]) -> str:
    return f"""
请对下面这篇新闻做投资研究用途的中文摘要。

请严格遵守：
1. 不要编造原文没有的信息。
2. 不要给出买入、卖出、持有等直接投资建议。
3. 不要提供个性化投资建议。
4. 如果原文信息不足，请明确说明“信息不足”。
5. 重点关注：事实摘要、可能影响的资产类别、市场含义、不确定性、后续需要关注的问题。
6. 使用简体中文。
7. 输出要清晰、紧凑、可直接写入数据库。

请按以下格式输出：

## 一句话摘要
用一句话概括新闻核心内容。

## 关键事实
- 列出 3 到 6 条关键事实。

## 市场相关性
说明这条新闻可能影响哪些市场或资产类别，例如：股票、债券、外汇、大宗商品、科技股、银行股、半导体、能源、黄金、美元、美债收益率等。

## 潜在影响
从宏观、行业、公司或风险偏好的角度分析可能影响。不要给交易建议。

## 不确定性与后续观察
- 列出需要继续跟踪的 2 到 5 个问题。

新闻信息如下：

标题：{article["title"]}
来源：{article["source"]}
发布时间：{article["published_at"]}
链接：{article["url"]}

正文：
{article["body"]}
""".strip()


def split_summary_and_analysis(text: str) -> Dict[str, str]:
    """
    Store a short summary separately if possible.
    Full structured output goes to ai_analysis.
    """

    summary = ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if "一句话摘要" in line:
            # Take the next non-heading line.
            for next_line in lines[i + 1:]:
                if not next_line.startswith("#"):
                    summary = next_line.lstrip("- ").strip()
                    break
            break

    if not summary and lines:
        # Fallback: use the first meaningful line.
        for line in lines:
            if not line.startswith("#"):
                summary = line.lstrip("- ").strip()
                break

    return {
        "summary": summary[:500],
        "analysis": text.strip(),
    }


def update_article_summary(
    conn: sqlite3.Connection,
    article_id: int,
    ai_summary: str,
    ai_analysis: str,
) -> None:
    now = datetime.now().isoformat(timespec="seconds")

    conn.execute(
        """
        UPDATE articles
        SET ai_summary = ?,
            ai_analysis = ?,
            ai_summarized_at = ?
        WHERE id = ?
        """,
        (ai_summary, ai_analysis, now, article_id),
    )

    conn.commit()


def summarize_articles(db_path: str, limit: int) -> None:
    conn = connect_db(db_path)
    ensure_ai_columns(conn)

    articles = fetch_unsummarized_articles(conn, limit)

    if not articles:
        print("No unsummarized articles found.")
        return

    print(f"Found {len(articles)} unsummarized article(s).")

    for index, row in enumerate(articles, start=1):
        article_id = row["id"]
        article = build_article_text(row)

        print()
        print(f"[{index}/{len(articles)}] Summarizing article ID={article_id}")
        print(f"Title: {article['title'][:120]}")

        if not article["title"] and not article["body"]:
            print("Skipped: empty title and body.")
            continue

        prompt = build_prompt(article)

        try:
            result = ask_llm(
                prompt,
                temperature=0.2,
                max_tokens=1536,
            )

            parsed = split_summary_and_analysis(result)

            update_article_summary(
                conn=conn,
                article_id=article_id,
                ai_summary=parsed["summary"],
                ai_analysis=parsed["analysis"],
            )

            print("Done.")
            print(f"Summary: {parsed['summary'][:160]}")

        except Exception as e:
            print(f"Failed to summarize article ID={article_id}: {repr(e)}")

    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"SQLite database path. Default: {DEFAULT_DB_PATH}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of articles to summarize. Default: 5",
    )

    args = parser.parse_args()

    summarize_articles(
        db_path=args.db,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
