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
    
    company_name = forms.CharField(
        max_length=200, 
        required=False, 
        label='Company Name(s)',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Google, Microsoft'})
    )
    
    revenue = forms.CharField(
        required=False, 
        label='Revenue(s)',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., $1M, $5M-$10M'})
    )

    search = forms.CharField(
        max_length=200, 
        required=False, 
        label='General Search',
        widget=forms.TextInput(attrs={'placeholder': 'Search name, email, company...'})
    )

    # --- Multi-select dropdowns ---
    
    job_title = forms.MultipleChoiceField(
        required=False,
        label='Job Title(s)',
        widget=forms.SelectMultiple(attrs={'class': 'select2-multi', 'placeholder': 'Search job titles...'})
    )

    industry = forms.MultipleChoiceField(
        required=False,
        label='Industry(ies)',
        widget=forms.SelectMultiple(attrs={'class': 'select2-multi', 'placeholder': 'Search industries...'})
    )
    
    person_country = forms.MultipleChoiceField(
        required=False,
        label='Person Country(ies)',
        widget=forms.SelectMultiple(attrs={'class': 'select2-multi', 'placeholder': 'Search countries...'})
    )
    
    company_country = forms.MultipleChoiceField(
        required=False,
        label='Company Country(ies)',
        widget=forms.SelectMultiple(attrs={'class': 'select2-multi', 'placeholder': 'Search countries...'})
    )
    
    employees_dropdown = forms.MultipleChoiceField(
        required=False, 
        label='Employees (Select)',
        widget=forms.SelectMultiple(attrs={'class': 'select2-multi', 'placeholder': 'Select employee ranges...'})
    )
    
    employees_text = forms.CharField(
        required=False,
        label='Employees (Custom)',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 15 or 30-70'})
    )

    def __init__(self, *args, **kwargs):
        # Kwargs se choices ko pop karein
        choices = {
            'EMPLOYEES_CHOICES': kwargs.pop('EMPLOYEES_CHOICES', []),
            'JOB_TITLE_CHOICES': kwargs.pop('JOB_TITLE_CHOICES', []),
            'INDUSTRY_CHOICES': kwargs.pop('INDUSTRY_CHOICES', []),
            'PERSON_COUNTRY_CHOICES': kwargs.pop('PERSON_COUNTRY_CHOICES', []),
            'COMPANY_COUNTRY_CHOICES': kwargs.pop('COMPANY_COUNTRY_CHOICES', [])
        }
        
        super(LeadFilterForm, self).__init__(*args, **kwargs)
        
        # Fields ko dynamically update karein
        self.fields['employees_dropdown'].choices = choices['EMPLOYEES_CHOICES']
        self.fields['job_title'].choices = choices['JOB_TITLE_CHOICES']
        self.fields['industry'].choices = choices['INDUSTRY_CHOICES']
        self.fields['person_country'].choices = choices['PERSON_COUNTRY_CHOICES']
        self.fields['company_country'].choices = choices['COMPANY_COUNTRY_CHOICES']
        
        # Sabhi fields ko optional banayein (DRY principle)
        for field_name, field in self.fields.items():
            field.required = False