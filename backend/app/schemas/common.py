from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# --- Auth ---

class SendOTPRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15, examples=["+16475551234", "6475551234"])
    source_code: str | None = None
    marketing_opt_in: bool = False

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        """Accept +1XXXXXXXXXX or bare 10-digit, normalize to E.164."""
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) == 10:
            return f"+1{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        if v.startswith("+1") and len(digits) == 11:
            return v
        raise ValueError("Phone must be a 10-digit North American number")


class VerifyOTPRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) == 10:
            return f"+1{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        if v.startswith("+1") and len(digits) == 11:
            return v
        raise ValueError("Phone must be a 10-digit North American number")


class TokenResponse(BaseModel):
    access_token: str | None = None  # null when using HttpOnly cookies
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    phone: str | None = None
    name: str | None = None
    email: str | None = None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminLoginRequest(BaseModel):
    email: str
    password: str


# --- Public ---

class LandingConfigResponse(BaseModel):
    restaurant_name: str
    primary_color: str
    secondary_color: str | None = None
    logo_url: str | None = None
    campaign: "CampaignConfig | None" = None
    allow_order_without_signup: bool = True
    external_ordering_url: str | None = None


class CampaignConfig(BaseModel):
    id: str
    source_code: str
    landing_headline: str | None = None
    landing_subtitle: str | None = None
    reward_template_id: str | None = None


# --- Reward ---

class RewardTemplateResponse(BaseModel):
    id: str
    name: str
    reward_type: str
    reward_value: int
    valid_days: int
    active: bool

    model_config = {"from_attributes": True}


class RewardResponse(BaseModel):
    id: str
    code: str
    status: str
    reward_type: str | None = None
    reward_value: int | None = None
    issued_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class ClaimRewardRequest(BaseModel):
    source_code: str | None = None
    campaign_id: str | None = None


class ClaimRewardResponse(BaseModel):
    reward: RewardResponse
    short_link: str | None = None


# --- Redirect ---

class OrderRedirectRequest(BaseModel):
    reward_id: str | None = None
    source_code: str | None = None
    campaign_id: str | None = None


class OrderRedirectResponse(BaseModel):
    destination_url: str


# --- Common ---

class APIResponse(BaseModel):
    data: dict | list | None = None
    error: dict | None = None


class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int
