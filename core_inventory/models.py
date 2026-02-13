from django.db import models
from django.utils import timezone

class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Batch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100, unique=True)
    manufacture_date = models.DateField(default=timezone.now)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} - {self.batch_number}"
