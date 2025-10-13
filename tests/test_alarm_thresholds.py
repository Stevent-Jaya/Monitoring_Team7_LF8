import alarm

def test_soft_and_hard(monkeypatch, tmp_path):
    # log to a temp file (don’t write in repo root)
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))

    # mock Mailjet HTTP call so CI doesn’t send email
    sent = {"count": 0}
    def fake_post(url, auth=None, json=None, timeout=None):
        sent["count"] += 1
        class Resp: status_code = 200; text = "OK"
        return Resp()

    # provide env vars so _mailjet_env_ready() is true
    monkeypatch.setenv("MAILJET_API_KEY", "x")
    monkeypatch.setenv("MAILJET_API_SECRET", "y")
    monkeypatch.setenv("MAIL_FROM", "from@example.com")
    monkeypatch.setenv("MAIL_TO", "to@example.com")

    # patch requests.post inside alarm
    monkeypatch.setattr(alarm, "requests", type("R", (), {"post": fake_post}))

    # OK → no email
    assert alarm.check_limits(50, 80, 95, "mem") == "OK"
    # SOFT → no email
    assert alarm.check_limits(85, 80, 95, "mem") == "SOFT_WARNING"
    # HARD → one email
    assert alarm.check_limits(99, 80, 95, "mem") == "HARD_ALARM"
    assert sent["count"] == 1
