from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth import login
from .forms import CustomUserCreationForm

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('dashboard')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        # Auto-login after signup
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

# --- Custom User Management Views ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from .models import CustomUser

def is_admin(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

@user_passes_test(is_admin)
def user_list(request):
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'users/user_list.html', {'users': users})

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
