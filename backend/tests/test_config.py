import os

from app.config import Settings


class TestConfig:
    def test_defaults(self):
        """Settings load with sensible defaults."""
        s = Settings()
        assert s.app_env == "development"
        assert s.aws_region == "us-east-1"
        assert s.sns_sender_id == "HongShing"

    def test_env_override(self, monkeypatch):
        """Environment variables override defaults."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("OWNER_EMAIL", "test@example.com")

        s = Settings()
        assert s.app_env == "production"
        assert s.secret_key == "test-secret"
        assert s.owner_email == "test@example.com"

    def test_otp_pepper_exists(self):
        """OTP pepper is always configured."""
        s = Settings()
        assert isinstance(s.otp_pepper, str)
        assert len(s.otp_pepper) > 0
