from django.db import models
from django.utils import timezone

class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    visual_guide = models.TextField(blank=True)
    material_type = models.CharField(max_length=100, blank=True)
    handling_guidelines = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Batch(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Paused', 'Paused'),
        ('Completed', 'Completed'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100, unique=True)
    manufacture_date = models.DateField(default=timezone.now)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    inspector_notes = models.TextField(blank=True)
    inspector_instructions = models.TextField(blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.batch_number}"
