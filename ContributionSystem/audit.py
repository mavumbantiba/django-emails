from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.dispatch import receiver

from auditlog.registry import auditlog

from .models import (
    AccountRecoveryRequest,
    Parent,
    Student,
    StudentClothingVerification,
    StudentCollection,
    StoreSupplyReceipt,
)


auditlog.register(
    get_user_model(),
    exclude_fields=("password", "last_login"),
    mask_fields=("email", "first_name", "last_name"),
    m2m_fields={"groups", "user_permissions"},
)
auditlog.register(
    Parent,
    mask_fields=("full_name", "phone_number", "email"),
)
auditlog.register(
    Student,
    mask_fields=(
        "admission_number",
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "region",
        "district",
        "ward",
        "village",
        "street",
    ),
)
auditlog.register(StudentCollection, mask_fields=("notes",))
auditlog.register(StoreSupplyReceipt, mask_fields=("notes",))
auditlog.register(StudentClothingVerification, mask_fields=("notes",))
auditlog.register(AccountRecoveryRequest, mask_fields=("email",))


@receiver(pre_save, sender=LogEntry, dispatch_uid="school_audit_safe_object_repr")
def use_safe_audit_object_repr(sender, instance, **kwargs):
    if instance.content_type_id:
        model = instance.content_type.model_class()
        if model is not None:
            instance.object_repr = f"{model._meta.verbose_name} #{instance.object_pk}"
