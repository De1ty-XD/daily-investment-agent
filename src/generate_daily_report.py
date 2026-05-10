import argparse
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


DEFAULT_DB_PATH = "data/db/news.db"
DEFAULT_REPORT_DIR = "reports"


def connect_db(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] for row in rows]


def pick_column(columns: List[str], candidates: List[str]) -> str:
    for col in candidates:
        if col in columns:
            return col
    return ""


def parse_datetime(value) -> Optional[datetime]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # 兼容常见格式：
    # 2026-05-10 20:14:26
    # 2026-05-10T20:14:26
    # 2026-05-10T20:14:26.123456
    # 2026-05-10T20:14:26+08:00
    candidates = [
        text,
        text.replace("Z", "+00:00"),
        text.replace("T", " "),
    ]

    for item in candidates:
        try:
            dt = datetime.fromisoformat(item)
            if dt.tzinfo is not None:
                dt = dt.astimezone().replace(tzinfo=None)
            return dt
        except Exception:
            pass

    # 兼容 RSS 常见格式
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            if dt.tzinfo is not None:
                dt = dt.astimezone().replace(tzinfo=None)
            return dt
        except Exception:
            pass

    return None


def safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def fetch_summarized_articles(conn: sqlite3.Connection, limit: int, hours: Optional[int]):
    columns = get_table_columns(conn, "articles")

    title_col = pick_column(columns, ["title", "headline", "name"]) or "title"
    source_col = pick_column(columns, ["source", "publisher", "feed_name"])
    url_col = pick_column(columns, ["url", "link"])
    published_col = pick_column(columns, ["published_at", "published", "created_at"])
    summary_col = "ai_summary"
    analysis_col = "ai_analysis"

    summarized_col = "ai_summarized_at" if "ai_summarized_at" in columns else ""
    order_col = summarized_col or published_col or "id"

    select_parts = [
        "id",
        f"{title_col} AS title",
        f"{summary_col} AS ai_summary",
        f"{analysis_col} AS ai_analysis",
    ]

    if source_col:
        select_parts.append(f"{source_col} AS source")
    else:
        select_parts.append("'' AS source")

    if url_col:
        select_parts.append(f"{url_col} AS url")
    else:
        select_parts.append("'' AS url")

    if published_col:
        select_parts.append(f"{published_col} AS published_at")
    else:
        select_parts.append("'' AS published_at")

    if summarized_col:
        select_parts.append(f"{summarized_col} AS ai_summarized_at")
    else:
        select_parts.append("'' AS ai_summarized_at")

    query = f"""
    SELECT {", ".join(select_parts)}
    FROM articles
    WHERE ai_summary IS NOT NULL
      AND TRIM(ai_summary) != ''
    ORDER BY {order_col} DESC
    """

    rows = conn.execute(query).fetchall()

    if hours is not None and hours > 0:
        threshold = datetime.now() - timedelta(hours=hours)
        filtered = []

        for row in rows:
            # 优先用 AI 摘要时间限制。
            # 这样可以表示“最近半天整理出来的内容”。
            dt = parse_datetime(row["ai_summarized_at"])

            # 如果没有摘要时间，则退回使用发布时间。
            if dt is None:
                dt = parse_datetime(row["published_at"])

            if dt is not None and dt >= threshold:
                filtered.append(row)

        rows = filtered

    return rows[:limit]


def build_report(rows, hours: Optional[int]) -> str:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    lines = []

    lines.append("# 每日投资新闻简报")
    lines.append("")
    lines.append(f"- 生成日期：{date_str}")
    lines.append(f"- 生成时间：{time_str}")

    if hours is not None and hours > 0:
        lines.append(f"- 时间范围：最近 {hours} 小时")
    else:
        lines.append("- 时间范围：不限")

    lines.append(f"- 新闻数量：{len(rows)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    if not rows:
        lines.append("暂无符合时间范围的已摘要新闻。")
        lines.append("")
        return "\n".join(lines)

    lines.append("## 一、摘要总览")
    lines.append("")

    for index, row in enumerate(rows, start=1):
        title = safe_text(row["title"])
        summary = safe_text(row["ai_summary"])

        lines.append(f"{index}. **{title}**")
        lines.append(f"   - {summary}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 二、详细分析")
    lines.append("")

    for index, row in enumerate(rows, start=1):
        article_id = row["id"]
        title = safe_text(row["title"])
        source = safe_text(row["source"])
        published_at = safe_text(row["published_at"])
        summarized_at = safe_text(row["ai_summarized_at"])
        url = safe_text(row["url"])
        summary = safe_text(row["ai_summary"])
        analysis = safe_text(row["ai_analysis"])

        lines.append(f"### {index}. {title}")
        lines.append("")
        lines.append(f"- ID：{article_id}")

        if source:
            lines.append(f"- 来源：{source}")

        if published_at:
            lines.append(f"- 发布时间：{published_at}")

        if summarized_at:
            lines.append(f"- 摘要时间：{summarized_at}")

        if url:
            lines.append(f"- 原文链接：{url}")

        lines.append("")
        lines.append(f"**一句话摘要：** {summary}")
        lines.append("")

        if analysis:
            lines.append(analysis)
        else:
            lines.append("暂无详细分析。")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def save_report(content: str, report_dir: str, hours: Optional[int]) -> Path:
    Path(report_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    if hours is not None and hours > 0:
        filename = f"daily_report_last_{hours}h_{timestamp}.md"
    else:
        filename = f"daily_report_{timestamp}.md"

    path = Path(report_dir) / filename
    path.write_text(content, encoding="utf-8")

    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"SQLite database path. Default: {DEFAULT_DB_PATH}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of summarized articles in report. Default: 20",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help="Only include articles summarized within the last N hours. Example: --hours 12",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_REPORT_DIR,
        help=f"Report output directory. Default: {DEFAULT_REPORT_DIR}",
    )

    args = parser.parse_args()

    conn = connect_db(args.db)
    rows = fetch_summarized_articles(conn, args.limit, args.hours)
    conn.close()

    report = build_report(rows, args.hours)
    path = save_report(report, args.out, args.hours)

    print(f"Report generated: {path}")
    print(f"Articles included: {len(rows)}")

    if args.hours:
        print(f"Time window: last {args.hours} hours")


if __name__ == "__main__":
    main()
