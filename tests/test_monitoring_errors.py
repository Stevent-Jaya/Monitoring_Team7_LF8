import monitoring1 as mon

def test_unknown_data_type():
    assert mon.monitor_data("not_a_metric", 80.0, 95.0) == "ERROR"

def test_disk_usage_bad_path():
    # invalid path → get_disk_usage returns None → monitor_data returns "ERROR"
    status = mon.monitor_data("disk_usage", 80.0, 95.0, path="/this/does/not/exist")
    assert status == "ERROR"
