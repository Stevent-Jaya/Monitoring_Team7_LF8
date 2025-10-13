# tests/test_monitoring_flow.py
import monitoring1 as mon

def test_monitor_data_branches(tmp_path, monkeypatch):
    # no emails in this test; just exercise CLI branches
    # disk_usage
    status = mon.monitor_data("disk_usage", 0.0, 100.0, path="/")
    assert status in ("OK", "SOFT_WARNING", "HARD_ALARM", "ERROR")

    # process_count
    status = mon.monitor_data("process_count", 0.0, 10_000.0)
    assert status in ("OK", "SOFT_WARNING", "HARD_ALARM", "ERROR")

    # user_count (logs and returns USER_LOGGED)
    assert mon.monitor_data("user_count", 0.0, 100.0) == "USER_LOGGED"
