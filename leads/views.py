from django.shortcuts import render
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth.models import Group
from .models import Lead
from .forms import LeadFilterForm, LeadsUploadForm
from accounts import models
from generate_lead_filters import generate_filters

import csv


@login_required
def upload_leads(request):
    # Check if the user is a superuser or in the 'Managers' group
    is_manager = request.user.groups.filter(name='Managers').exists()
    if not (request.user.is_superuser or is_manager):
        messages.error(request, "You do not have permission to upload leads.")
        return redirect('leads:leads_list')

    if request.method == 'POST':
        form = LeadsUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            overwrite = form.cleaned_data['overwrite']
            
            try:
                # Handle different file types
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                else:  # Excel files
                    df = pd.read_excel(file)
                
                # Column mapping — flexible matching for real-world variations
                COLUMN_MAPPING = {
                    # Person/Contact Info
                    'Full Name': 'full_name',
                    'First Name': 'first_name',
                    'Last Name': 'last_name',
                    'Job Title': 'job_title',
                    'Professional Email': 'professional_email',
                    'Email': 'professional_email',  # Accept "Email" as alias
                    'Email Status': 'email_status',
                    'Personal Email': 'personal_email',
                    'Person Linkedin Url': 'person_linkedin_url',
                    'Linkedin Url': 'person_linkedin_url',  # Accept this too
                    'Person City': 'person_city',
                    'Person State': 'person_state',
                    'Person Country': 'person_country',
                    'Person Direct Phone Number': 'person_direct_phone',
                    'Phone': 'person_direct_phone',  # Accept "Phone"

                    # Company Info
                    'Lead ID': 'lead_id',
                    'Company ID': 'company_id',
                    'Company Name': 'company_name',
                    'Company Website': 'company_website',
                    'Website': 'company_website',  # Accept "Website"
                    'Industry': 'industry',
                    'Employees': 'employees',
                    'Generic Email': 'generic_email',
                    'Full Address': 'full_address',
                    'First Address': 'first_address',
                    'Company City': 'company_city',
                    'Company State': 'company_state',
                    'Zip code': 'zip_code',
                    'Company Country': 'company_country',
                    'Company Linkedin Url': 'company_linkedin_url',
                    'Company Phone Numbers': 'company_phone',
                    'Company Phone': 'company_phone',  # Accept shorter version
                    'Comment': 'comments',
                    'Comments': 'comments',
                }

                # Normalize column names (strip whitespace, case-insensitive matching)
                column_map = {}
                for col in df.columns:
                    col_clean = col.strip()
                    # Try exact match first
                    if col_clean in COLUMN_MAPPING:
                        column_map[col] = COLUMN_MAPPING[col_clean]
                    else:
                        # Try case-insensitive match
                        for key in COLUMN_MAPPING:
                            if key.lower() == col_clean.lower():
                                column_map[col] = COLUMN_MAPPING[key]
                                break

                # Process each row
                success_count = 0
                error_count = 0
                errors = []

                for index, row in df.iterrows():
                    try:
                        # Build lead data with mapped columns
                        lead_data = {
                            'source': 'Uploaded File',
                            'created_by': request.user
                        }

                        for original_col, model_field in column_map.items():
                            value = row.get(original_col, '')
                            # Handle NaN/None values
                            if pd.isna(value) or value is None:
                                value = ''
                            else:
                                value = str(value).strip()
                            lead_data[model_field] = value

                        # Validate required field: professional_email
                        email = lead_data.get('professional_email')
                        if not email:
                            raise ValueError("Professional Email is required and missing")

                        # Check for existing lead
                        if overwrite and Lead.objects.filter(professional_email=email).exists():
                            lead = Lead.objects.get(professional_email=email)
                            for key, value in lead_data.items():
                                if key != 'created_by':  # Preserve creator
                                    setattr(lead, key, value)
                            lead.save()
                        else:
                            Lead.objects.create(**lead_data)

                        success_count += 1

                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {index + 2}: {str(e)}")

                # Show feedback messages
                if success_count > 0:
                    messages.success(request, f"✅ Successfully processed {success_count} leads.")
                if error_count > 0:
                    messages.warning(request, f"⚠️ Failed to process {error_count} leads. First 5 errors:")
                    for error in errors[:5]:
                        messages.error(request, error)

                return redirect('leads:leads_list')

            except Exception as e:
                messages.error(request, f"❌ Error processing file: {str(e)}")
                return render(request, 'leads/upload_leads.html', {'form': form})

    else:
        form = LeadsUploadForm()

    return render(request, 'leads/upload_leads.html', {'form': form})

@login_required
def leads_list(request):
    leads = Lead.objects.all()
    
    # Generate filter choices
    filter_choices = generate_filters(request)
    
    # Apply filters
    form = LeadFilterForm(request.GET, **filter_choices)
    if form.is_valid():
        status = form.cleaned_data.get('status')
        company = form.cleaned_data.get('company_name')
        job_title = form.cleaned_data.get('job_title')
        industry = form.cleaned_data.get('industry')
        search = form.cleaned_data.get('search')
        person_country = form.cleaned_data.get('person_country')
        company_country = form.cleaned_data.get('company_country')
        employees = form.cleaned_data.get('employees')
        revenue = form.cleaned_data.get('revenue')
        
        if status:
            leads = leads.filter(status=status)
        if company:
            leads = leads.filter(company_name__icontains=company)
        if job_title:
            leads = leads.filter(job_title__icontains=job_title)
        if industry:
            leads = leads.filter(industry__icontains=industry)
        if person_country:
            leads = leads.filter(person_country__icontains=person_country)
        if company_country:
            leads = leads.filter(company_country__icontains=company_country)
        if employees:
            leads = leads.filter(employees__icontains=employees)
        if revenue:
            leads = leads.filter(revenue__icontains=revenue)
        if search:
            leads = leads.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(professional_email__icontains=search) |
                Q(personal_email__icontains=search) |
                Q(company_name__icontains=search)
            )
    
    # Pagination
    paginator = Paginator(leads, 25)  # Show 25 leads per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'leads/leads_list.html', {
        'leads': page_obj,
        'form': form,
        'page_obj': page_obj
    })

@login_required
def export_leads(request):
    """
    Exports filtered leads to a CSV file.
    """
    leads = Lead.objects.filter(created_by=request.user)
    
    # Generate filter choices to instantiate the form correctly, although we don't display it
    filter_choices = generate_filters(request)
    
    # Apply the same filters as the list view
    form = LeadFilterForm(request.GET, **filter_choices)
    if form.is_valid():
        status = form.cleaned_data.get('status')
        company = form.cleaned_data.get('company_name')
        job_title = form.cleaned_data.get('job_title')
        industry = form.cleaned_data.get('industry')
        search = form.cleaned_data.get('search')
        person_country = form.cleaned_data.get('person_country')
        company_country = form.cleaned_data.get('company_country')
        employees = form.cleaned_data.get('employees')
        revenue = form.cleaned_data.get('revenue')
        
        if status:
            leads = leads.filter(status=status)
        if company:
            leads = leads.filter(company_name__icontains=company)
        if job_title:
            leads = leads.filter(job_title__icontains=job_title)
        if industry:
            leads = leads.filter(industry__icontains=industry)
        if person_country:
            leads = leads.filter(person_country__icontains=person_country)
        if company_country:
            leads = leads.filter(company_country__icontains=company_country)
        if employees:
            leads = leads.filter(employees__icontains=employees)
        if revenue:
            leads = leads.filter(revenue__icontains=revenue)
        if search:
            leads = leads.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(professional_email__icontains=search) |
                Q(personal_email__icontains=search) |
                Q(company_name__icontains=search)
            )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leads.csv"'

    writer = csv.writer(response)
    # Define the fields you want in your CSV
    field_names = ['full_name', 'job_title', 'professional_email', 'company_name', 'industry', 'status', 'comments']
    writer.writerow(field_names)

    for lead in leads:
        writer.writerow([getattr(lead, field) for field in field_names])

    return response

@login_required
def download_sample_csv(request):
    # Create a sample CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leads_sample.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Lead ID', 'Full Name', 'First Name', 'Last Name', 'Job Title', 
        'Professional Email', 'Email Status', 'Personal Email', 'Person Linkedin Url',
        'Person City', 'Person State', 'Person Country', 'Person Direct Phone Number',
        'Company ID', 'Company Name', 'Company Website', 'Industry', 'Employees',
        'Generic Email', 'Full Address', 'First Address', 'Company City', 'Company State',
        'Zip code', 'Company Country', 'Company Linkedin Url', 'Company Phone Numbers', 'Comments'
    ])
    writer.writerow([
        'L001', 'John Doe', 'John', 'Doe', 'CEO', 
        'john.doe@example.com', 'Verified', 'john.personal@example.com', 'https://linkedin.com/in/johndoe',
        'New York', 'NY', 'USA', '+1234567890',
        'C001', 'Example Inc', 'https://example.com', 'Technology', '100-500',
        'info@example.com', '123 Main St, New York, NY 10001', '123 Main St', 'New York', 'NY',
        '10001', 'USA', 'https://linkedin.com/company/example', '+1987654321', 'Interested in our product'
    ])
    
    return response
                