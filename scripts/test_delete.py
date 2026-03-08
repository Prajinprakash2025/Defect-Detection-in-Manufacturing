import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()
from django.test import Client
from inspections.models import Inspection
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.get(username='admin')

# Use actual existing inspections for the test
inspections = list(Inspection.objects.all()[:2])
ids_to_delete = [i.id for i in inspections]

print(f"Before delete: {Inspection.objects.filter(id__in=ids_to_delete).count()} inspections exist")

client = Client()
client.force_login(admin)

response = client.post('/inspections/bulk-delete/', {'inspection_ids': ids_to_delete})

print(f"Response status: {response.status_code}")
print(f"After delete: {Inspection.objects.filter(id__in=ids_to_delete).count()} inspections exist")
