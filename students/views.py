from django.shortcuts import render, redirect
from .email_notifications import send_email_notification,send_notifications
from django.contrib import messages
from .forms import StudentRegitrationForm
from .models import *
# Create your views here.


def home(request):
    return render(request,'templates/home.html')

def register_student(request):
    form=StudentRegitrationForm()
    if request.method=='POST':
        form=StudentRegitrationForm(request.POST)
        if form.is_valid():
            student=form.save()
            try:
                send_email_notification(student)
                messages.success(request,f'Student {student.name} has been registered successfully...!')
            except Exception:
                messages.warning(request,f'Student has been registered but email delivery failed')
            return redirect('register-student')
        else:
            form =StudentRegitrationForm()
            messages.error(request,'Something went wrong...')

    return render(request,'templates/register.html',{'form':form})


def send_notification(request):
    if request.method=='POST':
            try:
                notification=Notification.objects.create(subject=request.POST['subject'], message=request.POST['message'])
                send_notifications(notification)
                count=send_notifications(notification)
                messages.success(request,f' Notification sent successfully to users')
                return redirect('send-notification')
            except Exception:
                count=send_notifications(notification)
                notification=Notification.objects.create(subject=request.POST['subject'], message=request.POST['message'])
                send_notifications(notification)
                messages.warning(request,f'Notification sent but email delivering was failed')
            return redirect('send-notification')
    return render(request,'templates/notifications.html')

