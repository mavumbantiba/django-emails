from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import (
    Parent,
    Student,
    StudentClothingVerification,
    StudentCollection,
    StoreSupplyReceipt,
)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name")
        labels = {
            "username": _("Username"),
            "first_name": _("First name"),
            "last_name": _("Last name"),
        }


class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ("full_name", "phone_number", "email")
        labels = {
            "full_name": _("Full name"),
            "phone_number": _("Phone number"),
            "email": _("Email"),
        }


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        exclude = ("registered_at", "registered_by")
        labels = {
            "admission_number": _("Admission number"),
            "first_name": _("First name"),
            "middle_name": _("Middle name"),
            "last_name": _("Last name"),
            "gender": _("Gender"),
            "date_of_birth": _("Date of birth"),
            "class_level": _("Class level"),
            "parent": _("Parent"),
            "region": _("Region"),
            "district": _("District"),
            "ward": _("Ward"),
            "village": _("Village"),
            "street": _("Street"),
        }
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }


class StudentCollectionForm(forms.ModelForm):
    def __init__(self, *args, allowed_categories=None, **kwargs):
        super().__init__(*args, **kwargs)
        if allowed_categories is not None:
            self.fields["category"].choices = [
                choice
                for choice in self.fields["category"].choices
                if choice[0] == "" or choice[0] in allowed_categories
            ]

    class Meta:
        model = StudentCollection
        exclude = ("recorded_at", "recorded_by")
        labels = {
            "student": _("Student"),
            "category": _("Category"),
            "amount_collected": _("Amount collected"),
            "quantity_issued": _("Quantity issued"),
            "notes": _("Notes"),
        }


class StoreSupplyReceiptForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        label=_("Student"),
    )

    class Meta:
        model = StoreSupplyReceipt
        fields = ("student", "source", "notes")
        labels = {
            "source": _("Source"),
            "notes": _("Notes"),
        }


class StoreSupplyItemForm(forms.Form):
    item = forms.ChoiceField(
        choices=StoreSupplyReceipt.Item.choices,
        label=_("Item"),
    )
    quantity_collected = forms.IntegerField(
        min_value=1,
        label=_("Quantity collected"),
    )


class StudentClothingVerificationForm(forms.ModelForm):
    class Meta:
        model = StudentClothingVerification
        fields = ("category", "clothing_item", "is_verified", "notes")
        labels = {
            "category": _("Category"),
            "clothing_item": _("Clothing item"),
            "is_verified": _("Is verified"),
            "notes": _("Notes"),
        }
