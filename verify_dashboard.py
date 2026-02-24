import os
import django
from django.db.models import Count, Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from core_dashboard.views import dashboard
from accounts.models import CustomUser
from inspections.models import Inspection, Batch

def verify():
    # 1. Check Total Users
    total_users = CustomUser.objects.count()
    print(f"Total Users in DB: {total_users}")
    
    # 2. Check Top Batch Logic (Reproduce view logic)
    print("\nCalculating Top Batch by Percentage...")
    base_qs = Inspection.objects.all()
    batch_stats = base_qs.values('batch__batch_number') \
        .annotate(total=Count('id'), defective=Count('id', filter=Q(status='Defective')))
    
    top_batch = None
    highest_rate = -1
    
    for stat in batch_stats:
        rate = (stat['defective'] / stat['total']) * 100 if stat['total'] > 0 else 0
        print(f"Batch: {stat['batch__batch_number']}, Total: {stat['total']}, Defective: {stat['defective']}, Rate: {rate:.1f}%")
        
        if rate > highest_rate:
            highest_rate = rate
            top_batch = stat['batch__batch_number']
            
    print(f"\nCalculated Top Batch: {top_batch} ({highest_rate:.1f}%)")

if __name__ == '__main__':
    verify()
