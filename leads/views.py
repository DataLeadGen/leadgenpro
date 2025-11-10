from django.shortcuts import render
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, F, Count 
from django.contrib.auth.models import Group, User
from .models import Lead
from .forms import LeadFilterForm, LeadsUploadForm
from accounts import models
from generate_lead_filters import generate_filters
import csv
import io
import os  # ✅ YEH LINE ADD KAREN
from django.forms.models import model_to_dict
from django.urls import reverse
from django.db import transaction

# utils.py se imports (Fallback ke saath)
try:
    from .utils import EMPLOYEE_RANGES, REVENUE_RANGES, check_range_overlap, parse_range_to_tuple
except ImportError:
    print("Warning: Could not import from utils.py. Using fallbacks.")
    EMPLOYEE_RANGES = [('', 'Any')]
    REVENUE_RANGES = [('', 'Any')]
    def check_range_overlap(filter_range_str, db_value_str): return True
    def parse_range_to_tuple(range_str): return (None, None)


@login_required
def upload_leads(request):
    """
    Improved Leads Upload Function with Better Error Handling and User Feedback
    """
    is_manager = request.user.groups.filter(name='Managers').exists()
    if not (request.user.is_superuser or is_manager):
        messages.error(request, "You do not have permission to upload leads.")
        return redirect('leads:leads_list')

    # Clear previous upload errors
    if 'upload_errors' in request.session:
        del request.session['upload_errors']

    if request.method == 'POST':
        form = LeadsUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            overwrite = form.cleaned_data['overwrite']
            
            # File validation
            allowed_extensions = ['.csv', '.xls', '.xlsx']
            file_extension = os.path.splitext(file.name)[1].lower()  # ✅ Ab yeh kaam karega
            
            if file_extension not in allowed_extensions:
                messages.error(request, f"❌ Invalid file format. Please upload CSV or Excel files only.")
                return render(request, 'leads/upload_leads.html', {'form': form})
            
            if file.size > 10 * 1024 * 1024:  # 10MB limit
                messages.error(request, "❌ File size too large. Please upload files smaller than 10MB.")
                return render(request, 'leads/upload_leads.html', {'form': form})

            try:
                # --- 1. Read File with Better Error Handling ---
                try:
                    if file.name.endswith('.csv'):
                        # CSV reading with encoding detection
                        try:
                            df = pd.read_csv(file, dtype=str, keep_default_na=False, encoding='utf-8')
                        except UnicodeDecodeError:
                            df = pd.read_csv(file, dtype=str, keep_default_na=False, encoding='latin-1')
                    else:
                        # Excel file reading
                        df = pd.read_excel(file, dtype=str, keep_default_na=False)
                except Exception as e:
                    messages.error(request, f"❌ Error reading file: {str(e)}")
                    return render(request, 'leads/upload_leads.html', {'form': form})

                # Check if file is empty
                if df.empty:
                    messages.error(request, "❌ The uploaded file is empty.")
                    return render(request, 'leads/upload_leads.html', {'form': form})

                df.fillna('', inplace=True)  # Replace NaN with empty strings

                # --- 2. Enhanced Column Mapping ---
                COLUMN_MAPPING = {
                    # Person fields
                    'Full Name': 'full_name', 
                    'First Name': 'first_name', 
                    'Last Name': 'last_name',
                    'Job Title': 'job_title', 
                    'Job Title/Role': 'job_title',
                    'Professional Email': 'professional_email', 
                    'Email': 'professional_email',
                    'Work Email': 'professional_email',
                    'Email Status': 'email_status', 
                    'Personal Email': 'personal_email',
                    'Person Linkedin Url': 'person_linkedin_url', 
                    'Linkedin Url': 'person_linkedin_url',
                    'LinkedIn Profile': 'person_linkedin_url',
                    'Person City': 'person_city', 
                    'Person State': 'person_state', 
                    'Person Country': 'person_country',
                    'Person Direct Phone Number': 'person_direct_phone', 
                    'Phone': 'person_direct_phone',
                    'Direct Phone': 'person_direct_phone',
                    'Mobile': 'person_direct_phone',
                    'Lead ID': 'lead_id', 
                    'Comments': 'comments', 
                    'Comment': 'comments',
                    'Notes': 'comments',

                    # Company fields
                    'Company ID': 'company_id', 
                    'Company Name': 'company_name',
                    'Organization': 'company_name',
                    'Company Website': 'company_website', 
                    'Website': 'company_website',
                    'Industry': 'industry', 
                    'Employees': 'employees', 
                    'Employee Count': 'employees',
                    'Company Size': 'employees',
                    'Revenue': 'revenue',
                    'Annual Revenue': 'revenue',
                    'Generic Email': 'generic_email', 
                    'Full Address': 'full_address',
                    'Address': 'full_address',
                    'First Address': 'first_address', 
                    'Company City': 'company_city', 
                    'Company State': 'company_state', 
                    'Zip code': 'zip_code',
                    'Postal Code': 'zip_code',
                    'Company Country': 'company_country',
                    'Company Linkedin Url': 'company_linkedin_url',
                    'Company LinkedIn': 'company_linkedin_url',
                    'Company Phone Numbers': 'company_phone', 
                    'Company Phone': 'company_phone',
                    'Office Phone': 'company_phone',
                }

                # --- 3. Smart Column Detection ---
                column_map = {}
                processed_model_fields = set()
                available_columns = []
                
                for col in df.columns:
                    col_clean = col.strip()
                    available_columns.append(col_clean)
                    mapped_field = None
                    
                    # Exact match check
                    if col_clean in COLUMN_MAPPING:
                        mapped_field = COLUMN_MAPPING[col_clean]
                    else:
                        # Fuzzy match - case insensitive
                        for key, value in COLUMN_MAPPING.items():
                            if key.lower() == col_clean.lower():
                                mapped_field = value
                                break
                    
                    if mapped_field and mapped_field not in processed_model_fields:
                        column_map[col] = mapped_field
                        processed_model_fields.add(mapped_field)

                # Check for required columns
                if 'professional_email' not in processed_model_fields:
                    messages.warning(request, "⚠️ 'Professional Email' column not found. Please check your file headers.")
                    # Show available columns for debugging
                    messages.info(request, f"Available columns in your file: {', '.join(available_columns)}")

                # --- 4. Process Rows with Detailed Reporting ---
                success_count = 0
                update_count = 0
                error_count = 0
                errors_list = []
                warnings_list = []

                try:
                    with transaction.atomic():
                        for index, row in df.iterrows():
                            row_number = index + 2  # +2 for header and 0-index
                            original_row_data = row.to_dict()

                            try:
                                lead_data = {
                                    'source': f'Uploaded File: {file.name}',
                                    'created_by': request.user
                                }
                                missing_required = []

                                # Process each column
                                for original_col, model_field in column_map.items():
                                    value = original_row_data.get(original_col, '')
                                    value = str(value).strip() if value not in [None, ''] else ''
                                    lead_data[model_field] = value

                                # Required fields validation
                                email = lead_data.get('professional_email', '')
                                if not email:
                                    missing_required.append('Professional Email')
                                else:
                                    # Basic email validation
                                    if '@' not in email:
                                        raise ValueError(f"Invalid email format: {email}")

                                # Name handling with better logic
                                f_name = lead_data.get('first_name', '')
                                l_name = lead_data.get('last_name', '')
                                full_name = lead_data.get('full_name', '')

                                if not f_name and not l_name:
                                    if full_name:
                                        # Smart name splitting
                                        name_parts = full_name.split(' ', 1)
                                        lead_data['first_name'] = name_parts[0].strip()
                                        lead_data['last_name'] = name_parts[1].strip() if len(name_parts) > 1 else ''
                                    else:
                                        missing_required.append('First Name/Last Name or Full Name')
                                
                                # Ensure we have at least first name
                                if not lead_data.get('first_name') and not lead_data.get('last_name'):
                                    raise ValueError("Could not extract valid name from data")

                                if missing_required:
                                    raise ValueError(f"Required field(s) missing: {', '.join(missing_required)}")

                                # Check for existing lead
                                existing_lead = Lead.objects.filter(professional_email=email).first()

                                if existing_lead:
                                    if overwrite:
                                        # Update existing lead
                                        updated_fields = []
                                        for key, value in lead_data.items():
                                            if key not in ['created_by', 'source'] and value:
                                                current_value = getattr(existing_lead, key, '')
                                                if current_value != value:
                                                    setattr(existing_lead, key, value)
                                                    updated_fields.append(key)
                                        
                                        if updated_fields:
                                            existing_lead.save()
                                            update_count += 1
                                            warnings_list.append(f"Row {row_number}: Updated lead {email} - Fields: {', '.join(updated_fields)}")
                                        else:
                                            warnings_list.append(f"Row {row_number}: No changes for lead {email} (already up to date)")
                                    else:
                                        raise ValueError(f"Lead with email {email} already exists (Overwrite is OFF)")
                                else:
                                    # Create new lead
                                    Lead.objects.create(**lead_data)
                                    success_count += 1

                            except Exception as e:
                                error_count += 1
                                errors_list.append({
                                    'row_number': row_number,
                                    'error_message': str(e),
                                    'row_data': original_row_data,
                                    'email': email if 'email' in locals() else 'N/A'
                                })

                        # If too many errors, rollback
                        if error_count > len(df) * 0.5:  # More than 50% errors
                            raise ValueError(f"Too many errors ({error_count}/{len(df)} rows). Upload cancelled.")

                except Exception as transaction_error:
                    messages.error(request, f"❌ Upload failed and rolled back. {error_count} row(s) had errors.")
                    if errors_list:
                        request.session['upload_errors'] = errors_list
                        error_report_url = reverse('leads:download_upload_errors')
                        messages.warning(request, f'⚠️ <a href="{error_report_url}" class="alert-link">Download error report</a>', extra_tags='safe')
                    return render(request, 'leads/upload_leads.html', {'form': form})

                # --- 5. Final Results Summary ---
                result_messages = []
                
                if success_count > 0:
                    result_messages.append(f"✅ {success_count} new leads created")
                
                if update_count > 0:
                    result_messages.append(f"🔄 {update_count} existing leads updated")
                
                if error_count > 0:
                    result_messages.append(f"❌ {error_count} rows failed")
                    request.session['upload_errors'] = errors_list
                    error_report_url = reverse('leads:download_upload_errors')
                    result_messages.append(f'📄 <a href="{error_report_url}" class="alert-link">Download error report</a>')

                if warnings_list:
                    # Store warnings in session for detailed view
                    request.session['upload_warnings'] = warnings_list[:50]  # Limit to 50 warnings

                if result_messages:
                    final_message = " | ".join(result_messages)
                    messages.success(request, final_message, extra_tags='safe')

                # If no records processed at all
                if success_count == 0 and update_count == 0 and error_count == 0:
                    messages.info(request, "ℹ️ No leads were processed. Please check your file format and data.")

                return redirect('leads:leads_list')

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Upload Error: {error_details}")
                messages.error(request, f"❌ Unexpected error processing file: {str(e)}")
                return render(request, 'leads/upload_leads.html', {'form': form})

    else:
        form = LeadsUploadForm()

    return render(request, 'leads/upload_leads.html', {
        'form': form,
        'supported_columns': [
            'Professional Email', 'First Name', 'Last Name', 'Full Name', 'Job Title',
            'Company Name', 'Industry', 'Employees', 'Revenue', 'Person Country', 
            'Company Country', 'Company Website', 'Person LinkedIn Url', 'Company LinkedIn Url'
        ]
    })


@login_required
def leads_list(request):
    
    try:
        from .utils import EMPLOYEE_RANGES, REVENUE_RANGES, check_range_overlap, parse_range_to_tuple
    except ImportError:
        messages.error(request, "CRITICAL ERROR: leads/utils.py file is missing or broken. Range filters will not work.")
        return render(request, 'leads/leads_list.html', {'form': LeadFilterForm()})

    leads_queryset = Lead.objects.all() 
    
    try:
        filter_choices = generate_filters(request)
    except Exception as e:
        print(f"Error in generate_filters: {e}")
        filter_choices = {
            'JOB_TITLE_CHOICES': [('', 'All Job Titles')],
            'INDUSTRY_CHOICES': [('', 'All Industries')],
            'PERSON_COUNTRY_CHOICES': [('', 'All Person Countries')],
            'COMPANY_COUNTRY_CHOICES': [('', 'All Company Countries')],
        }
    
    form = LeadFilterForm(
        request.GET or None, 
        EMPLOYEES_CHOICES=EMPLOYEE_RANGES,
        JOB_TITLE_CHOICES=filter_choices.get('JOB_TITLE_CHOICES', []),
        INDUSTRY_CHOICES=filter_choices.get('INDUSTRY_CHOICES', []),
        PERSON_COUNTRY_CHOICES=filter_choices.get('PERSON_COUNTRY_CHOICES', []),
        COMPANY_COUNTRY_CHOICES=filter_choices.get('COMPANY_COUNTRY_CHOICES', [])
    )

    if form.is_valid():
        
        # --- REFACTORED: Sequential Filtering (Clean & Robust) ---

        # 1. Company Name (Contains - flexible)
        company_str = form.cleaned_data.get('company_name')
        if company_str:
            companies = [name.strip() for name in company_str.split(',') if name.strip()]
            if companies:
                company_query = Q()
                for name in companies:
                    company_query |= Q(company_name__icontains=name)
                leads_queryset = leads_queryset.filter(company_query)

        # 2. General Search (Contains - flexible)
        search = form.cleaned_data.get('search')
        if search:
            search_query = (
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(professional_email__icontains=search) |
                Q(personal_email__icontains=search) |
                Q(company_name__icontains=search) |
                Q(job_title__icontains=search) |
                Q(industry__icontains=search)
            )
            leads_queryset = leads_queryset.filter(search_query)

        # 3. Job Title (ROBUST FIX: __icontains)
        job_titles = form.cleaned_data.get('job_title')
        if job_titles:
            title_query = Q()
            for title in job_titles:
                title_query |= Q(job_title__icontains=title) 
            leads_queryset = leads_queryset.filter(title_query)

        # 4. Industry (ROBUST FIX: __icontains)
        industries = form.cleaned_data.get('industry')
        if industries:
            industry_query = Q()
            for ind in industries:
                industry_query |= Q(industry__icontains=ind)
            leads_queryset = leads_queryset.filter(industry_query)

        # 5. Person Country (ROBUST FIX: __icontains)
        person_countries = form.cleaned_data.get('person_country')
        if person_countries:
            p_country_query = Q()
            for c in person_countries:
                p_country_query |= Q(person_country__icontains=c)
            leads_queryset = leads_queryset.filter(p_country_query)

        # 6. Company Country (ROBUST FIX: __icontains)
        company_countries = form.cleaned_data.get('company_country')
        if company_countries:
            c_country_query = Q()
            for c in company_countries:
                c_country_query |= Q(company_country__icontains=c)
            leads_queryset = leads_queryset.filter(c_country_query)
        
        # --- Python-based filters (Range) ---

        # 7. Employee Range Filter 
        employees_filters_dropdown = form.cleaned_data.get('employees_dropdown', [])
        employees_filter_text = form.cleaned_data.get('employees_text')
        
        all_employee_ranges = list(employees_filters_dropdown)
        if employees_filter_text:
            all_employee_ranges.append(employees_filter_text.strip())

        if all_employee_ranges:
            try:
                employee_filtered_ids = []
                for lead in leads_queryset: 
                    for filter_range in all_employee_ranges:
                        if check_range_overlap(filter_range_str=filter_range, db_value_str=lead.employees):
                            employee_filtered_ids.append(lead.id)
                            break 
                
                if employee_filtered_ids:
                    leads_queryset = leads_queryset.filter(id__in=employee_filtered_ids)
            except Exception as e:
                messages.error(request, f"⚠️ Error in 'Employees' filter. Check values. {e}")

        # 8. Revenue Range Filter
        revenue_text = form.cleaned_data.get('revenue')
        if revenue_text:
            try:
                revenue_filters = [r.strip() for r in revenue_text.split(',') if r.strip()]
                revenue_filtered_ids = []
                for lead in leads_queryset:
                    for filter_range in revenue_filters:
                         if check_range_overlap(filter_range_str=filter_range, db_value_str=lead.revenue):
                            revenue_filtered_ids.append(lead.id)
                            break

                if revenue_filtered_ids:
                    leads_queryset = leads_queryset.filter(id__in=revenue_filtered_ids)
            except Exception as e:
                messages.error(request, f"⚠️ Error in 'Revenue' filter. Check values. {e}")
        
    paginator = Paginator(leads_queryset.order_by('-created_at'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'leads/leads_list.html', {
        'leads': page_obj, 
        'form': form,
        'page_obj': page_obj, 
        'filter_choices': filter_choices
    })


@login_required
def export_leads(request):
    
    # Yeh function leads_list ke jaisa hi hai, bas pagination nahi hai
    
    try:
        from .utils import EMPLOYEE_RANGES, REVENUE_RANGES, check_range_overlap, parse_range_to_tuple
    except ImportError:
        messages.error(request, "Could not export: leads/utils.py file is missing.")
        return redirect('leads:leads_list')

    leads_queryset = Lead.objects.all()
    
    try:
        filter_choices = generate_filters(request)
    except Exception as e:
        filter_choices = {
            'JOB_TITLE_CHOICES': [('', 'All Job Titles')],
            'INDUSTRY_CHOICES': [('', 'All Industries')],
            'PERSON_COUNTRY_CHOICES': [('', 'All Person Countries')],
            'COMPANY_COUNTRY_CHOICES': [('', 'All Company Countries')],
        }
    
    form = LeadFilterForm(
        request.GET or None, 
        EMPLOYEES_CHOICES=EMPLOYEE_RANGES,
        JOB_TITLE_CHOICES=filter_choices.get('JOB_TITLE_CHOICES', []),
        INDUSTRY_CHOICES=filter_choices.get('INDUSTRY_CHOICES', []),
        PERSON_COUNTRY_CHOICES=filter_choices.get('PERSON_COUNTRY_CHOICES', []),
        COMPANY_COUNTRY_CHOICES=filter_choices.get('COMPANY_COUNTRY_CHOICES', [])
    )

    # Same robust filter logic as leads_list
    if form.is_valid():
        company_str = form.cleaned_data.get('company_name')
        if company_str:
            companies = [name.strip() for name in company_str.split(',') if name.strip()]
            if companies:
                company_query = Q()
                for name in companies:
                    company_query |= Q(company_name__icontains=name)
                leads_queryset = leads_queryset.filter(company_query)
        
        search = form.cleaned_data.get('search')
        if search:
            search_query = (
                Q(first_name__icontains=search) | Q(last_name__icontains=search) |
                Q(professional_email__icontains=search) | Q(personal_email__icontains=search) |
                Q(company_name__icontains=search) | Q(job_title__icontains=search) |
                Q(industry__icontains=search)
            )
            leads_queryset = leads_queryset.filter(search_query)
        
        job_titles = form.cleaned_data.get('job_title')
        if job_titles:
            title_query = Q()
            for title in job_titles:
                title_query |= Q(job_title__icontains=title)
            leads_queryset = leads_queryset.filter(title_query)

        industries = form.cleaned_data.get('industry')
        if industries:
            industry_query = Q()
            for ind in industries:
                industry_query |= Q(industry__icontains=ind)
            leads_queryset = leads_queryset.filter(industry_query)

        person_countries = form.cleaned_data.get('person_country')
        if person_countries:
            p_country_query = Q()
            for c in person_countries:
                p_country_query |= Q(person_country__icontains=c)
            leads_queryset = leads_queryset.filter(p_country_query)

        company_countries = form.cleaned_data.get('company_country')
        if company_countries:
            c_country_query = Q()
            for c in company_countries:
                c_country_query |= Q(company_country__icontains=c)
            leads_queryset = leads_queryset.filter(c_country_query)
            
        # Employee filter
        employees_filters_dropdown = form.cleaned_data.get('employees_dropdown', [])
        employees_filter_text = form.cleaned_data.get('employees_text')
        all_employee_ranges = list(employees_filters_dropdown)
        if employees_filter_text:
            all_employee_ranges.append(employees_filter_text.strip())

        if all_employee_ranges:
            try:
                employee_filtered_ids = []
                for lead in leads_queryset:
                    for filter_range in all_employee_ranges:
                        if check_range_overlap(filter_range_str=filter_range, db_value_str=lead.employees):
                            employee_filtered_ids.append(lead.id)
                            break
                if employee_filtered_ids:
                    leads_queryset = leads_queryset.filter(id__in=employee_filtered_ids)
            except:
                 pass 

        # Revenue filter
        revenue_text = form.cleaned_data.get('revenue')
        if revenue_text:
            try:
                revenue_filters = [r.strip() for r in revenue_text.split(',') if r.strip()]
                revenue_filtered_ids = []
                for lead in leads_queryset:
                    for filter_range in revenue_filters:
                        if check_range_overlap(filter_range_str=filter_range, db_value_str=lead.revenue):
                            revenue_filtered_ids.append(lead.id)
                            break
                if revenue_filtered_ids:
                    leads_queryset = leads_queryset.filter(id__in=revenue_filtered_ids)
            except:
                 pass 

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="filtered_leads.csv"'

    writer = csv.writer(response)
    field_names = [
         'lead_id', 'full_name', 'first_name', 'last_name', 'job_title',
        'professional_email', 'email_status', 'personal_email', 'person_linkedin_url',
        'person_city', 'person_state', 'person_country', 'person_direct_phone',
        'company_id', 'company_name', 'company_website', 'industry', 'employees',
        'revenue', 'generic_email', 'full_address', 'first_address', 'company_city',
        'company_state', 'zip_code', 'company_country', 'company_linkedin_url',
        'company_phone', 'comments', 'source'
    ]
    writer.writerow(field_names) 

    for lead in leads_queryset:
        writer.writerow([getattr(lead, field, '') for field in field_names])

    return response


@login_required
def download_sample_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leads_sample.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Lead ID', 'Full Name', 'First Name', 'Last Name', 'Job Title',
        'Professional Email', 'Email Status', 'Personal Email', 'Person Linkedin Url',
        'Person City', 'Person State', 'Person Country', 'Person Direct Phone Number',
        'Company ID', 'Company Name', 'Company Website', 'Industry', 'Employees', 'Revenue',
        'Generic Email', 'Full Address', 'First Address', 'Company City', 'Company State',
        'Zip code', 'Company Country', 'Company Linkedin Url', 'Company Phone Numbers', 'Comments'
    ])
    writer.writerow([
        'L001', 'John Sample', 'John', 'Sample', 'Developer',
        'john.sample@example.com', 'Verified', 'john.personal@mail.com', 'https://linkedin.com/in/johnsample',
        'Sample City', 'CA', 'USA', '555-1234',
        'C001', 'Sample Inc', 'https://sample.com', 'Tech', '50-100', '$1M',
        'contact@sample.com', '123 Sample St, Sample City, CA 90210', '123 Sample St', 'Sample City', 'CA',
        '90210', 'USA', 'https.linkedin.com/company/sampleinc', '555-5678', 'Sample comment'
    ])

    return response


@login_required
def get_lead_detail_json(request, pk):
    try:
        lead = Lead.objects.get(pk=pk)
        lead_data = model_to_dict(lead)

        lead_data['created_at'] = lead.created_at.strftime('%b %d, %Y, %I:%M %p %Z') if lead.created_at else None
        lead_data['updated_at'] = lead.updated_at.strftime('%b %d, %Y, %I:%M %p %Z') if lead.updated_at else None
        lead_data['created_by'] = lead.created_by.username if lead.created_by else 'N/A'

        return JsonResponse({'status': 'success', 'lead': lead_data})

    except Lead.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Lead not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def export_selected_leads(request):
    ids_str = request.GET.get('ids', None)

    if not ids_str:
        messages.error(request, "No leads selected for export.")
        return redirect('leads:leads_list')

    try:
        selected_ids = [int(id) for id in ids_str.split(',')]
        leads_queryset = Lead.objects.filter(id__in=selected_ids)

        if not leads_queryset.exists():
            messages.error(request, "No valid leads found for the selected IDs.")
            return redirect('leads:leads_list')

        columns = [
            'lead_id', 'full_name', 'first_name', 'last_name', 'job_title',
            'professional_email', 'email_status', 'personal_email', 'person_linkedin_url',
            'person_city', 'person_state', 'person_country', 'person_direct_phone',
            'company_id', 'company_name', 'company_website', 'industry', 'employees',
            'revenue', 'generic_email', 'full_address', 'first_address', 'company_city',
            'company_state', 'zip_code', 'company_country', 'company_linkedin_url',
            'company_phone', 'comments', 'source', 'created_at', 'created_by'
        ]

        leads_data = list(leads_queryset.values(*columns, username=F('created_by__username'))) 

        df = pd.DataFrame(leads_data)

        if 'username' in df.columns:
             df.rename(columns={'username': 'created_by'}, inplace=True)

        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)

        df.rename(columns={
            'professional_email': 'Email',
            'person_linkedin_url': 'LinkedIn (Person)',
            'company_linkedin_url': 'LinkedIn (Company)',
            'created_at': 'Date Added',
            'created_by': 'Added By',
            'person_direct_phone': 'Direct Phone',
            'company_phone': 'Company Phone'
        }, inplace=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Selected Leads')
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="selected_leads.xlsx"'

        return response

    except Exception as e:
        messages.error(request, f"Error exporting selected leads: {e}")
        import traceback
        print(traceback.format_exc()) 
        return redirect('leads:leads_list')


@login_required
def download_upload_errors(request):
    upload_errors = request.session.get('upload_errors', None)

    if not upload_errors:
        messages.error(request, "No error report found for the previous upload.")
        return redirect('leads:upload_leads') 

    try:
        # Create detailed error report
        error_data_for_df = []
        
        # Get all unique headers from error data
        headers_set = set()
        for error_info in upload_errors:
            headers_set.update(error_info['row_data'].keys())
        
        headers = ['Row Number', 'Error Message', 'Email'] + sorted(headers_set)

        for error_info in upload_errors:
            row_entry = {
                'Row Number': error_info['row_number'],
                'Error Message': error_info['error_message'],
                'Email': error_info.get('email', 'N/A')
            }
            
            for header in headers_set:
                row_entry[header] = error_info['row_data'].get(header, '')
            
            error_data_for_df.append(row_entry)

        df = pd.DataFrame(error_data_for_df)
        df = df.reindex(columns=headers, fill_value='')

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Upload Errors')
            
            # Add summary sheet
            summary_data = {
                'Metric': ['Total Errors', 'Successful Rows', 'Failed Rows'],
                'Count': [len(upload_errors), 'N/A', len(upload_errors)]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, index=False, sheet_name='Summary')

        output.seek(0)

        # Clear session data
        del request.session['upload_errors']

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="upload_errors_detailed.xlsx"'

        return response

    except Exception as e:
        messages.error(request, f"Could not generate error report: {e}")
        import traceback
        print(traceback.format_exc())
        return redirect('leads:upload_leads')


# Debug view for testing filters
@login_required
def debug_filters(request):
    """Debug view to check filter functionality"""
    
    # Test each filter individually
    test_cases = [
        ('Company Name', Lead.objects.filter(company_name__icontains='Google').count()),
        ('Job Title', Lead.objects.filter(job_title__icontains='CEO').count()),
        ('Industry', Lead.objects.filter(industry__icontains='Tech').count()),
        ('Person Country', Lead.objects.filter(person_country__icontains='USA').count()),
        ('Company Country', Lead.objects.filter(company_country__icontains='USA').count()),
    ]
    
    context = {
        'test_cases': test_cases,
        'total_leads': Lead.objects.count(),
    }
    
    return render(request, 'leads/debug_filters.html', context)