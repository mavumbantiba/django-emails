from django.urls import path
from students.views import *
urlpatterns=[
    path('',home,name='home'),
    path('register',register_student,name='register-student')
]