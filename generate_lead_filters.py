import pandas as pd
from leads.models import Lead

def generate_filters(request):
    """
    Generates cleaned, unique, and sorted filter choices from the Lead model.
    """
    
    # Helper function (pehle jaisa hi)
    def get_unique_choices(field_name, blank_label):
        all_values = Lead.objects.values_list(field_name, flat=True)
        unique_cleaned_values = set()
        for value in all_values:
            if value:
                cleaned_value = str(value).strip().title() 
                if cleaned_value:
                    unique_cleaned_values.add(cleaned_value)
        
        sorted_values = sorted(list(unique_cleaned_values))
        return [('', blank_label)] + [(val, val) for val in sorted_values]

    # Dynamic choices (Industry, Country)
    INDUSTRY_CHOICES = get_unique_choices('industry', 'All Industries')
    PERSON_COUNTRY_CHOICES = get_unique_choices('person_country', 'All Person Countries')
    COMPANY_COUNTRY_CHOICES = get_unique_choices('company_country', 'All Company Countries')
    
    # --- YAHAN BADLAV HUA HAI ---
    # EMPLOYEES_CHOICES ko yahan se hata diya gaya hai

    return {
        'INDUSTRY_CHOICES': INDUSTRY_CHOICES,
        'PERSON_COUNTRY_CHOICES': PERSON_COUNTRY_CHOICES,
        'COMPANY_COUNTRY_CHOICES': COMPANY_COUNTRY_CHOICES,
        # 'EMPLOYEES_CHOICES' yahan nahi hai
    }