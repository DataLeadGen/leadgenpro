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
    
    # --- YAHAN BADLAV HUA HAI: Employee filter (Dono) ---
    
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
        EMPLOYEES_CHOICES = kwargs.pop('EMPLOYEES_CHOICES', [])
        JOB_TITLE_CHOICES = kwargs.pop('JOB_TITLE_CHOICES', [])
        INDUSTRY_CHOICES = kwargs.pop('INDUSTRY_CHOICES', [])
        PERSON_COUNTRY_CHOICES = kwargs.pop('PERSON_COUNTRY_CHOICES', [])
        COMPANY_COUNTRY_CHOICES = kwargs.pop('COMPANY_COUNTRY_CHOICES', [])
        
        super(LeadFilterForm, self).__init__(*args, **kwargs)
        
        # Choices assign karein
        self.fields['employees_dropdown'].choices = EMPLOYEES_CHOICES # Badlaav
        self.fields['job_title'].choices = JOB_TITLE_CHOICES
        self.fields['industry'].choices = INDUSTRY_CHOICES
        self.fields['person_country'].choices = PERSON_COUNTRY_CHOICES
        self.fields['company_country'].choices = COMPANY_COUNTRY_CHOICES
        
        # Sabko optional banayein
        self.fields['job_title'].required = False
        self.fields['industry'].required = False
        self.fields['person_country'].required = False
        self.fields['company_country'].required = False
        self.fields['employees_dropdown'].required = False # Badlaav
        self.fields['employees_text'].required = False # Badlaav