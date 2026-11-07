from django.core.mail import *

from django.conf import settings

def send_email_notification(student):
    send_mail(
        subject='REGISTRATION COMPLETED SUCCESSFUL...!',
        message=f'''Dear {student.name}, 
        Congratulation as you have been registered successfull with the following details:
        
        Name: {student.name}
        Gender: {student.gender}
        Email={student.email}

        Regards,

        School Administration
        ''',
        recipient_list=[student.email],
        from_email=settings.DEFAULT_FROM_EMAIL,
        fail_silently=False
    )

    send_mail(
            subject='NEW STUDENT REGISTERED SUCCESSFUL...!',
            message=f'''Dear School Administrator, 
            A new student been registered successfull with the following details:
            
            Name: {student.name}
            Gender: {student.gender}
            Email={student.email}
    
            Regards,
    
            School Administration
            ''',
            recipient_list=[settings.ADMIN_EMAIL],
            from_email=settings.DEFAULT_FROM_EMAIL,
            fail_silently=False,
    )
