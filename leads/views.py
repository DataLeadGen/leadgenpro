from django.shortcuts import render
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db import models
from .models import Lead
from .forms import LeadFilterForm, LeadsUploadForm
from accounts import models

import csv


@login_required
def upload_leads(request):
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
                
                # Process each row
                success_count = 0
                error_count = 0
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Map CSV columns to model fields
                        lead_data = {
                            'first_name': row.get('first_name', ''),
                            'last_name': row.get('last_name', ''),
                            'email': row.get('email', ''),
                            'phone': row.get('phone', ''),
                            'company': row.get('company', ''),
                            'job_title': row.get('job_title', ''),
                            'industry': row.get('industry', ''),
                            'website': row.get('website', ''),
                            'location': row.get('location', ''),
                            'source': row.get('source', 'Uploaded CSV'),
                            'created_by': request.user
                        }
                        
                        # Check if lead already exists
                        if overwrite and Lead.objects.filter(email=lead_data['email']).exists():
                            # Update existing lead
                            lead = Lead.objects.get(email=lead_data['email'])
                            for key, value in lead_data.items():
                                if key != 'created_by':  # Don't update created_by
                                    setattr(lead, key, value)
                            lead.save()
                        else:
                            # Create new lead
                            Lead.objects.create(**lead_data)
                        
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {index + 2}: {str(e)}")
                
                # Show results message
                if success_count > 0:
                    messages.success(request, f"Successfully processed {success_count} leads.")
                if error_count > 0:
                    messages.warning(request, f"Failed to process {error_count} leads. Check errors below.")
                    for error in errors[:5]:  # Show first 5 errors
                        messages.error(request, error)
                
                return redirect('leads:leads_list')
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
    else:
        form = LeadsUploadForm()
    
    return render(request, 'leads/upload_leads.html', {'form': form})

@login_required
def leads_list(request):
    leads = Lead.objects.filter(created_by=request.user)
    
    # Apply filters
    form = LeadFilterForm(request.GET)
    if form.is_valid():
        status = form.cleaned_data.get('status')
        company = form.cleaned_data.get('company')
        industry = form.cleaned_data.get('industry')
        search = form.cleaned_data.get('search')
        
        if status:
            leads = leads.filter(status=status)
        if company:
            leads = leads.filter(company__icontains=company)
        if industry:
            leads = leads.filter(industry__icontains=industry)
        if search:
            leads = leads.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(company__icontains=search)
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
def download_sample_csv(request):
    # Create a sample CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leads_sample.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['first_name', 'last_name', 'email', 'phone', 'company', 
                     'job_title', 'industry', 'website', 'location', 'source'])
    writer.writerow(['John', 'Doe', 'john.doe@example.com', '+1234567890', 'Example Inc', 
                     'CEO', 'Technology', 'https://example.com', 'New York, USA', 'Website'])
    writer.writerow(['Jane', 'Smith', 'jane.smith@example.com', '+0987654321', 'Sample Co', 
                     'CTO', 'Finance', 'https://sample.com', 'London, UK', 'Referral'])
    
    return response
                