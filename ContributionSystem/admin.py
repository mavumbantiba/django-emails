# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

# from .models import User


# class UserCreationForm(BaseUserCreationForm):
#     class Meta(BaseUserCreationForm.Meta):
#         model = User
#         fields = ("email",)


# class CustomUserChangeForm(UserChangeForm):
#     class Meta(UserChangeForm.Meta):
#         model = User
#         fields = "__all__"


# @admin.register(User)
# class UserAdmin(BaseUserAdmin):
#     form = CustomUserChangeForm
#     add_form = UserCreationForm
#     ordering = ("email",)
#     list_display = ("email", "first_name", "last_name", "role", "is_staff")
#     fieldsets = (
#         (None, {"fields": ("email", "password")}),
#         ("Personal info", {"fields": ("first_name", "last_name", "phone", "photo", "role")}),
#         (
#             "Permissions",
#             {
#                 "fields": (
#                     "is_active",
#                     "is_staff",
#                     "is_superuser",
#                     "groups",
#                     "user_permissions",
#                 )
#             },
#         ),
#         ("Important dates", {"fields": ("last_login", "date_joined")}),
#     )
#     add_fieldsets = (
#         (
#             None,
#             {
#                 "classes": ("wide",),
#                 "fields": ("email", "password1", "password2", "role"),
#             },
#         ),
#     )
