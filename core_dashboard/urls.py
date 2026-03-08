from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('inspector/dashboard/', views.inspector_dashboard, name='inspector_dashboard'),
    path('redirect/', views.role_redirect, name='role_redirect'),
    path('about/', views.about, name='about'),
    
]
