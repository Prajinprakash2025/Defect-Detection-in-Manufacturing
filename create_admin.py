import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        user = User.objects.get(username='admin')
        user.role = 'admin'
        user.save()
        print("Superuser 'admin' created with password 'admin123' and role 'admin'.")
    else:
        user = User.objects.get(username='admin')
        if not user.is_superuser:
            user.is_superuser = True
            user.is_staff = True
        user.set_password('admin123')
        user.role = 'admin'
        user.save()
        print("User 'admin' updated to superuser/admin role with password 'admin123'.")
except Exception as e:
    print(f"Error creating/updating admin user: {e}")
