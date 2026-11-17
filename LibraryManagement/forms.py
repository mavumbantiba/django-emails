from datetime import timedelta

from django import forms
from django.db.models import Count, F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ContributionSystem.models import Student

from .models import Book, BookLoan


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = (
            "title",
            "author",
            "isbn",
            "category",
            "publisher",
            "publication_year",
            "shelf_location",
            "total_copies",
            "description",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_isbn(self):
        isbn = self.cleaned_data["isbn"]
        return isbn or None


class BookLoanForm(forms.ModelForm):
    class Meta:
        model = BookLoan
        fields = ("book", "student", "due_date")
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "book": _("Book"),
            "student": _("Student"),
            "due_date": _("Return by"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["book"].queryset = (
            Book.objects.annotate(
                active_loan_count=Count(
                    "loans",
                    filter=Q(loans__returned_at__isnull=True),
                )
            )
            .filter(total_copies__gt=F("active_loan_count"))
            .order_by("title")
        )
        self.fields["student"].queryset = Student.objects.order_by(
            "last_name", "first_name"
        )
        self.fields["student"].label_from_instance = (
            lambda student: (
                f"{student.first_name} {student.last_name} "
                f"({student.admission_number})"
            )
        )
        self.fields["due_date"].initial = timezone.localdate() + timedelta(days=14)
