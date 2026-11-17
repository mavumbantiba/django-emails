from allauth.account.decorators import reauthentication_required
from allauth.account.views import LogoutView as AllauthLogoutView
from allauth.mfa.models import Authenticator
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Q, Sum
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.http import require_http_methods

from .access import (
    ACCOUNTANT_ROLE,
    ACADEMIC_ROLE,
    SECOND_HEAD_ROLE,
    allowed_collection_categories,
    role_required,
)
from .forms import (
    AccountDeletionForm,
    AccountRecoveryRequestForm,
    ParentForm,
    StudentClothingVerificationForm,
    StudentCollectionForm,
    StoreSupplyItemForm,
    StudentForm,
    StoreSupplyReceiptForm,
    UserProfileForm,
)
from .models import (
    Parent,
    Student,
    StudentClothingVerification,
    StudentCollection,
    StoreSupplyReceipt,
)
from .notifications import (
    record_snapshot,
    send_account_recovery_notification,
    send_record_notification,
)
from .security import require_mfa_reauthentication


class SchoolLogoutView(AllauthLogoutView):
    def get_redirect_url(self):
        return reverse("home")


mfa_logout = require_mfa_reauthentication(SchoolLogoutView.as_view())


@login_required
def profile(request):
    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": request.user,
            "display_name": (
                request.user.get_full_name() or request.user.get_username()
            ),
            "has_totp": Authenticator.objects.filter(
                user=request.user,
                type=Authenticator.Type.TOTP,
            ).exists(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    form = UserProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Your profile has been updated."))
        return redirect("profile")
    return render(request, "accounts/profile_edit.html", {"form": form})


@require_http_methods(["GET", "POST"])
def account_recovery(request):
    form = AccountRecoveryRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        recovery_request = form.save()
        send_account_recovery_notification(request, recovery_request)
        return render(request, "accounts/recovery_submitted.html")
    return render(request, "accounts/recovery.html", {"form": form})


@login_required
@require_mfa_reauthentication
@require_http_methods(["GET", "POST"])
def account_delete(request):
    form = AccountDeletionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        user.delete()
        return redirect("home")
    return render(request, "accounts/confirm_delete.html", {"form": form})


def home(request):
    return render(request, 'home.html')


def _confirm_record_deletion(
    request,
    record,
    record_title,
    return_url,
    cascade_warning="",
    blocked_message="",
    blocked_link="",
    notification=None,
):
    return_url = resolve_url(return_url)
    context = {
        "record_title": record_title,
        "return_url": return_url,
        "cascade_warning": cascade_warning,
        "blocked_message": blocked_message,
        "blocked_link": blocked_link,
    }
    if request.method == "POST":
        if blocked_message:
            return render(
                request,
                "contributions/confirm_delete.html",
                context,
                status=409,
            )
        try:
            with transaction.atomic():
                record.delete()
        except ProtectedError:
            context["blocked_message"] = (
                _(
                    "This record is now linked to other records and cannot be deleted. "
                    "Review or remove the linked records first."
                )
            )
            context["blocked_link"] = blocked_link
            return render(
                request,
                "contributions/confirm_delete.html",
                context,
                status=409,
            )
        if notification:
            send_record_notification(request, **notification)
        return redirect(return_url)
    return render(request, "contributions/confirm_delete.html", context)


@login_required
@role_required(SECOND_HEAD_ROLE)
@vary_on_headers("HX-Request")
def parent_list(request):
    query = request.GET.get("q", "").strip()
    parents = Parent.objects.all()
    if query:
        parents = parents.filter(
            Q(full_name__icontains=query)
            | Q(phone_number__icontains=query)
            | Q(email__icontains=query)
        )
    template = (
        "contributions/partials/parent_results.html"
        if request.headers.get("HX-Request") == "true"
        else "contributions/parent_list.html"
    )
    return render(request, template, {"parents": parents, "query": query})


@login_required
@role_required(SECOND_HEAD_ROLE)
@reauthentication_required
@require_http_methods(["GET", "POST"])
def parent_delete(request, parent_id):
    parent = get_object_or_404(Parent, pk=parent_id)
    student_count = parent.students.count()
    blocked_message = (
        _("This parent is linked to %(count)s student record(s). "
          "Remove or reassign those students before deleting this parent.")
        % {"count": student_count}
        if student_count
        else ""
    )
    return _confirm_record_deletion(
        request,
        parent,
        str(parent),
        "parent-list",
        blocked_message=blocked_message,
        blocked_link=reverse("student-list"),
        notification={
            "recipient": parent.created_by,
            "action": "deleted",
            "record_type": "Parent",
            "record_identifier": parent.pk,
            "data": record_snapshot(parent),
        },
    )


@login_required
@role_required(SECOND_HEAD_ROLE)
def parent_create(request):
    form = ParentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        parent = form.save(commit=False)
        parent.created_by = request.user
        parent.save()
        send_record_notification(
            request,
            recipient=parent.created_by,
            action="recorded",
            record_type="Parent",
            record_identifier=parent.pk,
            data=record_snapshot(parent),
        )
        return redirect("parent-list")
    return render(
        request,
        "contributions/form.html",
        {
            "form": form,
            "eyebrow": _("School records · Parent information"),
            "title": _("Add a parent"),
            "description": _("Save a parent or guardian’s contact details for student registration."),
            "section_title": _("Parent contact details"),
            "section_description": _("Enter a name and a phone number. Email is optional."),
            "button_text": _("Save parent"),
            "cancel_url": "parent-list",
            "can_save": True,
        },
    )


@login_required
@role_required(SECOND_HEAD_ROLE)
@vary_on_headers("HX-Request")
def student_list(request):
    query = request.GET.get("q", "").strip()
    students = Student.objects.select_related("parent")
    if query:
        students = students.filter(
            Q(admission_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(middle_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(class_level__icontains=query)
            | Q(parent__full_name__icontains=query)
            | Q(parent__phone_number__icontains=query)
            | Q(region__icontains=query)
            | Q(district__icontains=query)
            | Q(ward__icontains=query)
            | Q(village__icontains=query)
            | Q(street__icontains=query)
        )
    template = (
        "contributions/partials/student_results.html"
        if request.headers.get("HX-Request") == "true"
        else "contributions/student_list.html"
    )
    return render(request, template, {"students": students, "query": query})


@login_required
@role_required(SECOND_HEAD_ROLE)
@reauthentication_required
@require_http_methods(["GET", "POST"])
def student_delete(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    receipt_count = student.store_supply_receipts.count()
    collection_count = student.collections.count()
    clothing_count = student.clothing_verifications.count()
    cascade_warning = ""
    if collection_count or clothing_count:
        cascade_warning = (
            _("Deleting this student will also permanently delete %(collections)s "
              "collection record(s) and %(clothing)s clothing check(s).")
            % {"collections": collection_count, "clothing": clothing_count}
        )
    blocked_message = (
        _("This student has %(count)s linked supply record(s). Delete those "
          "supply records first to preserve the relationship history.")
        % {"count": receipt_count}
        if receipt_count
        else ""
    )
    deletion_data = record_snapshot(student)
    if request.method == "POST" and not blocked_message:
        deletion_data = {
            "student": deletion_data,
            "collections": [
                record_snapshot(collection)
                for collection in student.collections.select_related("recorded_by")
            ],
            "clothing_checks": [
                record_snapshot(check)
                for check in student.clothing_verifications.select_related(
                    "recorded_by",
                    "verified_by",
                )
            ],
        }
    return _confirm_record_deletion(
        request,
        student,
        str(student),
        "student-list",
        cascade_warning=cascade_warning,
        blocked_message=blocked_message,
        blocked_link=reverse(
            "student-supply-history",
            kwargs={"student_id": student.pk},
        ),
        notification={
            "recipient": student.registered_by,
            "action": "deleted",
            "record_type": "Student",
            "record_identifier": student.admission_number,
            "data": deletion_data,
        },
    )


@login_required
@role_required(SECOND_HEAD_ROLE)
def student_create(request):
    form = StudentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        student = form.save(commit=False)
        student.registered_by = request.user
        student.save()
        send_record_notification(
            request,
            recipient=student.registered_by,
            action="recorded",
            record_type="Student",
            record_identifier=student.admission_number,
            data=record_snapshot(student),
        )
        return redirect("student-clothing", student_id=student.pk)
    return render(
        request,
        "contributions/student_form.html",
        {
            "form": form,
            "has_parents": Parent.objects.exists(),
            "editing_student": False,
        },
    )


@login_required
@role_required(SECOND_HEAD_ROLE)
@require_http_methods(["GET", "POST"])
def student_edit(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    form = StudentForm(request.POST or None, instance=student)
    if request.method == "POST" and form.is_valid():
        before = record_snapshot(student)
        recipient = student.registered_by
        updated_student = form.save()
        send_record_notification(
            request,
            recipient=recipient,
            action="updated",
            record_type="Student",
            record_identifier=updated_student.admission_number,
            data={
                "before": before,
                "after": record_snapshot(updated_student),
            },
        )
        return redirect("student-list")

    return render(
        request,
        "contributions/student_form.html",
        {
            "form": form,
            "has_parents": Parent.objects.exists(),
            "editing_student": True,
        },
    )


@login_required
@role_required(ACADEMIC_ROLE, ACCOUNTANT_ROLE)
@vary_on_headers("HX-Request")
def collection_list(request):
    categories = allowed_collection_categories(request.user)
    query = request.GET.get("q", "").strip()
    collections = StudentCollection.objects.filter(
        category__in=categories,
    ).select_related("student", "recorded_by")
    if query:
        collections = collections.filter(
            Q(student__admission_number__icontains=query)
            | Q(student__first_name__icontains=query)
            | Q(student__last_name__icontains=query)
            | Q(category__icontains=query)
            | Q(notes__icontains=query)
        )
    template = (
        "contributions/partials/collection_results.html"
        if request.headers.get("HX-Request") == "true"
        else "contributions/collection_list.html"
    )
    return render(
        request,
        template,
        {
            "collections": collections,
            "query": query,
        },
    )


@login_required
@role_required(ACADEMIC_ROLE, ACCOUNTANT_ROLE)
def collection_create(request, collection_id=None):
    categories = allowed_collection_categories(request.user)
    collection = None
    if collection_id is not None:
        collection = get_object_or_404(
            StudentCollection.objects.filter(category__in=categories),
            pk=collection_id,
        )
    form = StudentCollectionForm(
        request.POST or None,
        instance=collection,
        allowed_categories=categories,
    )
    if request.method == "POST" and form.is_valid():
        if collection is None:
            collection = form.save(commit=False)
            collection.recorded_by = request.user
            collection.save()
            send_record_notification(
                request,
                recipient=collection.recorded_by,
                action="recorded",
                record_type="Student collection",
                record_identifier=collection.pk,
                data=record_snapshot(collection),
            )
        else:
            before = record_snapshot(collection)
            recipient = collection.recorded_by
            collection = form.save()
            send_record_notification(
                request,
                recipient=recipient,
                action="updated",
                record_type="Student collection",
                record_identifier=collection.pk,
                data={
                    "before": before,
                    "after": record_snapshot(collection),
                },
            )
        return redirect("collection-list")
    return render(
        request,
        "contributions/form.html",
        {
            "form": form,
            "eyebrow": _("School records · Student contributions"),
            "title": (
                _("Edit collection")
                if collection
                else _("Record a collection")
            ),
            "description": (
                _("Update this student collection.")
                if collection
                else _("Record a student payment, an item issued, or both.")
            ),
            "section_title": _("Collection details"),
            "section_description": _("Select a student and enter the amount collected or quantity issued."),
            "button_text": _("Save changes") if collection else _("Save collection"),
            "cancel_url": "collection-list",
            "can_save": Student.objects.exists(),
            "editing_collection": collection is not None,
            "prerequisite_title": _("Register a student first"),
            "prerequisite_description": _("A collection must be linked to a student record."),
            "prerequisite_action": _("Register student"),
            "prerequisite_url": "student-create",
        },
    )


@login_required
@role_required(ACADEMIC_ROLE, ACCOUNTANT_ROLE)
@reauthentication_required
@require_http_methods(["GET", "POST"])
def collection_delete(request, collection_id):
    collection = get_object_or_404(
        StudentCollection.objects.filter(
            category__in=allowed_collection_categories(request.user),
        ).select_related("student"),
        pk=collection_id,
    )
    return _confirm_record_deletion(
        request,
        collection,
        str(collection),
        "collection-list",
        notification={
            "recipient": collection.recorded_by,
            "action": "deleted",
            "record_type": "Student collection",
            "record_identifier": collection.pk,
            "data": record_snapshot(collection),
        },
    )


@login_required
@role_required()
@vary_on_headers("HX-Request")
def supply_list(request):
    query = request.GET.get("q", "").strip()
    supplies = StoreSupplyReceipt.objects.select_related("student", "recorded_by")
    if query:
        matching_items = [
            value
            for value, label in StoreSupplyReceipt.Item.choices
            if query.casefold() in label.casefold()
        ]
        supplies = supplies.filter(
            Q(item__icontains=query)
            | Q(item__in=matching_items)
            | Q(student__admission_number__icontains=query)
            | Q(student__first_name__icontains=query)
            | Q(student__middle_name__icontains=query)
            | Q(student__last_name__icontains=query)
            | Q(source__icontains=query)
            | Q(notes__icontains=query)
        )
    template = (
        "contributions/partials/supply_results.html"
        if request.headers.get("HX-Request") == "true"
        else "contributions/supply_list.html"
    )
    return render(request, template, {"supplies": supplies, "query": query})


@login_required
@role_required()
@reauthentication_required
@require_http_methods(["GET", "POST"])
def supply_delete(request, receipt_id):
    receipt = get_object_or_404(
        StoreSupplyReceipt.objects.select_related("student"),
        pk=receipt_id,
    )
    student = receipt.student or "Unassigned"
    record_title = (
        _("%(item)s (quantity %(quantity)s) for %(student)s")
        % {
            "item": receipt.get_item_display(),
            "quantity": receipt.quantity_collected,
            "student": student,
        }
    )
    return _confirm_record_deletion(
        request,
        receipt,
        record_title,
        "supply-list",
        notification={
            "recipient": receipt.recorded_by,
            "action": "deleted",
            "record_type": "Store supply receipt",
            "record_identifier": receipt.pk,
            "data": record_snapshot(receipt),
        },
    )


@login_required
@role_required()
def student_supply_history(request, student_id):
    student = get_object_or_404(
        Student.objects.select_related("parent"),
        pk=student_id,
    )
    receipts = StoreSupplyReceipt.objects.filter(student=student).select_related(
        "recorded_by"
    ).order_by("-collected_at", "-pk")
    item_labels = dict(StoreSupplyReceipt.Item.choices)
    supply_totals = [
        {
            "item_label": item_labels.get(entry["item"], entry["item"]),
            "quantity": entry["total_quantity"],
        }
        for entry in receipts.values("item")
        .annotate(total_quantity=Sum("quantity_collected"))
        .order_by("item")
    ]
    return render(
        request,
        "contributions/student_supply_history.html",
        {
            "student": student,
            "receipts": receipts,
            "supply_totals": supply_totals,
        },
    )


@login_required
@role_required(SECOND_HEAD_ROLE)
@reauthentication_required
@require_http_methods(["GET", "POST"])
def clothing_verification_delete(request, student_id, verification_id):
    verification = get_object_or_404(
        StudentClothingVerification.objects.select_related("student"),
        pk=verification_id,
        student_id=student_id,
    )
    record_title = (
        _("%(category)s: %(item)s for %(student)s")
        % {
            "category": verification.get_category_display(),
            "item": verification.clothing_item,
            "student": verification.student,
        }
    )
    return _confirm_record_deletion(
        request,
        verification,
        record_title,
        reverse("student-clothing", kwargs={"student_id": verification.student_id}),
        notification={
            "recipient": verification.recorded_by,
            "action": "deleted",
            "record_type": "Student clothing verification",
            "record_identifier": verification.pk,
            "data": record_snapshot(verification),
        },
    )


@login_required
@role_required()
def supply_create(request, receipt_id=None):
    receipt = None
    if receipt_id is not None:
        receipt = get_object_or_404(StoreSupplyReceipt, pk=receipt_id)
    initial = {}
    if receipt is None and request.method == "GET":
        initial_student = request.GET.get("student")
        if initial_student:
            initial["student"] = initial_student
    form = StoreSupplyReceiptForm(
        request.POST or None,
        instance=receipt,
        initial=initial or None,
    )
    item_formset_class = formset_factory(
        StoreSupplyItemForm,
        extra=0 if receipt else 1,
        min_num=1,
        validate_min=True,
    )
    initial_items = (
        [{"item": receipt.item, "quantity_collected": receipt.quantity_collected}]
        if receipt
        else None
    )
    item_formset = item_formset_class(
        request.POST or None,
        initial=initial_items,
        prefix="items",
    )
    if request.method == "POST":
        form_is_valid = form.is_valid()
        item_formset_is_valid = item_formset.is_valid()
        if form_is_valid and item_formset_is_valid:
            if receipt:
                before = record_snapshot(receipt)
                recipient = receipt.recorded_by
                with transaction.atomic():
                    supply = form.save(commit=False)
                    item_data = item_formset.cleaned_data[0]
                    supply.item = item_data["item"]
                    supply.quantity_collected = item_data["quantity_collected"]
                    supply.save()
                send_record_notification(
                    request,
                    recipient=recipient,
                    action="updated",
                    record_type="Store supply receipt",
                    record_identifier=supply.pk,
                    data={
                        "before": before,
                        "after": record_snapshot(supply),
                    },
                )
            else:
                student = form.cleaned_data["student"]
                recorded_items = []
                with transaction.atomic():
                    for item_data in item_formset.cleaned_data:
                        if not item_data:
                            continue
                        supply = StoreSupplyReceipt.objects.create(
                            student=student,
                            item=item_data["item"],
                            quantity_collected=item_data["quantity_collected"],
                            source=form.cleaned_data["source"],
                            notes=form.cleaned_data["notes"],
                            recorded_by=request.user,
                        )
                        recorded_items.append(
                            {
                                "receipt_id": supply.pk,
                                "item": supply.get_item_display(),
                                "quantity": supply.quantity_collected,
                            }
                        )
                send_record_notification(
                    request,
                    recipient=request.user,
                    action="recorded",
                    record_type="Store supply delivery",
                    record_identifier=student.admission_number,
                    data={
                        "student": str(student),
                        "items": recorded_items,
                        "source": form.cleaned_data["source"],
                        "notes": form.cleaned_data["notes"],
                    },
                )
            if receipt is None and request.GET.get("student"):
                return redirect(
                    "student-supply-history",
                    student_id=form.cleaned_data["student"].pk,
                )
            return redirect("supply-list")
    return render(
        request,
        "contributions/form.html",
        {
            "form": form,
            "supply_item_formset": item_formset,
            "editing_supply": receipt is not None,
            "eyebrow": _("Storekeeper · Supplies"),
            "title": _("Edit supply receipt") if receipt else _("Record supplies collected"),
            "description": (
                _("Update the student and details for this receipt.")
                if receipt
                else _("Record tools and other supplies received for a student.")
            ),
            "section_title": _("Supply receipt"),
            "section_description": (
                _("Select the student, then enter each item and its quantity.")
            ),
            "button_text": _("Update supply receipt") if receipt else _("Save supply items"),
            "cancel_url": "supply-list",
            "can_save": Student.objects.exists(),
            "prerequisite_title": _("Register a student first"),
            "prerequisite_description": _("Every supply receipt must be linked to a student."),
            "prerequisite_action": _("Register student"),
            "prerequisite_url": "student-create",
        },
    )


@login_required
@role_required(SECOND_HEAD_ROLE)
def student_clothing(request, student_id, verification_id=None):
    student = get_object_or_404(
        Student.objects.select_related("parent"),
        pk=student_id,
    )
    verification = None
    if verification_id is not None:
        verification = get_object_or_404(
            StudentClothingVerification,
            pk=verification_id,
            student=student,
        )
    form = StudentClothingVerificationForm(
        request.POST or None,
        instance=verification,
    )
    if request.method == "POST" and form.is_valid():
        before = record_snapshot(verification) if verification else None
        recipient = verification.recorded_by if verification else request.user
        clothing_check = form.save(commit=False)
        clothing_check.student = student
        if verification is None:
            clothing_check.recorded_by = request.user
        if clothing_check.is_verified:
            if clothing_check.verified_at is None:
                clothing_check.verified_at = timezone.now()
                clothing_check.verified_by = request.user
        else:
            clothing_check.verified_at = None
            clothing_check.verified_by = None
        clothing_check.save()
        send_record_notification(
            request,
            recipient=recipient,
            action="updated" if verification else "recorded",
            record_type="Student clothing verification",
            record_identifier=clothing_check.pk,
            data={
                "before": before,
                "after": record_snapshot(clothing_check),
            }
            if verification
            else record_snapshot(clothing_check),
        )
        return redirect("student-clothing", student_id=student.pk)

    return render(
        request,
        "contributions/student_clothing.html",
        {
            "student": student,
            "form": form,
            "verification": verification,
            "verifications": student.clothing_verifications.select_related(
                "recorded_by",
                "verified_by",
            ),
        },
    )
