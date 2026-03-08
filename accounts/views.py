from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .forms import CustomUserCreationForm

class SignUpView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('user_list')
    template_name = 'registration/signup.html'
    login_url = reverse_lazy('login')

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.role in ['admin', 'manager'] or user.is_superuser)

    def handle_no_permission(self):
        messages.error(self.request, "Only admins and managers can create new accounts.")
        return redirect('login')

    def form_valid(self, form):
        # Admin/Manager provisioning: create active account with default inspector role
        self.object = form.save(commit=False)
        self.object.role = 'inspector'
        self.object.is_active = True
        self.object.save()
        messages.success(self.request, f"User {self.object.username} created. Share credentials securely with the user.")
        return super().form_valid(form)

# --- Custom User Management Views ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from .models import CustomUser
from django.contrib.auth.hashers import make_password

def is_admin(user):
    # Allow admins and managers to manage users
    return user.is_authenticated and (user.role in ['admin', 'manager'] or user.is_superuser)

@user_passes_test(is_admin)
def user_list(request):
    if request.method == 'POST' and request.POST.get('action') == 'create':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', 'inspector')
        active = request.POST.get('active') == 'on'

        if not username or not password:
            messages.error(request, "Username and password are required.")
        elif role not in dict(CustomUser.ROLE_CHOICES):
            messages.error(request, "Invalid role selected.")
        elif CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            user = CustomUser.objects.create(
                username=username,
                email=email,
                role=role,
                is_active=active,
                password=make_password(password),
            )
            messages.success(request, f"User {user.username} created as {user.get_role_display()}{' (inactive)' if not active else ''}.")

    users = CustomUser.objects.all().order_by('-date_joined')
    pending_count = CustomUser.objects.filter(is_active=False).count()
    return render(request, 'users/user_list.html', {'users': users, 'pending_count': pending_count})

@user_passes_test(is_admin)
def edit_user_role(request, pk):
    user_to_edit = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(CustomUser.ROLE_CHOICES):
            user_to_edit.role = new_role
            user_to_edit.save()
            messages.success(request, f"Role for {user_to_edit.username} updated to {user_to_edit.get_role_display()}.")
        else:
            messages.error(request, "Invalid role selected.")
    return redirect('user_list')

@user_passes_test(is_admin)
def delete_user(request, pk):
    user_to_delete = get_object_or_404(CustomUser, pk=pk)
    # Prevent deleting self
    if user_to_delete == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_list')

    if request.method == 'POST':
        user_to_delete.delete()
        messages.success(request, "User deleted successfully.")
    return redirect('user_list')

@user_passes_test(is_admin)
def toggle_user_active(request, pk):
    user_to_edit = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        user_to_edit.is_active = not user_to_edit.is_active
        user_to_edit.save()
        state = "activated" if user_to_edit.is_active else "deactivated"
        messages.success(request, f"{user_to_edit.username} {state}.")
    return redirect('user_list')
