from django.db import models

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
