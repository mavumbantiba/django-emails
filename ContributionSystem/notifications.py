import io
import json
import logging
from smtplib import SMTPException
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext as _
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


logger = logging.getLogger(__name__)


def _build_record_pdf(payload):
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SchoolReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#183147"),
        spaceAfter=4 * mm,
    )
    section_style = ParagraphStyle(
        "SchoolReportSection",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#167a51"),
        spaceBefore=5 * mm,
        spaceAfter=2 * mm,
    )
    detail_style = ParagraphStyle(
        "SchoolReportDetail",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        wordWrap="CJK",
    )
    label_style = ParagraphStyle(
        "SchoolReportLabel",
        parent=detail_style,
        textColor=colors.HexColor("#334155"),
        fontName="Helvetica-Bold",
    )
    data_style = ParagraphStyle(
        "SchoolReportData",
        parent=detail_style,
        fontName="Courier",
        fontSize=8,
        leading=10,
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        pageCompression=0,
        title="Kafunjo Secondary School record change",
        author="Kafunjo Secondary School",
    )
    details = [
        ("Action", payload["action"]),
        ("Record type", payload["record_type"]),
        ("Record identifier", payload["record_identifier"]),
        ("Performed by", payload["performed_by"]),
        ("Date and time", payload["occurred_at"]),
    ]
    detail_rows = [
        [
            Paragraph(escape(str(label)), label_style),
            Paragraph(escape(str(value)), detail_style),
        ]
        for label, value in details
    ]
    detail_table = Table(detail_rows, colWidths=[42 * mm, 128 * mm], hAlign="LEFT")
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e2ec")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story = [
        Paragraph("Kafunjo Secondary School", title_style),
        Paragraph("School record change", styles["Heading1"]),
        Spacer(1, 3 * mm),
        detail_table,
        Paragraph("Record details", section_style),
    ]
    data_json = json.dumps(payload["data"], ensure_ascii=True, indent=2, default=str)
    for line in data_json.splitlines():
        story.append(Paragraph(escape(line) or "&nbsp;", data_style))

    doc.build(story)
    return buffer.getvalue()


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
    attachment = _build_record_pdf(payload)
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
        f"{occurred_at:%Y%m%dT%H%M%S}.pdf"
    )
    email.attach(filename, attachment, "application/pdf")
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
