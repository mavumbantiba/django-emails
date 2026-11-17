from django.urls import path

from . import views


app_name = "library"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("books/add/", views.book_create, name="book-create"),
    path("books/<int:book_id>/edit/", views.book_edit, name="book-edit"),
    path("books/<int:book_id>/delete/", views.book_delete, name="book-delete"),
    path("loans/", views.loan_list, name="loan-list"),
    path("loans/issue/", views.loan_create, name="loan-create"),
    path("loans/<int:loan_id>/return/", views.loan_return, name="loan-return"),
]
