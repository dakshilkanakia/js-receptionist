from app.agent.limits import CallLimiter


def test_concurrent_cap():
    lim = CallLimiter(max_concurrent=2, per_ip_per_hour=100)
    lim.start("a"); lim.start("b")
    assert "other calls" in lim.check("c")
    lim.end()
    assert lim.check("c") is None


def test_per_ip_hourly_cap():
    lim = CallLimiter(max_concurrent=100, per_ip_per_hour=2)
    for _ in range(2):
        assert lim.check("a") is None
        lim.start("a"); lim.end()
    assert "limit" in lim.check("a")
    assert lim.check("b") is None  # other callers unaffected


def test_old_calls_age_out(monkeypatch):
    import app.agent.limits as limits
    lim = CallLimiter(max_concurrent=100, per_ip_per_hour=1)
    now = 1_000_000.0
    monkeypatch.setattr(limits.time, "time", lambda: now)
    lim.start("a"); lim.end()
    assert lim.check("a")
    monkeypatch.setattr(limits.time, "time", lambda: now + 3601)
    assert lim.check("a") is None


def test_end_never_negative():
    lim = CallLimiter(max_concurrent=1, per_ip_per_hour=1)
    lim.end()
    assert lim.active == 0
