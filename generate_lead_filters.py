import pandas as pd
from leads.models import Lead

def get_unique_choices(field_name, blank_label, use_title_case=True):
    """
    Generates cleaned, unique, and sorted filter choices from the Lead model.
    use_title_case: Agar True hai, toh values ko .title() karega.
    """
    all_values = Lead.objects.values_list(field_name, flat=True)
    unique_cleaned_values = set()
    for value in all_values:
        if value:
            # Hamesha extra space (left/right) hatao
            cleaned_value = str(value).strip() 
            
            # Sirf zaroorat padne par hi title case istemaal karo
            if use_title_case:
                cleaned_value = cleaned_value.title()
                
            if cleaned_value:
                unique_cleaned_values.add(cleaned_value)
    
    sorted_values = sorted(list(unique_cleaned_values))
    return [('', blank_label)] + [(val, val) for val in sorted_values]

def generate_filters(request):
    """
    Generates cleaned, unique, and sorted filter choices from the Lead model.
    """
    
    # --- YAHAN BADLAV HUA HAI ---
    # Job Title ke liye title_case=False, taaki original data se match ho sake
    JOB_TITLE_CHOICES = get_unique_choices('job_title', 'All Job Titles', use_title_case=False)
    
    # Baaki filters ke liye title_case=True (optional, behtar dikhne ke liye)
    INDUSTRY_CHOICES = get_unique_choices('industry', 'All Industries', use_title_case=True)
    PERSON_COUNTRY_CHOICES = get_unique_choices('person_country', 'All Person Countries', use_title_case=True)
    COMPANY_COUNTRY_CHOICES = get_unique_choices('company_country', 'All Company Countries', use_title_case=True)

    return {
        'JOB_TITLE_CHOICES': JOB_TITLE_CHOICES,
        'INDUSTRY_CHOICES': INDUSTRY_CHOICES,
        'PERSON_COUNTRY_CHOICES': PERSON_COUNTRY_CHOICES,
        'COMPANY_COUNTRY_CHOICES': COMPANY_COUNTRY_CHOICES,
    }