from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ADMIN = 'admin'
    STAFF = 'staff'
    CLIENT = 'client'
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('client', 'Client'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')

    def __str__(self):
        return self.username

