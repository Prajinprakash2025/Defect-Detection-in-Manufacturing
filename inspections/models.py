from django.db import models
from django.conf import settings
from core_inventory.models import Batch

class Inspection(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Defective', 'Defective'),
        ('Non-Defective', 'Non-Defective'),
    )

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='inspections')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    image = models.ImageField(upload_to='inspection_images/')
    prediction_label = models.CharField(max_length=100, blank=True, null=True)
    confidence_score = models.FloatField(blank=True, null=True)
    raw_prediction_json = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_training_data = models.BooleanField(default=False, help_text="Marked as High-Value Training Data")
    is_manually_verified = models.BooleanField(default=False, help_text="Verified by Human Admin")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inspection {self.id} - {self.batch.batch_number}"

class Defect(models.Model):
    SEVERITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    )

    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='defects')
    defect_type = models.CharField(max_length=100)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='Medium')

    def __str__(self):
        return f"{self.defect_type} ({self.severity})"

class Alert(models.Model):
    STATUS_CHOICES = (
        ('Unread', 'Unread'),
        ('Read', 'Read'),
    )

    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='alerts')
    message = models.TextField()
    alert_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unread')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert for Inspection {self.inspection.id}"
