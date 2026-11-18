from django.core.management.base import BaseCommand
from django.utils import timezone

from ContributionSystem.sms import send_sms
from LibraryManagement.models import BookLoan


class Command(BaseCommand):
    help = "Send Africa's Talking SMS reminders for overdue library loans"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show overdue loans without sending SMS messages",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        overdue_loans = BookLoan.objects.filter(
            returned_at__isnull=True,
            due_date__lt=today,
        ).select_related("book", "student", "student__parent")

        sent = 0
        for loan in overdue_loans:
            message = (
                f"Kafunjo Secondary School library: "
                f"{loan.student.first_name} {loan.student.last_name} has an overdue "
                f"copy of {loan.book.title}, due {loan.due_date:%Y-%m-%d}. "
                f"Please return it promptly."
            )
            if options["dry_run"]:
                self.stdout.write(
                    f"{loan.pk}: {loan.student.parent.phone_number}: {message}"
                )
                continue
            if send_sms(loan.student.parent.phone_number, message):
                sent += 1

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{overdue_loans.count()} overdue loan(s) found; dry run only"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sent {sent} of {overdue_loans.count()} overdue SMS reminder(s)"
                )
            )
