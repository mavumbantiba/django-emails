from django import forms

from .models import Parent, Student, StudentCollection


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
