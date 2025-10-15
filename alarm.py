# alarm.py
# Two-stage alarm logic + logging + Mailjet email (via HTTP API).
# Supports single-metric emails and one-shot summary emails for batch runs.

from __future__ import annotations

import os
import socket
import datetime
from typing import cast, Iterable, Literal, TypedDict

from dotenv import load_dotenv
import requests

# Load variables from .env (if present)
load_dotenv()

# ------- Configuration (env-driven) -------
LOG_FILE = os.getenv("MONITOR_LOG", "server_monitoring.log")

MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
MAILJET_API_SECRET = os.getenv("MAILJET_API_SECRET")
MAIL_FROM = os.getenv("MAIL_FROM")           # verified sender in Mailjet
MAIL_TO = os.getenv("MAIL_TO")               # recipient
MAIL_SENDER_NAME = os.getenv("MAIL_SENDER_NAME", "Server Monitor")
MAILJET_ENDPOINT = "https://api.mailjet.com/v3.1/send"


# ------- Utilities -------
def _now_str() -> str:
    return datetime.datetime.now().isoformat(sep=" ", timespec="seconds")


def _hostname() -> str:
    return socket.gethostname()


def _fmt(v: float) -> str:
    try:
        return f"{int(v)}" if float(v).is_integer() else f"{float(v):.1f}"
    except Exception:
        return str(v)


def _log_message(level: str, current_value: float, hard_limit: float, info_text: str) -> None:
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
    """Send a message via Mailjet HTTP API (v3.1). Skips if env is missing."""
    if not _mailjet_env_ready():
        print("WARN: Mailjet env vars not set; skipping email send.")
        print(f"Subject (skipped): {subject}\nBody:\n{body}")
        return

    api_key = cast(str, MAILJET_API_KEY)
    api_secret = cast(str, MAILJET_API_SECRET)
    sender = cast(str, MAIL_FROM)
    recipient = cast(str, MAIL_TO)

    payload = {
        "Messages": [{
            "From": {"Email": sender, "Name": MAIL_SENDER_NAME},
            "To": [{"Email": recipient}],
            "Subject": subject,
            "TextPart": body
        }]
    }

    try:
        resp = requests.post(
            MAILJET_ENDPOINT,
            auth=(api_key, api_secret),
            json=payload,
            timeout=20
        )
        if resp.status_code == 200:
            print(f"EMAIL SENT to {recipient} via Mailjet.")
        else:
            print(f"ERROR: Mailjet responded {resp.status_code}: {resp.text}")
    except requests.RequestException as e:
        print(f"ERROR: Mailjet request failed: {e}")


# ------- Public API -------
Level = Literal["OK", "SOFT_WARNING", "HARD_ALARM"]


def _single_subject(info_text: str, current_value: float, soft: float, hard: float, level: Level) -> str:
    emoji = "🟢" if level == "OK" else ("🟠" if level == "SOFT_WARNING" else "🔴")
    return (
        f"{emoji} {level}: {info_text} | current={_fmt(current_value)} "
        f"(soft={_fmt(soft)}, hard={_fmt(hard)}) on {_hostname()}"
    )


def _single_body(info_text: str, current_value: float, soft: float, hard: float, level: Level) -> str:
    return (
        f"Machine:  {_hostname()}\n"
        f"Time:     {_now_str()}\n"
        f"Level:    {level}\n"
        f"Metric:   {info_text}\n"
        f"Current:  {_fmt(current_value)}\n"
        f"Soft:     {_fmt(soft)}\n"
        f"Hard:     {_fmt(hard)}\n"
    )


def check_limits(
    current_value: float,
    soft_limit: float,
    hard_limit: float,
    info_text: str,
    *,
    trigger_email: bool = True,
) -> Level:
    """
    Two-stage alarm:
      - > hard_limit  -> log HARD_ALARM and (optionally) send email
      - > soft_limit  -> log SOFT_WARNING
      - else          -> print OK
    Returns: "HARD_ALARM" | "SOFT_WARNING" | "OK"

    trigger_email=False lets you run many checks and send one summary later.
    """
    if current_value > hard_limit:
        _log_message("HARD_ALARM", current_value, hard_limit, info_text)
        if trigger_email:
            subject = _single_subject(info_text, current_value, soft_limit, hard_limit, "HARD_ALARM")
            body = _single_body(info_text, current_value, soft_limit, hard_limit, "HARD_ALARM")
            _send_email(subject, body)
        return "HARD_ALARM"

    if current_value > soft_limit:
        _log_message("SOFT_WARNING", current_value, hard_limit, info_text)
        return "SOFT_WARNING"

    print(f"OK: {info_text} (Current: {current_value}) is within limits.")
    return "OK"


class Result(TypedDict):
    metric: str
    level: Level
    current: float
    soft: float
    hard: float


def send_summary_email(results: Iterable[Result], *, only_hard: bool = True) -> None:
    """
    Send a single summary email for multiple checks.
    - If only_hard=True, send only if at least one HARD_ALARM occurred.
    - If only_hard=False, always send (include SOFT/OK as well).
    """
    items = list(results)
    if not items:
        return

    any_hard = any(r["level"] == "HARD_ALARM" for r in items)
    if only_hard and not any_hard:
        print("Summary: no HARD_ALARM; not sending email.")
        return

    emoji = "🔴" if any_hard else "🟠"
    subject = f"{emoji} Monitoring summary on {_hostname()} — "
    counts = {
        "HARD_ALARM": sum(r["level"] == "HARD_ALARM" for r in items),
        "SOFT_WARNING": sum(r["level"] == "SOFT_WARNING" for r in items),
        "OK": sum(r["level"] == "OK" for r in items),
    }
    subject += f"HARD={counts['HARD_ALARM']}, SOFT={counts['SOFT_WARNING']}, OK={counts['OK']}"

    lines = [
        f"Machine:  {_hostname()}",
        f"Time:     {_now_str()}",
        "",
        "Metric Status:",
    ]
    for r in items:
        icon = "🔴" if r["level"] == "HARD_ALARM" else ("🟠" if r["level"] == "SOFT_WARNING" else "🟢")
        lines.append(
            f"  {icon} {r['metric']}: current={_fmt(r['current'])} "
            f"(soft={_fmt(r['soft'])}, hard={_fmt(r['hard'])}) — {r['level']}"
        )
    body = "\n".join(lines)
    _send_email(subject, body)


def log_current_users() -> int:
    """
    Capture and log currently logged-in users. Returns the user count.
    """
    try:
        import psutil  # local import keeps module import light if psutil is missing
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
        host = getattr(u, "host", "") or "local"
        details.append(f"{u.name}@{host} since {started}")

    info_text = f"Currently logged in users ({count}): {', '.join(details) if details else '-'}"
    # For user info, hard limit is not relevant; pass 0 for display.
    _log_message("USER_INFO", float(count), 0.0, info_text)
    return count


__all__ = ["check_limits", "send_summary_email", "log_current_users", "Result"]
