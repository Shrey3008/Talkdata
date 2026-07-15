from app.core.rate_limit import _allow, _hits


def setup_function():
    _hits.clear()


def test_allows_up_to_limit():
    for _ in range(5):
        assert _allow("u1", limit=5, window_seconds=60) is None


def test_blocks_over_limit_with_retry_hint():
    for _ in range(3):
        _allow("u1", limit=3, window_seconds=60)
    retry_in = _allow("u1", limit=3, window_seconds=60)
    assert retry_in is not None and 0 < retry_in <= 60


def test_isolated_per_user():
    for _ in range(3):
        _allow("u1", limit=3, window_seconds=60)
    assert _allow("u2", limit=3, window_seconds=60) is None


def test_window_slides(monkeypatch):
    import app.core.rate_limit as rl

    t = [1000.0]
    monkeypatch.setattr(rl.time, "monotonic", lambda: t[0])
    for _ in range(3):
        assert rl._allow("u1", limit=3, window_seconds=60) is None
    assert rl._allow("u1", limit=3, window_seconds=60) is not None
    t[0] += 61  # window passes
    assert rl._allow("u1", limit=3, window_seconds=60) is None
