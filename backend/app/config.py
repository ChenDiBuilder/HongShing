from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    database_url: str = "postgresql+asyncpg://fting@localhost:5432/hongshing"
    cors_origins: str = "http://localhost:3500,http://localhost:3501"

    # Bearer token for the /mcp agent tool surface (Act 2). Empty = the mount
    # answers 404 and the agent channel is off for this restaurant.
    mcp_service_token: str = ""

    # URL path prefix the app is served under (PRD-12 / SCRUM-77). Empty for the
    # per-box model (nginx serves at the host root); the strip_demo_prefix
    # middleware is a no-op when this is "". Set DEMO_PREFIX only for a legacy
    # path-prefixed host.
    demo_prefix: str = ""

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

    @property
    def cookie_secure(self) -> bool:
        """Session cookies require HTTPS (Secure flag) in production. In dev the app
        is served over http://localhost, where a Secure cookie is silently dropped —
        so only enforce Secure when APP_ENV=production."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

