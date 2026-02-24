from django import forms
from .models import Product, Batch

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'visual_guide', 'material_type', 'handling_guidelines']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'visual_guide': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'material_type': forms.TextInput(attrs={'class': 'form-control'}),
            'handling_guidelines': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['product', 'batch_number', 'manufacture_date', 'quantity', 'status', 'inspector_notes', 'inspector_instructions']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacture_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'inspector_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'inspector_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
