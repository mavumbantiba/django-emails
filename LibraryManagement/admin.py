from django.contrib import admin

from .models import Book, BookLoan


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "category",
        "total_copies",
        "shelf_location",
    )
    list_filter = ("category",)
    search_fields = ("title", "author", "isbn")


@admin.register(BookLoan)
class BookLoanAdmin(admin.ModelAdmin):
    list_display = ("book", "student", "issued_at", "due_date", "returned_at")
    list_filter = ("due_date", "returned_at")
    search_fields = (
        "book__title",
        "student__first_name",
        "student__last_name",
        "student__admission_number",
    )
    autocomplete_fields = ("book", "student", "issued_by")
    readonly_fields = ("issued_at", "returned_at")
