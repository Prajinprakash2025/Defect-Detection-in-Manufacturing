from django import forms
from .models import Inspection
from core_inventory.models import Batch

class InspectionForm(forms.ModelForm):
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.all(),
        empty_label="Select a Batch",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Inspection
        fields = ['batch', 'image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not Batch.objects.exists():
            self.fields['batch'].help_text = "No batches available. Please create a batch first."
