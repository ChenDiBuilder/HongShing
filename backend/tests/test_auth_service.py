import pytest
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_otp,
    hash_password,
    hash_phone,
    hash_ip,
    hash_token,
    generate_temp_password,
    verify_password,
)


class TestTokenCreation:
    def test_access_token_contains_claims(self):
        token = create_access_token("user-1", "customer")
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["role"] == "customer"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_refresh_token_contains_claims(self):
        token = create_refresh_token("user-1", "admin")
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["role"] == "admin"
        assert payload["type"] == "refresh"

    def test_token_round_trip(self):
        token = create_access_token("abc-123", "staff")
        payload = decode_token(token)
        assert payload["sub"] == "abc-123"

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            decode_token("not-a-valid-jwt")


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("secret123")
        assert hashed != "secret123"
        assert verify_password("secret123", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_hash_is_unique_per_call(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestOTPHashing:
    def test_hash_is_deterministic(self):
        assert hash_otp("123456") == hash_otp("123456")

    def test_hash_is_different_for_different_otps(self):
        assert hash_otp("123456") != hash_otp("654321")

    def test_hash_length(self):
        assert len(hash_otp("000000")) == 64  # SHA-256 hex


class TestPhoneHashing:
    def test_hash_uses_pepper(self):
        h = hash_phone("+16475551234")
        assert len(h) == 64

    def test_hash_is_deterministic(self):
        assert hash_phone("+16475551234") == hash_phone("+16475551234")

    def test_different_phones_different_hash(self):
        assert hash_phone("+16475551234") != hash_phone("+16475559876")


class TestIPHashing:
    def test_hash_length(self):
        assert len(hash_ip("127.0.0.1")) == 64

    def test_hash_is_deterministic(self):
        assert hash_ip("192.168.1.1") == hash_ip("192.168.1.1")


class TestTokenHashing:
    def test_token_hash_consistent(self):
        t = "token-value"
        assert hash_token(t) == hash_token(t)

    def test_different_tokens_different_hash(self):
        assert hash_token("a") != hash_token("b")


class TestTempPassword:
    def test_generates_string(self):
        pw = generate_temp_password()
        assert isinstance(pw, str)
        assert len(pw) > 8

    def test_unique_per_call(self):
        assert generate_temp_password() != generate_temp_password()
