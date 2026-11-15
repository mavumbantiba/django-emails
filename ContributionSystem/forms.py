from django import forms

from .models import (
    Parent,
    Student,
    StudentClothingVerification,
    StudentCollection,
    StoreSupplyReceipt,
)


class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ("full_name", "phone_number", "email")


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        exclude = ("registered_at", "registered_by")
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }


class StudentCollectionForm(forms.ModelForm):
    class Meta:
        model = StudentCollection
        exclude = ("recorded_at", "recorded_by")


class StoreSupplyReceiptForm(forms.ModelForm):
    student = forms.ModelChoiceField(queryset=Student.objects.all())

    class Meta:
        model = StoreSupplyReceipt
        fields = ("student", "source", "notes")


class StoreSupplyItemForm(forms.Form):
    item = forms.ChoiceField(choices=StoreSupplyReceipt.Item.choices)
    quantity_collected = forms.IntegerField(min_value=1)


class StudentClothingVerificationForm(forms.ModelForm):
    class Meta:
        model = StudentClothingVerification
        fields = ("category", "clothing_item", "is_verified", "notes")
