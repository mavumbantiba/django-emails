import json
import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext as _


logger = logging.getLogger(__name__)


def record_snapshot(record):
    snapshot = {}
    for field in record._meta.concrete_fields:
        value = getattr(record, field.name)
        if field.is_relation:
            value = str(value) if value is not None else None
        snapshot[field.name] = value
    return snapshot


def send_record_notification(
    request,
    *,
    recipient,
    action,
    record_type,
    record_identifier,
    data,
):
    email_address = (getattr(recipient, "email", "") or "").strip()
    if not email_address:
        messages.warning(
            request,
            _(
                "The record change was completed, but no email was sent because the "
                "original creator has no available email address."
            ),
        )
        return False

    occurred_at = timezone.localtime()
    payload = {
        "action": action,
        "record_type": record_type,
        "record_identifier": record_identifier,
        "performed_by": request.user.get_username(),
        "occurred_at": occurred_at.isoformat(),
        "data": data,
    }
    attachment = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    subject = f"Kafunjo school records: {action} {record_type}"
    body = (
        "A school record was changed.\n\n"
        f"Action: {action}\n"
        f"Record type: {record_type}\n"
        f"Record identifier: {record_identifier}\n"
        f"Performed by: {request.user.get_username()}\n"
        f"Time: {occurred_at:%Y-%m-%d %H:%M:%S %Z}\n\n"
        "Record data:\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2, default=str)}"
    )
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email_address],
    )
    filename = (
        f"school-record-{slugify(record_type)}-{slugify(action)}-"
        f"{occurred_at:%Y%m%dT%H%M%S}.json"
    )
    email.attach(filename, attachment, "application/json")
    try:
        sent_count = email.send(fail_silently=False)
    except (OSError, SMTPException, ValueError) as error:
        logger.warning(
            "Could not send %s notification for %s (%s)",
            action,
            record_type,
            type(error).__name__,
        )
        messages.warning(
            request,
            _(
                "The record change was completed, but its email notification could not "
                "be sent. Check the email server settings and try again."
            ),
        )
        return False

    if sent_count != 1:
        messages.warning(
            request,
            _(
                "The record change was completed, but its email notification was not "
                "accepted by the email server."
            ),
        )
        return False
    return True
