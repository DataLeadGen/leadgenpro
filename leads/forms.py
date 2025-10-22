from django import forms
from .models import Lead

class LeadsUploadForm(forms.Form):
    file = forms.FileField(
        label='Select CSV or Excel File',
        help_text='Supported formats: .csv, .xls, .xlsx',
        widget=forms.FileInput(attrs={'accept':'.csv, .xls, .xlsx'})
    )
    
    overwrite = forms.BooleanField(
        required=False,
        initial=False,
        label='Overwrite existing leads',
        help_text='If checked, existing leads with same professional email will be updated'
    )

class LeadFilterForm(forms.Form):
    # --- Status filter yahan se hata diya gaya hai ---
    
    # Standard text inputs
    company_name = forms.CharField(max_length=200, required=False, label='Company Name')
    job_title = forms.CharField(max_length=200, required=False, label='Job Title')
    search = forms.CharField(max_length=200, required=False, label='Search')
    revenue = forms.CharField(required=False, label='Revenue')

    # --- Autocomplete Inputs (CharField + Datalist) ---
    industry = forms.CharField(
        required=False, 
        label='Industry',
        widget=forms.TextInput(attrs={'list': 'industry-datalist', 'autocomplete': 'off'})
    )
    
    person_country = forms.CharField(
        required=False, 
        label='Person Country',
        widget=forms.TextInput(attrs={'list': 'person-country-datalist', 'autocomplete': 'off'})
    )
    
    company_country = forms.CharField(
        required=False, 
        label='Company Country',
        widget=forms.TextInput(attrs={'list': 'company-country-datalist', 'autocomplete': 'off'})
    )
    
    # --- Employee Range Dropdown (ChoiceField) ---
    employees = forms.ChoiceField(choices=[], required=False, label='Employees')

    def __init__(self, *args, **kwargs):
        # View se sirf pre-defined employee ranges ko yahan pass kiya jayega
        EMPLOYEES_CHOICES = kwargs.pop('EMPLOYEES_CHOICES', [])
        
        super(LeadFilterForm, self).__init__(*args, **kwargs)
        
        # Sirf employee dropdown ke choices set kiye jayenge
        self.fields['employees'].choices = EMPLOYEES_CHOICES