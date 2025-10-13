# alarm.py
# Two-stage alarm logic + logging + Mailjet email (via HTTP API).
# Secrets come from environment variables, not hardcoded.

from __future__ import annotations

import os
import socket
import datetime
from dotenv import load_dotenv
import requests

#load variables from local .env
load_dotenv()
# ------- Configuration (env-driven) -------

# Log file path (default in repo root)
LOG_FILE = os.getenv("MONITOR_LOG", "server_monitoring.log")

# Mail/alerts
MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
MAILJET_API_SECRET = os.getenv("MAILJET_API_SECRET")
MAIL_FROM = os.getenv("MAIL_FROM")          # verified sender in Mailjet
MAIL_TO = os.getenv("MAIL_TO")              # recipient
MAIL_SENDER_NAME = os.getenv("MAIL_SENDER_NAME", "Server Monitor")
MAILJET_ENDPOINT = "https://api.mailjet.com/v3.1/send"


# ------- Internal helpers -------

def _now_str() -> str:
    return datetime.datetime.now().isoformat(sep=" ", timespec="seconds")


def _hostname() -> str:
    return socket.gethostname()


def _log_message(level: str, current_value: float, hard_limit: float, info_text: str) -> None:
    """
    Append a line to the log file and echo to stdout.
    Format example:
      [2025-10-10 12:34:56] Host: MYPC | LEVEL: SOFT_WARNING | INFO: mem | VALUE: 85 | HARD_LIMIT: 95
    """
    line = (
        f"[{_now_str()}] Host: {_hostname()} | LEVEL: {level} | "
        f"INFO: {info_text} | VALUE: {current_value} | HARD_LIMIT: {hard_limit}"
    )
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as e:
        print(f"ERROR: could not write log file '{LOG_FILE}': {e}")
    print(f"LOGGED: {line}")


def _mailjet_env_ready() -> bool:
    return bool(MAILJET_API_KEY and MAILJET_API_SECRET and MAIL_FROM and MAIL_TO)


def _send_email(subject: str, body: str) -> None:
    """
    Send a message via Mailjet HTTP API (v3.1).
    Skips sending if required env vars are missing.
    """
    if not _mailjet_env_ready():
        print("WARN: Mailjet env vars not set; skipping email send.")
        print(f"Subject (skipped): {subject}\nBody:\n{body}")
        return

    payload = {
        "Messages": [{
            "From": {"Email": MAIL_FROM, "Name": MAIL_SENDER_NAME},
            "To": [{"Email": MAIL_TO}],
            "Subject": subject,
            "TextPart": body
        }]
    }

    try:
        resp = requests.post(
            MAILJET_ENDPOINT,
            auth=(MAILJET_API_KEY, MAILJET_API_SECRET),
            json=payload,
            timeout=20
        )
        if resp.status_code == 200:
            print(f"HARD-LIMIT ALARM - Email sent to {MAIL_TO} via Mailjet.")
        else:
            print(f"ERROR: Mailjet responded {resp.status_code}: {resp.text}")
    except requests.RequestException as e:
        print(f"ERROR: Mailjet request failed: {e}")


# ------- Public API (used by monitoring1.py) -------

def check_limits(current_value: float, soft_limit: float, hard_limit: float, info_text: str) -> str:
    """
    Two-stage alarm:
      - > hard_limit  -> log HARD_ALARM and send Mailjet email
      - > soft_limit  -> log SOFT_WARNING
      - else          -> print OK
    Returns: "HARD_ALARM" | "SOFT_WARNING" | "OK"
    """
    if current_value > hard_limit:
        _log_message("HARD_ALARM", current_value, hard_limit, info_text)
        subject = f"CRITICAL: {info_text} exceeded hard limit on {_hostname()}"
        body = (
            f"Machine: {_hostname()}\n"
            f"Time:    {_now_str()}\n"
            f"Metric:  {info_text}\n"
            f"Value:   {current_value}\n"
            f"Hard:    {hard_limit}\n"
        )
        _send_email(subject, body)
        return "HARD_ALARM"

    if current_value > soft_limit:
        _log_message("SOFT_WARNING", current_value, hard_limit, info_text)
        return "SOFT_WARNING"

    print(f"OK: {info_text} (Current: {current_value}) is within limits.")
    return "OK"


def log_current_users() -> int:
    """
    Log currently logged-in users. Returns the user count.
    """
    try:
        import psutil  # local import to keep module import light if psutil is missing
    except ImportError:
        print("WARNING: psutil is required for user logging.")
        return 0

    users = psutil.users()
    count = len(users)
    details = []
    for u in users:
        try:
            started = datetime.datetime.fromtimestamp(u.started).strftime("%H:%M")
        except Exception:
            started = "?"
        details.append(f"{u.name}@{getattr(u, 'host', '') or 'local'} since {started}")

    info_text = f"Currently logged in users ({count}): {', '.join(details) if details else '-'}"
    # For user info, hard limit is not relevant; pass 0 for display.
    _log_message("USER_INFO", float(count), 0.0, info_text)
    return count


__all__ = ["check_limits", "log_current_users"]
