# monitoring1.py

import argparse
import sys
import os
from typing import Optional, List

import psutil
from alarm import check_limits, log_current_users, send_summary_email, Result

# -------- Per-metric defaults --------
DEFAULTS = {
    "disk_usage":   {"soft": 80.0,  "hard": 95.0,  "path": "/"},
    "memory_usage": {"soft": 80.0,  "hard": 90.0,  "path": None},
    "process_count":{"soft": 150.0, "hard": 220.0, "path": None},
    "user_count":   {"soft": None,  "hard": None,  "path": None},
}

# -------- Collectors --------
def get_disk_usage(path: str = "/") -> Optional[float]:
    """Return disk usage percent for a filesystem path (0..100)."""
    try:
        if os.name == "nt" and path == "/":
            path = "C:\\"
        return float(psutil.disk_usage(path).percent)
    except FileNotFoundError:
        print(f"ERROR: File system path '{path}' not found.")
        return None
    except Exception as e:
        print(f"ERROR during disk usage check: {e}")
        return None

def get_process_count() -> int:
    """Return number of running processes."""
    return len(psutil.pids())

def get_memory_usage() -> float:
    """Return system-wide memory usage percent (0..100)."""
    return float(psutil.virtual_memory().percent)

# -------- Single-metric runner --------
def monitor_data(data_type: str, soft_limit: float, hard_limit: float, path: Optional[str] = None) -> str:
    """Collect data for one metric, run the alarm check, and return the status."""
    dt = data_type.lower()
    current_value: Optional[float] = None
    info_text = f"Measurement: {data_type}"

    if dt == "disk_usage":
        selected_path = path if path is not None else "/"
        current_value = get_disk_usage(selected_path)
        info_text = f"Disk Usage (%) on {selected_path}"
    elif dt == "process_count":
        current_value = float(get_process_count())
        info_text = "Running Process Count"
    elif dt == "memory_usage":
        current_value = get_memory_usage()
        info_text = "Memory Usage (%)"
    elif dt == "user_count":
        print("\n--- User Logging (INFO ONLY) ---")
        log_current_users()
        return "USER_LOGGED"
    else:
        print(f"ERROR: Unknown data type '{data_type}'. Use 'disk_usage', 'process_count', 'memory_usage' or 'user_count'.")
        return "ERROR"

    if current_value is None:
        return "ERROR"

    print(f"\n--- Checking {info_text} (Current Value: {current_value}) ---")
    return check_limits(current_value, soft_limit, hard_limit, info_text)

# -------- All-metrics runner --------
def monitor_all(disk_path: Optional[str] = None, *, send_one_email: bool = True) -> str:
    """
    Run disk, memory, process, and user checks.
    If send_one_email=True, suppress per-metric emails and send one summary if any HARD_ALARM.
    """
    results: List[Result] = []

    # Disk
    d = DEFAULTS["disk_usage"]
    disk_selected = disk_path if disk_path is not None else d["path"]
    dv = get_disk_usage(disk_selected)
    if dv is not None:
        lvl = check_limits(float(dv), float(d["soft"]), float(d["hard"]),
                           f"Disk Usage (%) on {disk_selected}",
                           trigger_email=not send_one_email)
        results.append({
            "metric": f"Disk ({disk_selected})",
            "level": lvl,
            "current": float(dv),
            "soft": float(d["soft"]),
            "hard": float(d["hard"]),
        })

    # Memory
    m = DEFAULTS["memory_usage"]
    mv = get_memory_usage()
    lvl = check_limits(float(mv), float(m["soft"]), float(m["hard"]),
                       "Memory Usage (%)",
                       trigger_email=not send_one_email)
    results.append({
        "metric": "Memory",
        "level": lvl,
        "current": float(mv),
        "soft": float(m["soft"]),
        "hard": float(m["hard"]),
    })

    # Processes
    p = DEFAULTS["process_count"]
    pv = float(get_process_count())
    lvl = check_limits(float(pv), float(p["soft"]), float(p["hard"]),
                       "Running Process Count",
                       trigger_email=not send_one_email)
    results.append({
        "metric": "Processes",
        "level": lvl,
        "current": float(pv),
        "soft": float(p["soft"]),
        "hard": float(p["hard"]),
    })

    # Users (info-only)
    print("\n--- User Logging (INFO ONLY) ---")
    log_current_users()

    if send_one_email:
        # one summary email if any HARD alarm occurred (change only_hard=False to always send)
        send_summary_email(results, only_hard=True)

    if any(r["level"] == "HARD_ALARM" for r in results):
        return "HARD_ALARM"
    if any(r["level"] == "SOFT_WARNING" for r in results):
        return "SOFT_WARNING"
    return "OK"

# -------- CLI --------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Server Monitoring Tool mit zweistufigem Alarmsystem.",
        epilog=(
            "Beispiele:\n"
            "  python monitoring1.py all --one-email        # alle Checks, eine Sammelmail bei HARD\n"
            "  python monitoring1.py disk_usage             # Standard-Limits & Pfad\n"
            "  python monitoring1.py memory_usage -s 80 -hl 92\n"
            "  python monitoring1.py process_count          # Standard-Limits\n"
            "  python monitoring1.py user_count             # loggt nur eingeloggte Nutzer"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "data_type",
        choices=["all", "disk_usage", "process_count", "user_count", "memory_usage"],
        help="Messdaten oder 'all' (alle Checks).",
    )
    parser.add_argument("-s", "--soft-limit", type=float, default=None,
                        help="Soft-Limit; Standard pro Metrik, wenn weggelassen.")
    parser.add_argument("-hl", "--hard-limit", type=float, default=None,
                        help="Hard-Limit; Standard pro Metrik, wenn weggelassen.")
    parser.add_argument("-p", "--path", type=str, default=None,
                        help="Pfad für Plattennutzung (z.B. C:\\ oder /var).")
    parser.add_argument("--one-email", action="store_true",
                        help="Bei 'all': pro-Metrik-Emails unterdrücken und eine Sammelmail senden.")

    args = parser.parse_args()
    metric = args.data_type.lower()

    if metric == "all":
        status = monitor_all(disk_path=args.path, send_one_email=args.one_email)
        print(f"\nOverall status: {status}")
        return

    # Per-metric defaults when flags omitted
    defaults = DEFAULTS.get(metric, {})
    soft = args.soft_limit if args.soft_limit is not None else defaults.get("soft")
    hard = args.hard_limit if args.hard_limit is not None else defaults.get("hard")
    eff_path = args.path if args.path is not None else defaults.get("path")

    # For metrics that ignore limits (user_count), use numeric placeholders
    soft_f = 0.0 if soft is None else float(soft)
    hard_f = 0.0 if hard is None else float(hard)

    monitor_data(metric, soft_f, hard_f, eff_path)

if __name__ == "__main__":
    try:
        import psutil  # noqa: F401
    except ImportError:
        print("ERROR: Das Modul 'psutil' ist nicht installiert. Bitte installieren Sie es mit 'pip install psutil'.")
        sys.exit(1)
    main()
