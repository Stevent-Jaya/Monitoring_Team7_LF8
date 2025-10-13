from types import SimpleNamespace
import builtins
import requests
import importlib

def test_hard_email_skipped_when_env_missing(monkeypatch, tmp_path):
    # no Mailjet env vars set → skip send branch
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))
    import alarm; importlib.reload(alarm)
    # hard breach still returns HARD_ALARM, but no email attempt
    assert alarm.check_limits(99, 80, 95, "mem") == "HARD_ALARM"

def test_logfile_write_error(monkeypatch, tmp_path):
    # force _log_message file write to raise OSError
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))
    import alarm; importlib.reload(alarm)

    real_open = builtins.open
    def boom(*a, **k):  # raise once, then fall back so later writes work
        builtins.open = real_open
        raise OSError("nope")
    builtins.open = boom
    # soft branch still returns SOFT_WARNING despite log-write issue
    assert alarm.check_limits(85, 80, 95, "mem") == "SOFT_WARNING"

def test_mailjet_non_200(monkeypatch, tmp_path):
    # cover non-200 response path
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))
    monkeypatch.setenv("MAILJET_API_KEY", "x")
    monkeypatch.setenv("MAILJET_API_SECRET", "y")
    monkeypatch.setenv("MAIL_FROM", "from@example.com")
    monkeypatch.setenv("MAIL_TO", "to@example.com")
    import alarm; importlib.reload(alarm)

    def fake_post(url, auth=None, json=None, timeout=None):
        return SimpleNamespace(status_code=400, text="Bad Request")
    alarm.requests = SimpleNamespace(post=fake_post)

    assert alarm.check_limits(99, 80, 95, "mem") == "HARD_ALARM"

def test_mailjet_exception(monkeypatch, tmp_path):
    # cover RequestException path
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))
    monkeypatch.setenv("MAILJET_API_KEY", "x")
    monkeypatch.setenv("MAILJET_API_SECRET", "y")
    monkeypatch.setenv("MAIL_FROM", "from@example.com")
    monkeypatch.setenv("MAIL_TO", "to@example.com")
    import alarm; importlib.reload(alarm)

    def boom(*a, **k):
        raise requests.RequestException("net down")
    alarm.requests = SimpleNamespace(post=boom)

    assert alarm.check_limits(99, 80, 95, "mem") == "HARD_ALARM"
