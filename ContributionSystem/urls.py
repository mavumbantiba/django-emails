from django.urls import include, path

from . import views


urlpatterns = [
    path("accounts/profile/", views.profile, name="profile"),
    path("home/", views.home, name="home"),
    path("parents/", views.parent_list, name="parent-list"),
    path("parents/add/", views.parent_create, name="parent-create"),
    path("students/", views.student_list, name="student-list"),
    path("students/register/", views.student_create, name="student-create"),
    path("collections/", views.collection_list, name="collection-list"),
    path("collections/add/", views.collection_create, name="collection-create"),
    path("accounts/", include("allauth.urls")),
]
