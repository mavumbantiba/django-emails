from django.contrib import admin

from .models import Parent, Student, StudentCollection


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone_number", "email")
    search_fields = ("full_name", "phone_number", "email")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "admission_number",
        "first_name",
        "last_name",
        "class_level",
        "parent",
        "region",
        "district",
        "registered_at",
    )
    list_filter = ("class_level", "gender")
    search_fields = (
        "admission_number",
        "first_name",
        "middle_name",
        "last_name",
        "parent__full_name",
        "parent__phone_number",
        "region",
        "district",
        "ward",
        "village",
        "street",
    )
    autocomplete_fields = ("parent",)


@admin.register(StudentCollection)
class StudentCollectionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "category",
        "amount_collected",
        "quantity_issued",
        "recorded_at",
        "recorded_by",
    )
    list_filter = ("category", "recorded_at")
    search_fields = (
        "student__admission_number",
        "student__first_name",
        "student__last_name",
    )
