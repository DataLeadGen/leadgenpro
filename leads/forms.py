from django import forms
from .models import Lead

class LeadsUploadForm(forms.Form):
    file = forms.FileField(
        label='Select CSV or Excel File',
        help_text='Supported formates: .csv, .xls, .xlsx',
        widget= forms.FileInput(attrs={'accept':'.csv, .xls, .xlsx'})
    )
    
    overwrite = forms.BooleanField(
        required=False,
        initial=False,
        label='Overwrite existing leads',
        help_text='If checked, existing leads with same email will be updated'
    )
    
class LeadFilterForm(forms.Form):
    STATUS_CHOICES =[
        ('', 'All Statuses'),
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Qualified', 'Qualified'),
        ('Lost', 'Lost'),
    ]
    
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    company = forms.CharField(max_length=200, required=False)
    industry = forms.CharField(max_length=200, required=False)
    search = forms.CharField(max_length=200, required=False, label='Search')
    