# Tavily Scraping Assignment — Gabriel Zackon

This repository contains my solution for Tavily’s scraping assignment.

The goal is to explore different ways of scraping and analyzing “hard” dynamic URLs (Google, Bing, realtor sites, etc.) while balancing **latency, accuracy, and cost**.

The project implements:

- A **lightweight HTTP scraper** (`aiohttp`)
- A **JS-enabled browser scraper** (Playwright / Chromium)
- A **robots.txt-aware pipeline** with persistent caching
- An **escalation policy** that decides when to send a URL from HTTP → Browser
- An **analysis notebook** with metrics, plots, and a simple **cost model**

---

## 1. Project Structure

```text
tavily-scraper/
├── src/
│   ├── __init__.py
│   ├── http_scraper.py       # aiohttp-based lightweight scraper
│   ├── browser_scraper.py    # Playwright-based JS browser scraper
│   ├── robots.py             # robots.txt cache with TTL + persistence
│   ├── utils.py              # helpers (robots_blocked_result, retryable errors, etc.)
│   ├── policy.py             # should_escalate() — HTTP → Browser escalation logic
│   ├── storage.py            # save_df() utility for writing result CSVs
│   ├── metrics.py            # FetchResult dataclass (per-URL metrics)
│   └── settings.py           # ScrapeConfig, ProxySettings, YAML config loading
│
├── notebooks/
│   └── scraper_final.ipynb   # Main analysis notebook (end-to-end pipeline)
│
├── data/
│   ├── failed_urls.example.csv    # Example input (structure only)
│   ├── ProxyURL.example.txt       # Example proxy file format
│   └── (real files are gitignored: ProxyURL.txt, failed_urls.csv, robots_cache.json)
│
├── results/                    # Per-run outputs (CSV), ignored by git
├── artifacts/                  # Optional plots/exports, ignored by git
│
├── tests/
│   ├── test_policy.py          # Unit tests for escalation policy
│   └── test_settings.py        # Unit tests for proxy/config loading
│
├── scrape_config.yaml          # Configurable knobs for HTTP/Browser/robots
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 2. Flow: From URLs to Metrics

High-level flow of the system:

```mermaid
flowchart LR
    U[Input URLs] --> C[Sampling & per-domain cap]

    C --> H[HTTP Scraper (aiohttp)]
    H --> R[RobotsCache]
    R -->|disallowed| RB[robots_blocked_result]
    R -->|allowed| HF[HTTP FetchResult]

    HF --> P[Policy: should_escalate()]
    RB --> P

    P -->|no| HONLY[HTTP-only result]
    P -->|yes| B[BrowserScraper (Playwright)]

    B --> BRES[Browser FetchResult]

    HONLY --> M[Hybrid aggregator]
    BRES --> M

    M --> A[Analysis & Plots in scraper_final.ipynb]
    A --> O[results/*.csv, cost model, histograms, scatter plots]
```

---

## 3. Setup

### 3.1. Create and activate environment

```bash
Using conda (example):
cd /path/to/tavily-scraper

conda create -n tavily python=3.11 -y
conda activate tavily
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

### 3.2. Proxy configuration

The scraper expects a proxy URL in data/ProxyURL.txt.

Example format (data/ProxyURL.example.txt):

```text
https://username:password@proxy-hostname:65535
```

Steps:

Copy the example file and fill in real credentials:

```bash
cp data/ProxyURL.example.txt data/ProxyURL.txt
# edit data/ProxyURL.txt and insert your real proxy URL
```

The loader (settings.load_proxy_from_txt) parses the URL into:

- ProxySettings.server = scheme://host:port

- ProxySettings.username / password

- .url property that reconstructs scheme://user:pass@host:port for use in aiohttp.

The real ProxyURL.txt is gitignored to avoid leaking credentials.

### 3.3. URLs input

The notebook expects data/failed_urls.csv with at least a url column.

For the assignment, Tavily provides urls.txt; in this repo I work from a CSV (failed_urls.csv)
for convenience. An example schema is given in data/failed_urls.example.csv.

Real data files are ignored by git.

### 3.4. Configuration via YAML

scrape_config.yaml controls most runtime knobs:

- HTTP:

  - concurrency, total/connect/read timeouts

  - max retries and backoff

- Browser:

  - headless mode, timeout, whether to block heavy resources

  - max number of URLs to escalate per run

- Robots cache:

  - cache file path

  - TTL in seconds

- Escalation:

  - minimum bytes threshold for HTTP before considering browser

  - whether to consider latency as a trigger

  - Defaults are loaded into ScrapeConfig via load_scrape_config() in settings.py.

---

## 4. Running the Notebook

1. Activate the environment:

```bash
conda activate tavily
```

2. Start Jupyter:

```bash
jupyter lab
# or
jupyter notebook
```

3. Open:

```text
notebooks/scraper_final.ipynb
```

4. Make sure the kernel is the tavily environment (e.g., "Python (tavily)").

5. Run All (Kernel → Restart & Run All).

The notebook will:

1. Add src/ to sys.path so imports work.

2. Load scrape_config.yaml and the proxy settings.

3. Load and sample URLs (cap per domain, then global sample).

4. Run the HTTP scraper with:

   - aiohttp client session,

   - robots-aware gating (RobotsCache),

   - retry logic for transient transport errors,

   - per-URL metrics (FetchResult).

5. Classify failures (robots, captcha, HTTP 4xx/5xx, transport error).

6. Decide which URLs to escalate to Playwright using policy.should_escalate.

7. Run the browser scraper (reusing a single Chromium process/context).

8. Build:

   - HTTP-only view

   - Browser-only view

   - Hybrid (“best of”) view

9. Compute summary metrics:

   - success rate

   - latency distribution

   - content size distribution

   - retry statistics

10. Plot:

    - latency histograms

    - failure mix bar charts

    - latency vs bytes scatter

    - bytes histograms

11. Compute a simple cost model:

    - assign relative costs to HTTP and browser calls

    - estimate cost per successful page for HTTP-only, Browser-only, and Hybrid policies.

12. Save results under results/ using storage.save_df.

---

## 5. Running Tests

From the repo root:

```bash
conda activate tavily
python -m pytest
```

Current tests cover:

    - test_policy.py:

        - Asserts that should_escalate does not escalate robots-blocked or CAPTCHA pages.

        - Verifies it does escalate HTTP errors, transport errors, and very small pages.

    - test_settings.py:

        - Ensures load_proxy_from_txt parses a full proxy URL correctly into ProxySettings.

        - Checks YAML config overrides (TTL etc.) are loaded into ScrapeConfig.

---

## 6. Notes on Design & Trade-offs

A few intentional design choices:

    - HTTP-first, browser-only-on-demand:
        Most URLs are attempted via the lightweight HTTP client; the browser is reserved for “hard” pages only, guided by the escalation policy.

    - Robots-aware but coarse:
        For this assignment, robots handling is origin-level (allow/deny for the whole host), with a TTL and persisted JSON cache to avoid re-fetching on every run.

    - Config-driven:
        Timeouts, concurrency, retry behavior, escalation thresholds, and caching behavior live in ScrapeConfig / scrape_config.yaml, so the code can be tuned without edits.

    - Simple but explicit cost model:
        Uses unit costs (HTTP=1, Browser=8 by default) to compare cost per successful page between HTTP-only, Browser-only, and Hybrid “best-of” strategy.

For more detail, see the One-pager PDF and the commentary cells in scraper_final.ipynb.

---

## 7. How a Reviewer Can Reproduce

1. Clone the repo:

```bash
git clone <this-repo-url>.git
cd tavily-scraper
```

2. Create environment & install dependencies:

```bash
conda create -n tavily python=3.11 -y
conda activate tavily
pip install -r requirements.txt
playwright install
```

3. Prepare data files:

```bash
cp data/ProxyURL.example.txt data/ProxyURL.txt
# edit ProxyURL.txt and insert real proxy URL

cp data/failed_urls.example.csv data/failed_urls.csv
# or drop in the real failed_urls.csv from the assignment
```

Run tests:

```bash
python -m pytest
```

Run notebook:

    - Open notebooks/scraper_final.ipynb

    - Select kernel “Python (tavily)”

    - Run all cells

All outputs (metrics CSVs) will land under results/, plots are visible in the notebook, and the cost model + hybrid policy are summarized in the final cells.
