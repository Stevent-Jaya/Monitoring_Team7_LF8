# tests/test_alarm_edges.py
from types import SimpleNamespace
import importlib
import builtins
import requests


def test_hard_email_skipped_when_env_missing(monkeypatch, tmp_path):
    # No Mailjet env vars set -> skip send branch
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))

    import alarm
    importlib.reload(alarm)

    # Hard breach still returns HARD_ALARM, but no email attempt
    assert alarm.check_limits(99, 80, 95, "mem") == "HARD_ALARM"


def test_logfile_write_error(monkeypatch, tmp_path):
    # Force _log_message file write to raise OSError
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))

    import alarm
    importlib.reload(alarm)

    def boom(*args, **kwargs):
        raise OSError("nope")

    # Use monkeypatch to replace builtins.open just for this test
    monkeypatch.setattr(builtins, "open", boom)

    # Soft branch still returns SOFT_WARNING despite log-write issue
    assert alarm.check_limits(85, 80, 95, "mem") == "SOFT_WARNING"


def test_mailjet_non_200(monkeypatch, tmp_path):
    # Cover non-200 response path
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))
    monkeypatch.setenv("MAILJET_API_KEY", "x")
    monkeypatch.setenv("MAILJET_API_SECRET", "y")
    monkeypatch.setenv("MAIL_FROM", "from@example.com")
    monkeypatch.setenv("MAIL_TO", "to@example.com")

    import alarm
    importlib.reload(alarm)

    def fake_post(url, auth=None, json=None, timeout=None):
        return SimpleNamespace(status_code=400, text="Bad Request")

    alarm.requests = SimpleNamespace(post=fake_post)

    assert alarm.check_limits(99, 80, 95, "mem") == "HARD_ALARM"


def test_mailjet_exception(monkeypatch, tmp_path):
    # Cover RequestException path
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))
    monkeypatch.setenv("MAILJET_API_KEY", "x")
    monkeypatch.setenv("MAILJET_API_SECRET", "y")
    monkeypatch.setenv("MAIL_FROM", "from@example.com")
    monkeypatch.setenv("MAIL_TO", "to@example.com")

    import alarm
    importlib.reload(alarm)

    def boom(*args, **kwargs):
        raise requests.RequestException("net down")

    alarm.requests = SimpleNamespace(post=boom)

    assert alarm.check_limits(99, 80, 95, "mem") == "HARD_ALARM"
