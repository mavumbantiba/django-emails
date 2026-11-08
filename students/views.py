from django.shortcuts import render, redirect
from .email_notifications import send_email_notification
from django.contrib import messages
from .forms import StudentRegitrationForm
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