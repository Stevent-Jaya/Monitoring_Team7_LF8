# tests/test_users_logging.py
def test_log_current_users(monkeypatch, tmp_path):
    monkeypatch.setenv("MONITOR_LOG", str(tmp_path / "monitor.log"))
    import alarm
    count = alarm.log_current_users()
    assert isinstance(count, int)
    assert count >= 0
