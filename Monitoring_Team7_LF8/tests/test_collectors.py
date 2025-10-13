import monitoring1 as mon

def test_collectors_return_values():
    # real system data sanity-checks
    v = mon.get_disk_usage("/")
    assert v is None or (0 <= v <= 100)
    assert mon.get_process_count() >= 1
