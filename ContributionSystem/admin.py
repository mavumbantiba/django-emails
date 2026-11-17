
from django.contrib import admin
from django.utils.decorators import method_decorator

from allauth.account.decorators import reauthentication_required

from .models import (
    AccountRecoveryRequest,
    Parent,
    Student,
    StudentClothingVerification,
    StudentCollection,
    StoreSupplyReceipt,
)
from .notifications import record_snapshot, send_record_notification
from .security import force_logout_home, require_mfa_reauthentication


admin.site.site_header = "Kafunjo Secondary School Administration"
admin.site.site_title = "Kafunjo Secondary School Admin Portal"
admin.site.index_title = "School Management Dashboard"
admin.site.logout = require_mfa_reauthentication(
    force_logout_home(admin.site.logout)
)


@admin.register(AccountRecoveryRequest)
class AccountRecoveryRequestAdmin(admin.ModelAdmin):
    list_display = ("email", "status", "requested_at")
    list_filter = ("status", "requested_at")
    search_fields = ("email",)
    readonly_fields = ("requested_at",)
    help_texts = {
        "email": (
            "Verify the requester's identity through the school's established "
            "process before changing credentials or MFA settings."
        ),
    }


class RecordAuditAdminMixin:
    creator_field = ""
    record_type = ""

    @method_decorator(reauthentication_required)
    def delete_view(self, request, object_id, extra_context=None):
        return super().delete_view(request, object_id, extra_context)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def save_model(self, request, obj, form, change):
        before = None
        if change:
            original = type(obj)._default_manager.get(pk=obj.pk)
            before = record_snapshot(original)
            recipient = getattr(original, self.creator_field)
        else:
            recipient = request.user
            setattr(obj, self.creator_field, request.user)

        super().save_model(request, obj, form, change)
        send_record_notification(
            request,
            recipient=recipient,
            action="updated" if change else "recorded",
            record_type=self.record_type,
            record_identifier=getattr(obj, "admission_number", obj.pk),
            data={
                "before": before,
                "after": record_snapshot(obj),
            }
            if change
            else record_snapshot(obj),
        )

    def delete_model(self, request, obj):
        recipient = getattr(obj, self.creator_field)
        snapshot = record_snapshot(obj)
        if isinstance(obj, Student):
            snapshot = {
                "student": snapshot,
                "collections": [
                    record_snapshot(collection)
                    for collection in obj.collections.select_related("recorded_by")
                ],
                "clothing_checks": [
                    record_snapshot(check)
                    for check in obj.clothing_verifications.select_related(
                        "recorded_by",
                        "verified_by",
                    )
                ],
            }
        identifier = getattr(obj, "admission_number", obj.pk)
        super().delete_model(request, obj)
        send_record_notification(
            request,
            recipient=recipient,
            action="deleted",
            record_type=self.record_type,
            record_identifier=identifier,
            data=snapshot,
        )


@admin.register(Parent)
class ParentAdmin(RecordAuditAdminMixin, admin.ModelAdmin):
    creator_field = "created_by"
    record_type = "Parent"
    list_display = ("full_name", "phone_number", "email", "created_by")
    search_fields = ("full_name", "phone_number", "email")
    readonly_fields = ("created_by",)


@admin.register(Student)
class StudentAdmin(RecordAuditAdminMixin, admin.ModelAdmin):
    creator_field = "registered_by"
    record_type = "Student"
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
    readonly_fields = ("registered_by",)


@admin.register(StudentCollection)
class StudentCollectionAdmin(RecordAuditAdminMixin, admin.ModelAdmin):
    creator_field = "recorded_by"
    record_type = "Student collection"
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
        "student__middle_name",
        "student__last_name",
    )
    readonly_fields = ("recorded_by",)


@admin.register(StoreSupplyReceipt)
class StoreSupplyReceiptAdmin(RecordAuditAdminMixin, admin.ModelAdmin):
    creator_field = "recorded_by"
    record_type = "Store supply receipt"
    list_display = (
        "student",
        "item",
        "quantity_collected",
        "source",
        "collected_at",
        "recorded_by",
    )
    list_filter = ("item", "collected_at")
    search_fields = (
        "student__admission_number",
        "student__first_name",
        "student__last_name",
        "item",
        "source",
        "notes",
    )
    readonly_fields = ("recorded_by",)


@admin.register(StudentClothingVerification)
class StudentClothingVerificationAdmin(RecordAuditAdminMixin, admin.ModelAdmin):
    creator_field = "recorded_by"
    record_type = "Student clothing verification"
    list_display = (
        "student",
        "category",
        "clothing_item",
        "is_verified",
        "verified_at",
        "verified_by",
    )
    list_filter = ("category", "is_verified")
    search_fields = (
        "student__admission_number",
        "student__first_name",
        "student__last_name",
        "clothing_item",
    )
    readonly_fields = ("recorded_by",)
