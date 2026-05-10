  # Daily Investment Agent

  Daily Investment Agent is a Python-based automation tool for collecting, organizing, and summarizing daily investment-related information from financial RSS feeds and news sources.

  The project is designed to help track market updates, macroeconomic news, U.S. equities, technology, AI-related trends, crypto markets, and other investment-related topics. It currently focuses on local automation and can be extended with AI summarization, keyword monitoring, importance scoring, scheduled execution, and notification delivery.

  ---

  ## Project Goal

  The main goal of this project is to build a personal daily investment information agent.

  The basic workflow is:

  ```text
  Collect daily investment-related information
  → Clean and deduplicate data
  → Store data in a local database
  → Generate a daily investment briefing
  ```

  In short, this project acts as a lightweight personal market intelligence assistant.

  ---

  ## Features

  - Fetch financial news from RSS / news sources
  - Manage source configuration with YAML
  - Parse news title, URL, source, and published time
  - Store collected data in a local SQLite database
  - Deduplicate news items
  - Generate daily investment briefings in Markdown format
  - Keep local runtime data out of the GitHub repository
  - Support future extensions such as AI summaries, keyword filters, and automated notifications

  ---

  ## Tech Stack

  - Python
  - YAML
  - RSS / HTTP
  - SQLite
  - Markdown
  - Git / GitHub

  Possible Python dependencies include:

  - `feedparser`
  - `requests`
  - `PyYAML`
  - `beautifulsoup4`
  - `pandas`

  Please refer to `requirements.txt` for the actual dependency list.

  ---

  ## Project Structure

  ```text
  daily-investment-agent/
  ├── config/
  │   └── sources.yaml
  ├── scripts/
  ├── src/
  ├── README.md
  ├── requirements.txt
  └── .gitignore
  ```

  During local execution, the following folders may also be generated:

  ```text
  daily-investment-agent/
  ├── data/
  │   └── db/
  │       └── news.db
  ├── logs/
  └── reports/
  ```

  ---

  ## Directory Overview

  | Path | Description |
  |---|---|
  | `config/` | Project configuration files |
  | `config/sources.yaml` | Financial news / RSS source configuration |
  | `src/` | Core application logic |
  | `scripts/` | Execution and utility scripts |
  | `data/` | Local database directory, not committed to GitHub |
  | `logs/` | Local runtime logs, not committed to GitHub |
  | `reports/` | Generated daily briefings, not committed to GitHub |
  | `requirements.txt` | Python dependency list |
  | `.gitignore` | Git ignore rules |

  ---

  ## Source Configuration

  News sources are configured in:

  ```text
  config/sources.yaml
  ```

  Example:

  ```yaml
  sources:
    - name: Yahoo Finance
      type: rss
      url: https://finance.yahoo.com/news/rssindex

    - name: CNBC Markets
      type: rss
      url: https://www.cnbc.com/id/100003114/device/rss/rss.html
  ```

  To add new financial information sources, update `config/sources.yaml` without changing the core application code.

  ---

  ## Installation

  Clone the repository and enter the project directory:

  ```bash
  cd daily-investment-agent
  ```

  Create a virtual environment:

  ```bash
  python3 -m venv .venv
  ```

  Activate the virtual environment:

  ```bash
  source .venv/bin/activate
  ```

  Install dependencies:

  ```bash
  pip install -r requirements.txt
  ```

  ---

  ## Usage

  Depending on the script structure, the project can usually be run with:

  ```bash
  python scripts/run_daily.py
  ```

  Or through the main module:

  ```bash
  python -m src.main
  ```

  Please refer to the scripts inside the `scripts/` directory for the actual entry points.

  ---

  ## Output

  After running the project, it may generate:

  ```text
  data/db/news.db
  reports/YYYY-MM-DD.md
  logs/
  ```

  Where:

  - `data/db/news.db` is the local SQLite database
  - `reports/YYYY-MM-DD.md` is the generated daily investment briefing
  - `logs/` contains runtime logs

  These are local runtime files and should not be committed to GitHub.

  ---

  ## GitHub Commit Rules

  This repository should only store source code, configuration files, and documentation.

  Files and folders that should be committed:

  ```text
  config/
  scripts/
  src/
  README.md
  requirements.txt
  .gitignore
  ```

  Files and folders that should not be committed:

  ```text
  data/
  logs/
  reports/
  .venv/
  .env
  __pycache__/
  ```

  This prevents local databases, runtime logs, generated reports, virtual environments, and sensitive credentials from being uploaded.

  ---

  ## Workflow

  The current workflow is:

  ```text
  Read config/sources.yaml
        ↓
  Fetch RSS / financial news
        ↓
  Parse title, URL, source, and published time
        ↓
  Store data in a local SQLite database
        ↓
  Deduplicate and organize records
        ↓
  Generate a Markdown daily investment briefing
  ```

  ---

  ## Roadmap

  Planned improvements include:

  - Add more financial news sources
  - Add keyword monitoring
  - Add watchlists for stocks, sectors, and assets
  - Add news importance scoring
  - Add AI-powered summarization and market impact analysis
  - Add sentiment analysis
  - Add email, Telegram, Notion, or other notification channels
  - Add scheduled execution for daily automation
  - Add a web dashboard for browsing historical news and reports

  ---

  ## Suggested Extensions

  ### 1. Keyword Configuration

  A new configuration file can be added:

  ```text
  config/keywords.yaml
  ```

  It can be used to manage watched stocks, sectors, macro themes, and custom keywords.

  ### 2. AI Summarization

  Future versions can integrate with LLM APIs to summarize news into:

  ```text
  Title
  Summary
  Related assets
  Potential market impact
  Risk notes
  Importance score
  ```

  ### 3. Scheduled Execution

  The project can be scheduled to run automatically every day using:

  - `cron`
  - `launchd`
  - GitHub Actions

  ### 4. Notification Delivery

  Daily briefings can be delivered to:

  - Email
  - Telegram
  - Notion
  - Slack
  - Feishu / Lark

  ---

  ## Disclaimer

  This project is not an investment advisory tool. It is designed to help collect and organize publicly available market information. The generated content should not be used as the sole basis for investment decisions.

  ---

  ## License

  This project is currently intended for personal learning and research. A formal open-source license can be added later if needed.
