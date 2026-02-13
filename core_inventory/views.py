from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Product, Batch
from .forms import ProductForm, BatchForm

def is_admin(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

@login_required
@user_passes_test(is_admin)
def product_list(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, 'inventory/product_list.html', {'products': products})

@login_required
@user_passes_test(is_admin)
def create_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully.')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/create_product.html', {'form': form, 'title': 'Create Product'})

@login_required
@user_passes_test(is_admin)
def batch_list(request):
    batches = Batch.objects.select_related('product').all().order_by('-manufacture_date')
    return render(request, 'inventory/batch_list.html', {'batches': batches})

@login_required
@user_passes_test(is_admin)
def create_batch(request):
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Batch created successfully.')
            return redirect('batch_list')
    else:
        form = BatchForm()
    return render(request, 'inventory/create_batch.html', {'form': form, 'title': 'Create Batch'})

@login_required
@user_passes_test(is_admin)
def edit_batch(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Batch updated successfully.')
            return redirect('batch_list')
    else:
        form = BatchForm(instance=batch)
    return render(request, 'inventory/create_batch.html', {'form': form, 'title': 'Edit Batch'})

@login_required
@user_passes_test(is_admin)
def delete_batch(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        batch.delete()
        messages.success(request, 'Batch deleted successfully.')
        return redirect('batch_list')
    return render(request, 'inventory/delete_confirm.html', {'object': batch, 'type': 'Batch'})
