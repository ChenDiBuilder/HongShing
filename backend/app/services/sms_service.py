"""Send SMS messages via AWS SNS."""

import boto3

from app.config import get_settings

settings = get_settings()


def send_sms(phone: str, message: str) -> None:
    """Send an SMS message via AWS SNS.

    The phone number should be in E.164 format (e.g. +16475551234).
    Falls back to printing to console if boto3 fails (sandbox, missing creds).
    """
    try:
        client = boto3.client("sns", region_name=settings.aws_region)
        client.publish(
            PhoneNumber=phone,
            Message=message,
            MessageAttributes={
                "AWS.SNS.SMS.SenderID": {
                    "DataType": "String",
                    "StringValue": settings.sns_sender_id,
                },
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",
                },
            },
        )
    except Exception as e:
        print(f"[SMS] Failed to send to {phone}: {e}")
        print(f"[SMS] Message: {message}")
