from django.conf import settings
from django.db import models


class Parent(models.Model):
    full_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=30)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"


class Student(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "F", "Female"
        MALE = "M", "Male"
        OTHER = "O", "Other"

    admission_number = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    date_of_birth = models.DateField(null=True, blank=True)
    class_level = models.CharField(max_length=30)
    parent = models.ForeignKey(
        Parent,
        on_delete=models.PROTECT,
        related_name="students",
    )
    region = models.CharField(max_length=100, default="Kagera")
    district = models.CharField(max_length=100, default="Karagwe")
    ward = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    street = models.CharField(max_length=100)
    registered_at = models.DateField(auto_now_add=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_students",
    )

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.admission_number} - {self.first_name} {self.last_name}"


class StudentCollection(models.Model):
    class Category(models.TextChoices):
        ACADEMIC_FEE = "academic_fee", "Academic fee"
        REAM_A4 = "ream_a4", "A4 ream"
        TSHIRT = "tshirt", "T-shirt"
        SCHOOL_GUARD_FEE = "school_guard_fee", "School guard fee"
        NECKTIE = "necktie", "Necktie"
        LOGO = "logo", "Logo"
        TABLE = "table", "Table"
        CHAIR = "chair", "Chair"

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="collections",
    )
    category = models.CharField(max_length=30, choices=Category.choices)
    amount_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_issued = models.PositiveIntegerField(default=0)
    recorded_at = models.DateField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_collections",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-recorded_at", "student"]

    def __str__(self):
        return f"{self.student} - {self.get_category_display()}"
