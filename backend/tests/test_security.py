import time
from datetime import timedelta

import pytest

from app.core import security


def test_password_hash_roundtrip():
    hashed = security.hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert security.verify_password("correct horse battery staple", hashed)
    assert not security.verify_password("wrong password", hashed)


def test_verify_handles_garbage_hash():
    assert not security.verify_password("anything", "not-a-bcrypt-hash")


def test_access_token_roundtrip():
    token = security.create_access_token("user-123", "member")
    payload = security.decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "member"
    assert payload["type"] == "access"


def test_refresh_token_type():
    token = security.create_refresh_token("user-123", "admin")
    assert security.decode_token(token)["type"] == "refresh"


def test_tampered_token_rejected():
    token = security.create_access_token("user-123", "member")
    tampered = token[:-4] + ("AAAA" if token[-4:] != "AAAA" else "BBBB")
    with pytest.raises(ValueError):
        security.decode_token(tampered)


def test_expired_token_rejected(monkeypatch):
    token = security._create_token("user-123", "member", timedelta(seconds=-10), "access")
    with pytest.raises(ValueError):
        security.decode_token(token)


def test_token_signed_with_other_key_rejected(monkeypatch):
    token = security.create_access_token("user-123", "member")
    monkeypatch.setattr(security.settings, "JWT_SECRET_KEY", "a-completely-different-key")
    with pytest.raises(ValueError):
        security.decode_token(token)
