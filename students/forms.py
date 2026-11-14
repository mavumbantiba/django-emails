from django.forms import *
from .models import *

class StudentRegitrationForm(ModelForm):
    class Meta:
        model=Student
        fields='__all__'