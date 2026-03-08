import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from accounts.forms import CustomUserCreationForm
from accounts.models import CustomUser

def test_duplicate_username_validation():
    # 1. Ensure user exists
    username = "duplicate_user_test"
    if not CustomUser.objects.filter(username=username).exists():
        CustomUser.objects.create_user(username=username, password="password123")
        print(f"Created user: {username}")
    else:
        print(f"User {username} already exists")

    # 2. Try to create form with same username
    data = {
        'username': username,
        'email': 'test@example.com',
        'role': 'inspector',
        'password': 'password123',  # UserCreationForm expects password fields usually?
        # Actually UserCreationForm expects 'password1' and 'password2' by default.
        # But wait, looking at forms.py, we didn't add password fields to 'fields'.
        # UserCreationForm adds them by default.
    }
    
    # We need to simulate the POST data structure for UserCreationForm
    # It usually requires 'passwd1' and 'passwd2' or similar, depending on Django version.
    # Standard UserCreationForm fields are 'username', 'password', 'password_confirmation' (named differently).
    
    # Let's check fields of the form instance
    form = CustomUserCreationForm()
    print("Form fields:", form.fields.keys())
    
    # UserCreationForm usually has 'username', 'password' (as '1' and '2')
    data['password'] = 'password123' 
    # Let's inspect what fields are required.
    
    # To test validation of username specifically, we can ignore other errors for moment, 
    # but to call is_valid() we need other fields.
    
    # Let's try to pass standard password fields
    data['password_1'] = 'password123' # common name
    data['password_2'] = 'password123'
    
    # In recent Django, it is 'password' and 'password_confirmation'? 
    # No, usually declared as 'password_1' and 'password_2' in the form local fields.
    
    # Let's just create the form and see errors
    form = CustomUserCreationForm(data=data)
    
    if form.is_valid():
        print("FAILURE: Form is VALID despite duplicate username!")
    else:
        print("SUCCESS: Form is INVALID.")
        print("Errors:", form.errors)
        if 'username' in form.errors:
            print("Username error found:", form.errors['username'])
        else:
            print("Username error NOT found!")

if __name__ == "__main__":
    test_duplicate_username_validation()
