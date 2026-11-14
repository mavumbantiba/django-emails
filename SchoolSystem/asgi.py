"""
ASGI config for SchoolSystem project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.contrib.messages import api

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SchoolSystem.settings')

application = get_asgi_application()
from students.models import *
from fastapi import FastAPI

api=FastAPI()
@api.get('/')
def home():
    students=Student.objects.all()
    return {
        'STUDENTS':[
            s.name,
            s.gender
        ] for s in students
    }

app=FastAPI()
app.mount('/',api)
app.mount('/',application)
