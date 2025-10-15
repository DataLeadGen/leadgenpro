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
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Qualified', 'Qualified'),
        ('Lost', 'Lost'),
    ]

    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    company_name = forms.CharField(max_length=200, required=False, label='Company Name')
    job_title = forms.CharField(max_length=200, required=False, label='Job Title')
    industry = forms.ChoiceField(choices=[], required=False)
    search = forms.CharField(max_length=200, required=False, label='Search')
    person_country = forms.ChoiceField(choices=[], required=False, label='Person Country')
    company_country = forms.ChoiceField(choices=[], required=False, label='Company Country')
    employees = forms.ChoiceField(choices=[], required=False, label='Employees')
    revenue = forms.CharField(required=False, label='Revenue')

    def __init__(self, *args, **kwargs):
        INDUSTRY_CHOICES = kwargs.pop('INDUSTRY_CHOICES', [])
        PERSON_COUNTRY_CHOICES = kwargs.pop('PERSON_COUNTRY_CHOICES', [])
        COMPANY_COUNTRY_CHOICES = kwargs.pop('COMPANY_COUNTRY_CHOICES', [])
        EMPLOYEES_CHOICES = kwargs.pop('EMPLOYEES_CHOICES', [])
        
        super(LeadFilterForm, self).__init__(*args, **kwargs)
        
        self.fields['industry'].choices = INDUSTRY_CHOICES
        self.fields['person_country'].choices = PERSON_COUNTRY_CHOICES
        self.fields['company_country'].choices = COMPANY_COUNTRY_CHOICES
        self.fields['employees'].choices = EMPLOYEES_CHOICES