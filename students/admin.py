from django.contrib import admin
from .models import *
# Register your models here.
from .email_notifications import *
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

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display=('subject','message','is_sent','created_at')

    def save_model(self,request,notification,form,change):
            super().save_model(request,notification,form,change)
    
            if not change:
                transaction.on_commit(lambda:send_notifications(notification))

    def delete_model(request,notification):
                emails=User.objects.filter(is_superuser=True).exclude(email='').values_list('email',flat=True)
                deleted_at=timezone.now()
                super().delete_model(request,notification)
                transaction.on_commit(lambda:send_delete_notifications_to_admin(
                       subject='Notification deleted',
                                           message=f'''
                       
                                           Dear administrator, someone deleted the notification with the following information:
                                           Title: {notification.subject}.
                                           Message deleted: {notification.message}.
                                           Time the message was deleted: {deleted_at}
                                            
                                           ''',
                                           from_email=settings.ADMIN_EMAIL,
                                           recipient_list=list(emails),
                                           fail_silently=False
                 ))
         

