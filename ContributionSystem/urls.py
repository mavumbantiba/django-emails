from django.urls import include, path

from . import views


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/profile/", views.profile, name="profile"),
    path("accounts/profile/edit/", views.profile_edit, name="profile-edit"),
    path("", views.home, name="home"),
    path("home/", views.home, name="home-legacy"),
    path("parents/", views.parent_list, name="parent-list"),
    path("parents/add/", views.parent_create, name="parent-create"),
    path(
        "parents/<int:parent_id>/delete/",
        views.parent_delete,
        name="parent-delete",
    ),
    path("students/", views.student_list, name="student-list"),
    path("students/register/", views.student_create, name="student-create"),
    path(
        "students/<int:student_id>/edit/",
        views.student_edit,
        name="student-edit",
    ),
    path(
        "students/<int:student_id>/delete/",
        views.student_delete,
        name="student-delete",
    ),
    path(
        "students/<int:student_id>/clothing/",
        views.student_clothing,
        name="student-clothing",
    ),
    path(
        "students/<int:student_id>/clothing/<int:verification_id>/edit/",
        views.student_clothing,
        name="student-clothing-edit",
    ),
    path(
        "students/<int:student_id>/clothing/<int:verification_id>/delete/",
        views.clothing_verification_delete,
        name="clothing-verification-delete",
    ),
    path(
        "students/<int:student_id>/supplies/",
        views.student_supply_history,
        name="student-supply-history",
    ),
    path("collections/", views.collection_list, name="collection-list"),
    path("collections/add/", views.collection_create, name="collection-create"),
    path(
        "collections/<int:collection_id>/edit/",
        views.collection_create,
        name="collection-edit",
    ),
    path(
        "collections/<int:collection_id>/delete/",
        views.collection_delete,
        name="collection-delete",
    ),
    path("supplies/", views.supply_list, name="supply-list"),
    path("supplies/add/", views.supply_create, name="supply-create"),
    path(
        "supplies/<int:receipt_id>/delete/",
        views.supply_delete,
        name="supply-delete",
    ),
    path(
        "supplies/<int:receipt_id>/edit/",
        views.supply_create,
        name="supply-edit",
    ),
    path("accounts/logout/", views.mfa_logout, name="account_logout"),
    path("accounts/", include("allauth.urls")),
]
