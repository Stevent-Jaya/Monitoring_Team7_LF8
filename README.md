# Server Monitoring (Team 7)

Two-stage server monitoring in Python with **real system metrics** (disk, memory, process count, logged-in users), **logging**, and **Mailjet email alerts**.
Comes with a full **CI pipeline** (lint, type-check, tests + coverage, security scan, build) and is ready for **CD** to a server.

## Features

* **Metrics (live via `psutil`)**

  * Disk usage % (`disk_usage` with `-p` path)
  * Memory usage % (`memory_usage`)
  * Process count (`process_count`)
  * Logged-in users (`user_count`, info-only)
* **Two-stage alarm**

  * **Soft warning** → log only
  * **Hard alarm** → log + **Mailjet email** (subject includes metric/current/limits/host)
* **Run everything in one command** (`all`)

  * Optionally **one summary email** instead of multiple messages (`--one-email`)
* **Logging**

  * Appends lines like
    `[YYYY-MM-DD HH:MM:SS] Host: NAME | LEVEL: SOFT_WARNING | INFO: ... | VALUE: 85 | HARD_LIMIT: 95`
* **Config via `.env`**

  * `MAILJET_API_KEY`, `MAILJET_API_SECRET`, `MAIL_FROM`, `MAIL_TO`, `MONITOR_LOG`
* **CI (GitHub Actions)**

  * `ruff`, `mypy`, `pytest` + coverage gate, `bandit`, `pip-audit`, build wheel/sdist
* **Ready for CD**

  * Build artifact (`dist/*.whl`) installable on a server; sample systemd/cron/Task Scheduler flows below

---

## Quick start

### 1) Requirements

* Python 3.10+
* `pip`, `venv`
* (Optional) Mailjet account with verified sender

### 2) Local install (from source)

```bash
python -m venv .venv
source .venv/bin/activate         # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3) Configure Mailjet (optional but recommended)

Create `.env` in the project root (same folder you run commands from):

```
MAILJET_API_KEY=your-api-key
MAILJET_API_SECRET=your-api-secret
MAIL_FROM=verified-sender@example.com
MAIL_TO=recipient@example.com
MAIL_SENDER_NAME=Server Monitor
# optional custom log path
MONITOR_LOG=server_monitoring.log
```

> If `.env` is missing, the app still runs and logs, but emails are skipped with a warning.

### 4) Run checks

Single metric (with sensible defaults):

```bash
# Disk (defaults: soft=80, hard=95; Linux path /, Windows auto-maps / -> C:\)
python monitoring1.py disk_usage
python monitoring1.py disk_usage -p C:\

# Memory (defaults: soft=80, hard=90)
python monitoring1.py memory_usage

# Processes (defaults: soft=150, hard=220)
python monitoring1.py process_count

# Users (info only, no thresholds)
python monitoring1.py user_count
```

Run **all** in one command, send **one summary email** if any hard alarm:

```bash
python monitoring1.py all --one-email
# override disk path if needed:
python monitoring1.py all --one-email -p C:\
```

---

## CLI reference

```
usage: monitoring1.py {all,disk_usage,process_count,user_count,memory_usage} [options]

Options:
  -s,  --soft-limit FLOAT   Soft limit (per-metric default if omitted)
  -hl, --hard-limit FLOAT   Hard limit (per-metric default if omitted)
  -p,  --path PATH          Disk path (disk_usage only), e.g. /var or C:\
       --one-email          In 'all' mode: suppress per-metric emails, send one summary
  -h,  --help               Show help
```

**Per-metric defaults**

| Metric        | Soft | Hard | Notes                 |
| ------------- | ---- | ---- | --------------------- |
| disk_usage    | 80   | 95   | Path `/` (or `C:\`)   |
| memory_usage  | 80   | 90   | System-wide           |
| process_count | 150  | 220  | Count of running PIDs |
| user_count    | —    | —    | Info-only, logs users |

---

## Email format (Mailjet)

* **Subject (single metric):**
  `🔴 HARD_ALARM: Memory Usage (%) | current=93.4 (soft=80.0, hard=90.0) on HOSTNAME`

* **Body (single metric):**

  ```
  Machine:  HOSTNAME
  Time:     2025-10-14 10:30:05
  Level:    HARD_ALARM
  Metric:   Memory Usage (%)
  Current:  93.4
  Soft:     80.0
  Hard:     90.0
  ```

* **Summary email (all checks):**

  ```
  Subject: 🔴 Monitoring summary on HOSTNAME — HARD=1, SOFT=1, OK=1

  Machine:  HOSTNAME
  Time:     2025-10-14 10:30:05

  Metric Status:
    🔴 Disk (/): current=96.7 (soft=80.0, hard=95.0) — HARD_ALARM
    🟠 Memory: current=85.1 (soft=80.0, hard=90.0) — SOFT_WARNING
    🟢 Processes: current=104 (soft=150.0, hard=220.0) — OK
  ```

---

## Run on a schedule (prod-like)

### Linux (cron)

```cron
*/5 * * * * cd /opt/monitoring && . .venv/bin/activate && \
  python monitoring1.py all --one-email -p / >> /var/log/monitoring/cron.log 2>&1
```

### Linux (systemd) — suggested for servers

Create a service and timer (as root), then enable the timer:

```
sudo systemctl daemon-reload
sudo systemctl enable --now monitoring.timer
```

> Keep your environment in `/etc/monitoring/env` (MAILJET_*, MONITOR_LOG, …).

### Windows (Task Scheduler)

Create a task that runs every 5 minutes:

```
<path>\.venv\Scripts\python.exe <repo>\monitoring1.py all --one-email -p C:\
```

---

## Development

### Repo layout

```
.
├─ monitoring1.py        # CLI + collectors + 'all' summary
├─ alarm.py              # two-stage alarm, logging, Mailjet, summary email
├─ requirements.txt      # runtime
├─ requirements-dev.txt  # dev tools (pytest, ruff, mypy, bandit, etc.)
├─ pyproject.toml        # package metadata & entry point (monitoring)
└─ .github/workflows/ci.yml
```

### Run the full pipeline locally

```bash
ruff check .
mypy .
pytest -q --cov=. --cov-report=term-missing
bandit -r alarm.py monitoring1.py
pip-audit -r requirements.txt || true
python -m build
```

### Install from the build (wheel)

```bash
python -m venv .venv
source .venv/bin/activate
pip install dist/server_monitoring_team7-*.whl
monitoring --help   # installed console script
```

---

## Continuous Integration / (optional) Deployment

* On each push/PR, **GitHub Actions** runs:

  * Lint (`ruff`)
  * Type-check (`mypy`)
  * Tests + coverage gate (pytest + `--cov-fail-under=80`)
  * Security scan (`bandit`) — app code only
  * Dependency audit (`pip-audit`, non-blocking)
  * Build (wheel + sdist) and upload `dist/` artifact

* **CD (Optional)**
  Add a `deploy_prod` job that copies `dist/*.whl` to a server over SSH, installs into a venv, and restarts a `systemd` timer. See `docs/` (or ask for a ready-made job snippet).

---

## Troubleshooting

* **“.env not detected”**
  Ensure the file is named exactly `.env` (no `.txt`), lives in the **current working directory**, and contains `KEY=value` lines. You can also set env vars in your shell/session.

* **Windows path**
  Use `-p C:\` for disk. If you pass `/`, the code auto-maps to `C:\` on Windows.

* **No email sent**
  Check console for `WARN: Mailjet env vars not set`. Verify sender is **verified** in Mailjet.

* **“monitoring: command not found”**
  Use the venv’s PATH or run `python monitoring1.py ...`. The `monitoring` command is available after installing the wheel.

---

## License

Choose one (e.g., MIT). Add a `LICENSE` file.

---

## Acknowledgements

* `psutil`, `requests`, `python-dotenv`
* GitHub Actions for CI

---

If you want, I can also generate **Mermaid/PlantUML diagrams** for:

* the **pipeline sequence** (Dev → push → CI jobs → build → optional deploy), and
* a **class/interaction diagram** (CLI → collectors → alarm → email/log).
