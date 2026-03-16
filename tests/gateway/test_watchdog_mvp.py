from gateway.watchdog import GatewayWatchdog, WatchdogConfig


def test_watchdog_triggers_429_backoff():
    wd = GatewayWatchdog(WatchdogConfig(window_seconds=300, threshold_429=2))
    wd.record_error_code("429")
    wd.record_error_code("429")
    snap = wd.snapshot()
    assert snap["trigger_429"] is True
    assert snap["action"] == "rate_limit_backoff"
