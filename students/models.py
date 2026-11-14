from django.db import models
from django.contrib.auth.models import User

class Student(models.Model):
    name=models.CharField(max_length=200)
    gender=models.CharField(max_length=20,choices={
        'MALE':'MALE',
        'FEMALE':'FEMALE'
    })
    email=models.EmailField(unique=True)

    class Meta:
        ordering=['name']

    def __str__(self):
        return self.name


class Notification(models.Model):
    subject=models.CharField(max_length=100)
    message=models.TextField()
    
    is_sent=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=['created_at']

    def __str__(self):
        return f'{self.subject}'