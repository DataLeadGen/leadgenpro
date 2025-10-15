
import pandas as pd
from leads.models import Lead

def generate_filters(request):
    """
    Generates filter choices from the Lead model.
    """
    # Get distinct values for filterable fields
    industries = Lead.objects.values_list('industry', flat=True).distinct()
    person_countries = Lead.objects.values_list('person_country', flat=True).distinct()
    company_countries = Lead.objects.values_list('company_country', flat=True).distinct()
    employees_options = Lead.objects.values_list('employees', flat=True).distinct()
    
    # Create choices for the form, including a blank option for 'All'
    INDUSTRY_CHOICES = [('', 'All Industries')] + [(industry, industry) for industry in industries if industry]
    PERSON_COUNTRY_CHOICES = [('', 'All Person Countries')] + [(country, country) for country in person_countries if country]
    COMPANY_COUNTRY_CHOICES = [('', 'All Company Countries')] + [(country, country) for country in company_countries if country]
    EMPLOYEES_CHOICES = [('', 'All Sizes')] + [(emp, emp) for emp in employees_options if emp]

    return {
        'INDUSTRY_CHOICES': INDUSTRY_CHOICES,
        'PERSON_COUNTRY_CHOICES': PERSON_COUNTRY_CHOICES,
        'COMPANY_COUNTRY_CHOICES': COMPANY_COUNTRY_CHOICES,
        'EMPLOYEES_CHOICES': EMPLOYEES_CHOICES,
    }
