from django.contrib import messages
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from .access import library_staff_required
from .forms import BookForm, BookLoanForm
from .models import Book, BookLoan


def _books_with_availability():
    return Book.objects.annotate(
        active_loan_count=Count(
            "loans",
            filter=Q(loans__returned_at__isnull=True),
        )
    )


@library_staff_required
def dashboard(request):
    books = _books_with_availability()
    search = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    availability = request.GET.get("availability", "").strip()

    if search:
        books = books.filter(
            Q(title__icontains=search)
            | Q(author__icontains=search)
            | Q(isbn__icontains=search)
            | Q(shelf_location__icontains=search)
        )
    if category in Book.Category.values:
        books = books.filter(category=category)
    if availability == "available":
        books = books.filter(total_copies__gt=F("active_loan_count"))
    elif availability == "unavailable":
        books = books.filter(total_copies__lte=F("active_loan_count"))

    today = timezone.localdate()
    context = {
        "books": books,
        "search": search,
        "selected_category": category,
        "selected_availability": availability,
        "categories": Book.Category.choices,
        "total_titles": Book.objects.count(),
        "total_copies": Book.objects.aggregate(total=Sum("total_copies"))[
            "total"
        ]
        or 0,
        "active_loans": BookLoan.objects.filter(returned_at__isnull=True).count(),
        "overdue_loans": BookLoan.objects.filter(
            returned_at__isnull=True,
            due_date__lt=today,
        ).count(),
        "recent_loans": BookLoan.objects.select_related("book", "student")[:6],
    }
    return render(request, "librarymanagement/dashboard.html", context)


@library_staff_required
@require_http_methods(["GET", "POST"])
def book_create(request):
    form = BookForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        book = form.save()
        messages.success(
            request,
            _("“%(title)s” was added to the catalog.") % {"title": book.title},
        )
        return redirect("library:dashboard")
    return render(
        request,
        "librarymanagement/book_form.html",
        {"form": form, "page_title": _("Add a book")},
    )


@library_staff_required
@require_http_methods(["GET", "POST"])
def book_edit(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    form = BookForm(request.POST or None, instance=book)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Book details were updated."))
        return redirect("library:dashboard")
    return render(
        request,
        "librarymanagement/book_form.html",
        {"form": form, "book": book, "page_title": _("Edit book")},
    )


@library_staff_required
@require_http_methods(["GET", "POST"])
def book_delete(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    if request.method == "POST":
        if book.loans.exists():
            messages.error(
                request,
                _("This book has loan history and cannot be deleted."),
            )
            return redirect("library:dashboard")
        title = book.title
        book.delete()
        messages.success(
            request,
            _("“%(title)s” was removed from the catalog.") % {"title": title},
        )
        return redirect("library:dashboard")
    return render(
        request,
        "librarymanagement/book_confirm_delete.html",
        {"book": book},
    )


@library_staff_required
def loan_list(request):
    today = timezone.localdate()
    loans = BookLoan.objects.select_related("book", "student", "issued_by")
    status = request.GET.get("status", "active")
    search = request.GET.get("q", "").strip()

    if status == "active":
        loans = loans.filter(returned_at__isnull=True)
    elif status == "overdue":
        loans = loans.filter(
            returned_at__isnull=True,
            due_date__lt=today,
        )
    elif status == "returned":
        loans = loans.filter(returned_at__isnull=False)
    else:
        status = "all"
    if search:
        loans = loans.filter(
            Q(book__title__icontains=search)
            | Q(student__first_name__icontains=search)
            | Q(student__last_name__icontains=search)
            | Q(student__admission_number__icontains=search)
        )
    return render(
        request,
        "librarymanagement/loan_list.html",
        {
            "loans": loans,
            "selected_status": status,
            "search": search,
            "today": today,
        },
    )


@library_staff_required
@require_http_methods(["GET", "POST"])
def loan_create(request):
    form = BookLoanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            book = Book.objects.select_for_update().get(
                pk=form.cleaned_data["book"].pk
            )
            active_loans = book.loans.filter(returned_at__isnull=True)
            if active_loans.count() >= book.total_copies:
                form.add_error("book", _("There are no copies available to loan."))
            elif active_loans.filter(
                student=form.cleaned_data["student"]
            ).exists():
                form.add_error(
                    "student",
                    _("This student already has an active loan for this book."),
                )
            else:
                loan = form.save(commit=False)
                loan.book = book
                loan.issued_by = request.user
                loan.save()
                messages.success(
                    request,
                    _("“%(title)s” was issued successfully.") % {
                        "title": book.title,
                    },
                )
                return redirect("library:loan-list")
    return render(
        request,
        "librarymanagement/loan_form.html",
        {"form": form, "page_title": _("Issue a book")},
    )


@library_staff_required
@require_POST
def loan_return(request, loan_id):
    with transaction.atomic():
        loan = get_object_or_404(
            BookLoan.objects.select_for_update(),
            pk=loan_id,
        )
        if loan.returned_at is not None:
            messages.info(request, _("This book has already been returned."))
        else:
            loan.returned_at = timezone.now()
            loan.save(update_fields=["returned_at"])
            messages.success(
                request,
                _("“%(title)s” was marked as returned.") % {
                    "title": loan.book.title,
                },
            )
    return redirect("library:loan-list")
