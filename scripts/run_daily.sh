#!/usr/bin/env bash
set -e

PROJECT_DIR="/Users/limen/daily-investment-agent"
cd "$PROJECT_DIR"

mkdir -p logs reports

LOG_FILE="logs/run_daily_$(date '+%Y-%m-%d_%H%M%S').log"

{
  echo "======================================"
  echo "Daily Investment Agent"
  echo "Started at: $(date)"
  echo "Project: $PROJECT_DIR"
  echo "======================================"
  echo ""

  echo "[0/4] Activating virtual environment..."
  source .venv/bin/activate

  echo ""
  echo "[1/4] Checking local LLM server..."
  if curl -s http://127.0.0.1:8080/v1/models >/dev/null; then
    echo "LLM server is running."
  else
    echo "ERROR: LLM server is not running at http://127.0.0.1:8080/v1"
    echo ""
    echo "请先在另一个终端启动 llama-server。"
    echo "启动后再重新运行："
    echo "./scripts/run_daily.sh"
    exit 1
  fi

  echo ""
  echo "[2/4] Collecting RSS articles..."
  python src/rss_collector.py

  echo ""
  echo "[3/4] Summarizing new articles..."
  python src/summarize_articles.py --limit 20

  echo ""
  echo "[4/4] Generating report..."
  python src/generate_daily_report.py --hours 12 --limit 50

  echo ""
  echo "Latest reports:"
  ls -lt reports | head

  echo ""
  echo "Finished at: $(date)"
  echo "Done."
} 2>&1 | tee "$LOG_FILE"
