from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.create_product, name='create_product'),
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/create/', views.create_batch, name='create_batch'),
    path('batches/edit/<int:pk>/', views.edit_batch, name='edit_batch'),
    path('batches/delete/<int:pk>/', views.delete_batch, name='delete_batch'),
]
