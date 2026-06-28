"""Send SMS messages via AWS SNS."""

import boto3

from app.config import get_settings

settings = get_settings()

SNS_RETRY_ATTEMPTS = 3

DEFAULT_OTP_TEMPLATE = "Your {restaurant} verification code is {code}. It expires in 5 minutes."


def render_otp_message(template: str | None, restaurant: str, code: str) -> str:
    """Render the OTP SMS body from a profile-configured template (PRD-12 S3 /
    SCRUM-60), falling back to the default. A malformed template (unknown/extra
    placeholder) can never raise — it falls back to the default — so an OTP send
    is never blocked by bad config."""
    tmpl = template or DEFAULT_OTP_TEMPLATE
    try:
        return tmpl.format(restaurant=restaurant, code=code)
    except (KeyError, IndexError, ValueError):
        return DEFAULT_OTP_TEMPLATE.format(restaurant=restaurant, code=code)


def _check_sms_capability() -> None:
    """Log SNS SMS account attributes to help diagnose delivery issues."""
    try:
        client = boto3.client("sns", region_name=settings.sns_region or settings.aws_region)
        attrs = client.get_sms_attributes()
        spend_limit = attrs.get("attributes", {}).get("MonthlySpendLimit", "unknown")
        account_status = attrs.get("attributes", {}).get("DefaultSMSType", "unknown")
        print(f"[SMS] Account status: spend_limit={spend_limit} default_type={account_status}")
    except Exception:
        print("[SMS] WARNING: Unable to check SNS SMS account attributes (missing IAM permission)")


def send_sms(phone: str, message: str) -> None:
    """Send an SMS message via AWS SNS.

    Uses origination number for Canadian delivery.
    Falls back to console log if boto3 fails (sandbox, missing creds).
    """
    orig_number = settings.sns_origination_number or "(not set)"
    sender_id = settings.sns_sender_id or "(not set)"

    print(f"[SMS] Sending: to={phone} origination={orig_number} sender_id={sender_id}")

    try:
        client = boto3.client("sns", region_name=settings.sns_region or settings.aws_region)
        attrs = {
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                "StringValue": "Transactional",
            },
        }
        if settings.sns_origination_number:
            attrs["AWS.MM.SMS.OriginationNumber"] = {
                "DataType": "String",
                "StringValue": settings.sns_origination_number,
            }
        elif settings.sns_sender_id:
            attrs["AWS.SNS.SMS.SenderID"] = {
                "DataType": "String",
                "StringValue": settings.sns_sender_id,
            }

        for attempt in range(1, SNS_RETRY_ATTEMPTS + 1):
            try:
                response = client.publish(
                    PhoneNumber=phone,
                    Message=message,
                    MessageAttributes=attrs,
                )
                message_id = response.get("MessageId", "unknown")
                print(f"[SMS] SUCCESS: to={phone} message_id={message_id} attempt={attempt}")
                return
            except client.exceptions.EndpointDisabledException:
                print(f"[SMS] ERROR: SNS SMS endpoint disabled — account may be in sandbox. to={phone}")
                return
            except Exception as retry_err:
                if attempt == SNS_RETRY_ATTEMPTS:
                    raise retry_err
                print(f"[SMS] RETRY: attempt={attempt} to={phone} error={retry_err}")

    except Exception as e:
        print(f"[SMS] FAILED: to={phone} error={e} message={message}")
