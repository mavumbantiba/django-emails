from django.contrib import admin
from .models import *
# Register your models here.
from .email_notifications import send_email_notification
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail



@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display=('name','gender')


    def save_model(self,request,student,form,change):
        super().save_model(request,student,form,change)

        if not change:
            transaction.on_commit(lambda:send_email_notification(student))

    def delete_model(self,request,student):
        student_email=student.email
        student_name=student.name
        super().delete_model(request,student)
        transaction.on_commit(lambda:send_mail(
        'Student Deletion',
        f'Student registration with the name {student_name} and email {student_email} have been deleted',
        'settings.EMAIL_HOST_USER', [student_email],
            fail_silently=False,
            ))

