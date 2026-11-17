from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ContributionSystem.models import Student


class Book(models.Model):
    class Category(models.TextChoices):
        FICTION = "fiction", _("Fiction")
        REFERENCE = "reference", _("Reference")
        SCIENCE = "science", _("Science")
        MATHEMATICS = "mathematics", _("Mathematics")
        HISTORY = "history", _("History")
        LANGUAGE = "language", _("Language")
        OTHER = "other", _("Other")

    title = models.CharField(max_length=200)
    author = models.CharField(max_length=160)
    isbn = models.CharField(max_length=20, unique=True, null=True, blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    publisher = models.CharField(max_length=160, blank=True)
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True)
    shelf_location = models.CharField(max_length=60, blank=True)
    total_copies = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "author"]

    def __str__(self):
        return f"{self.title} — {self.author}"

    @property
    def available_copies(self):
        active_loan_count = getattr(self, "active_loan_count", None)
        if active_loan_count is None:
            active_loan_count = self.loans.filter(returned_at__isnull=True).count()
        return max(self.total_copies - active_loan_count, 0)


class BookLoan(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name="loans",
    )
    book_number = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text=_("Physical copy identifier, for example 01/100."),
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="library_loans",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="library_loans_issued",
    )
    issued_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateField()
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at", "-pk"]
        indexes = [
            models.Index(fields=["returned_at", "due_date"]),
            models.Index(fields=["student", "returned_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "student"],
                condition=Q(returned_at__isnull=True),
                name="unique_active_student_book_loan",
            ),
            models.UniqueConstraint(
                fields=["book", "book_number"],
                condition=Q(returned_at__isnull=True),
                name="unique_active_book_number",
            ),
        ]

    def __str__(self):
        return f"{self.book} — {self.student}"

    @property
    def is_overdue(self):
        return (
            self.returned_at is None
            and self.due_date < timezone.localdate()
        )
