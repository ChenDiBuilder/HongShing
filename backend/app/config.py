from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    database_url: str = "postgresql+asyncpg://fting@localhost:5432/hongshing"
    cors_origins: str = "http://localhost:3500,http://localhost:3501"

    aws_region: str = "us-east-1"
    s3_bucket: str = "hongshing-assets"
    cloudfront_url: str = ""
    sqs_queue_url: str = ""

    sns_sender_id: str = "HongShing"
    sns_origination_number: str = ""
    # SMS-only region override. Empty -> aws_region. Set to the region where the
    # SNS account is out of sandbox and the origination number lives (us-east-2),
    # while the rest of the app (S3, instance) stays in aws_region (us-east-1).
    sns_region: str = ""

    owner_email: str = "owner@hongshing.com"

    # OTP pepper for hashing phone/IP before storing in rate limit table
    otp_pepper: str = "change-me-in-production"

    # Hardcoded OTP for development/testing — set to empty string to disable
    hardcoded_otp: str = "111111"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

