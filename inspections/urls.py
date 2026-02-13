from django.urls import path
from . import views

urlpatterns = [
    path('user-management/', views.user_management, name='user_management'),
    path('user-management/change-role/<int:pk>/', views.change_user_role, name='change_user_role'),
    path('upload/', views.upload_inspection, name='upload_inspection'),
    path('list/', views.inspection_list, name='inspection_list'),
    path('<int:pk>/', views.inspection_detail, name='inspection_detail'),
    path('delete/<int:pk>/', views.delete_inspection, name='delete_inspection'),
    path('verify/<int:pk>/', views.verify_result, name='verify_result'),
    path('alerts/', views.alert_list, name='alert_list'),
    path('export/', views.export_report, name='export_report'),
]
