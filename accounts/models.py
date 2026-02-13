from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('inspector', 'Quality Inspector'),
        ('manager', 'Production Manager'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='inspector')
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_inspector(self):
        return self.role == 'inspector' or self.is_superuser
        
    @property
    def is_manager(self):
        return self.role == 'manager' or self.is_superuser
