# tests/test_alarm_thresholds.py
from types import SimpleNamespace
import importlib

def test_soft_and_hard(monkeypatch, tmp_path):
    # log to temp file
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))

    # Provide env vars so _mailjet_env_ready() is true **before importing alarm**
    monkeypatch.setenv("MAILJET_API_KEY", "x")
    monkeypatch.setenv("MAILJET_API_SECRET", "y")
    monkeypatch.setenv("MAIL_FROM", "from@example.com")
    monkeypatch.setenv("MAIL_TO", "to@example.com")

    # Import/reload alarm *after* env is set so it sees the values
    import alarm
    importlib.reload(alarm)

    sent = {"count": 0}
    def fake_post(url, auth=None, json=None, timeout=None):
        sent["count"] += 1
        return SimpleNamespace(status_code=200, text="OK")

    # Patch requests.post inside alarm
    alarm.requests = SimpleNamespace(post=fake_post)

    assert alarm.check_limits(50, 80, 95, "mem") == "OK"
    assert alarm.check_limits(85, 80, 95, "mem") == "SOFT_WARNING"
    assert alarm.check_limits(99, 80, 95, "mem") == "HARD_ALARM"
    assert sent["count"] == 1
