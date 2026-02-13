from django.urls import path, include
from .views import SignUpView
from . import views

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('users/', views.user_list, name='user_list'),
    path('users/edit/<int:pk>/', views.edit_user_role, name='edit_user'),
    path('users/delete/<int:pk>/', views.delete_user, name='delete_user'),
    path('', include('django.contrib.auth.urls')),
]
