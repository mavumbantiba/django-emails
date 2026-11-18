import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)


def normalize_phone_number(phone_number):
    value = "".join(str(phone_number or "").strip().split())
    if value.startswith("00"):
        value = "+" + value[2:]
    if value.startswith("+"):
        return value
    if value.startswith("255") and len(value) >= 12:
        return "+" + value
    if value.startswith("0") and len(value) >= 9:
        return "+255" + value[1:]
    return value


def send_sms(phone_number, message):
    recipient = normalize_phone_number(phone_number)
    if not recipient:
        logger.warning("SMS was not sent because the recipient phone number is empty")
        return False

    if not getattr(settings, "SMS_ENABLED", False):
        logger.info("SMS is disabled; notification was not sent to %s", recipient)
        return False

    username = getattr(settings, "AFRICASTALKING_USERNAME", "").strip()
    api_key = getattr(settings, "AFRICASTALKING_API_KEY", "").strip()
    if not username or not api_key:
        logger.warning("SMS was not sent because Africa's Talking credentials are missing")
        return False

    data = {
        "username": username,
        "to": recipient,
        "message": message,
    }
    sender_id = getattr(settings, "AFRICASTALKING_SENDER_ID", "").strip()
    if sender_id:
        data["from"] = sender_id

    request = Request(
        "https://api.africastalking.com/version1/messaging",
        data=urlencode(data).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "ApiKey": api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        logger.warning("Could not send SMS (%s)", type(error).__name__)
        return False

    try:
        recipients = payload["SMSMessageData"]["Recipients"]
    except (KeyError, TypeError):
        logger.warning("Africa's Talking returned an invalid SMS response")
        return False

    successful = [
        recipient_data
        for recipient_data in recipients
        if str(recipient_data.get("status")).upper() in {"SUCCESS", "SENT"}
    ]
    if not successful:
        logger.warning("Africa's Talking did not accept the SMS recipient")
        return False
    return True
