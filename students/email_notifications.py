from django.core.mail import *
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

def send_email_notification(student):
    send_mail(
        subject='REGISTRATION COMPLETED SUCCESSFUL',
        message=f'''
        Dear {student.name}

        Congratulation as you have been registered successfull with the following details:

        Name: {student.name}
        Gender: {student.gender}
        Email: {student.email}

        With Regards,

        School Administration
        Copyright@2026


        ''',
        recipient_list=[student.email],
        from_email=settings.DEFAULT_FROM_EMAIL,
        fail_silently=False
    )

    send_mail(
            subject='NEW STUDENT REGISTERED SUCCESSFUL',

            message=f'''
            Dear School Administrator

            You are hereby notified that a new student been registered successfull with the following details:

            Name: {student.name}
            Gender: {student.gender}
            Email:{student.email}

           

                With Regards,

                School Administration

                Copyright@2026
            ''',
            recipient_list=[settings.ADMIN_EMAIL],
            from_email=settings.DEFAULT_FROM_EMAIL,
            fail_silently=False,
    )


def send_notifications(notification):
        emails=User.objects.filter(is_active=True).exclude(email='').values_list('email',flat=True)
        send_mail(
            subject=notification.subject,
            message=f'''{notification.message}.
            This message was sent {notification.created_at}
            ''',
            from_email=None,
            recipient_list=list(emails),
            fail_silently=False
        )
        notification.is_sent=True
        notification.save()

def send_delete_notifications_to_admin(notification):
        deleted_at=timezone.now()
        emails=User.objects.filter(is_superuser=True).exclude(email='').values_list('email',flat=True)
        send_mail(
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
                )
        
        