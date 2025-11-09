from django.shortcuts import render
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, F, Count # Count ko import karein
from django.contrib.auth.models import Group, User
from .models import Lead
from .forms import LeadFilterForm, LeadsUploadForm
from accounts import models
from generate_lead_filters import generate_filters
import csv
import io
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
    is_manager = request.user.groups.filter(name='Managers').exists()
    if not (request.user.is_superuser or is_manager):
        messages.error(request, "You do not have permission to upload leads.")
        return redirect('leads:leads_list')

    # Session se purane errors clear karein (agar maujood hain)
    if 'upload_errors' in request.session:
        del request.session['upload_errors']

    if request.method == 'POST':
        form = LeadsUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            overwrite = form.cleaned_data['overwrite']
            
            try:
                if file.name.endswith('.csv'):
                    # Force string data type for all columns to avoid type inference issues
                    df = pd.read_csv(file, dtype=str, keep_default_na=False)
                else:
                    df = pd.read_excel(file, dtype=str, keep_default_na=False)

                # Replace empty strings potentially read as NaN back to empty strings
                df.fillna('', inplace=True)

                COLUMN_MAPPING = {
                    # ... (Keep your existing COLUMN_MAPPING) ...
                    'Full Name': 'full_name', 'First Name': 'first_name', 'Last Name': 'last_name',
                    'Job Title': 'job_title', 'Professional Email': 'professional_email', 'Email': 'professional_email',
                    'Email Status': 'email_status', 'Personal Email': 'personal_email',
                    'Person Linkedin Url': 'person_linkedin_url', 'Linkedin Url': 'person_linkedin_url',
                    'Person City': 'person_city', 'Person State': 'person_state', 'Person Country': 'person_country',
                    'Person Direct Phone Number': 'person_direct_phone', 'Phone': 'person_direct_phone',
                    'Lead ID': 'lead_id', 'Company ID': 'company_id', 'Company Name': 'company_name',
                    'Company Website': 'company_website', 'Website': 'company_website', 'Industry': 'industry',
                    'Employees': 'employees', 'Generic Email': 'generic_email', 'Full Address': 'full_address',
                    'First Address': 'first_address', 'Company City': 'company_city', 'Company State': 'company_state',
                    'Zip code': 'zip_code', 'Company Country': 'company_country',
                    'Company Linkedin Url': 'company_linkedin_url', 'Company Phone Numbers': 'company_phone',
                    'Company Phone': 'company_phone', 'Comment': 'comments', 'Comments': 'comments',
                    'Revenue': 'revenue',
                }

                column_map = {}
                processed_columns = set() # Track mapped model fields
                original_df_columns = list(df.columns) # Original file headers

                for col in original_df_columns:
                    col_clean = col.strip()
                    mapped_field = None
                    if col_clean in COLUMN_MAPPING:
                        mapped_field = COLUMN_MAPPING[col_clean]
                    else:
                        for key in COLUMN_MAPPING:
                            if key.lower() == col_clean.lower():
                                mapped_field = COLUMN_MAPPING[key]
                                break
                    if mapped_field:
                         # Handle cases where multiple source columns map to the same target
                        if mapped_field not in processed_columns:
                            column_map[col] = mapped_field
                            processed_columns.add(mapped_field)
                        else:
                             # If target field already mapped, ignore this column
                            print(f"Ignoring duplicate mapping for '{mapped_field}' from column '{col}'")


                success_count = 0
                error_count = 0
                errors_list = [] # List to store detailed errors

                # Use transaction.atomic to ensure all-or-nothing save
                try:
                    with transaction.atomic():
                        for index, row in df.iterrows():
                            # Original row data as dictionary
                            original_row_data = row.to_dict()

                            try:
                                lead_data = {
                                    'source': f'Uploaded File: {file.name}',
                                    'created_by': request.user
                                }
                                missing_required = []

                                for original_col, model_field in column_map.items():
                                    value = original_row_data.get(original_col, '')
                                    # Ensure value is treated as string and stripped
                                    value = str(value).strip() if value not in [None, ''] else ''
                                    lead_data[model_field] = value

                                # *** Simple Validations (Add more as needed) ***
                                email = lead_data.get('professional_email', '')
                                if not email:
                                    missing_required.append('Professional Email')
                                
                                # First/Last Name logic
                                f_name = lead_data.get('first_name', '')
                                l_name = lead_data.get('last_name', '')
                                full_name = lead_data.get('full_name', '')

                                if not f_name and not l_name:
                                    if full_name:
                                        parts = full_name.split(' ', 1)
                                        lead_data['first_name'] = parts[0]
                                        if len(parts) > 1:
                                            lead_data['last_name'] = parts[1]
                                        else:
                                            lead_data['last_name'] = ' ' 
                                    else:
                                        missing_required.append('First Name/Last Name or Full Name')
                                elif not f_name:
                                    lead_data['first_name'] = ' '
                                elif not l_name:
                                    lead_data['last_name'] = ' '


                                if missing_required:
                                     raise ValueError(f"Required field(s) missing: {', '.join(missing_required)}")

                                # *** End Validations ***

                                existing_lead = Lead.objects.filter(professional_email=email).first()

                                if existing_lead:
                                    if overwrite:
                                        # Update existing lead
                                        for key, value in lead_data.items():
                                            if key != 'created_by': # Preserve original creator
                                                 # Don't overwrite existing values with empty strings unless intended
                                                if value != '' or getattr(existing_lead, key) is None:
                                                    setattr(existing_lead, key, value)
                                        existing_lead.save()
                                        success_count += 1
                                    else:
                                        # Skip duplicate if overwrite is off
                                        raise ValueError("Lead with this Professional Email already exists (Overwrite is OFF).")
                                else:
                                    # Create new lead
                                    Lead.objects.create(**lead_data)
                                    success_count += 1

                            except Exception as e:
                                error_count += 1
                                # Store detailed error info
                                errors_list.append({
                                    'row_number': index + 2, # Excel row number
                                    'error_message': str(e),
                                    'row_data': original_row_data # Store original row data
                                })
                                # Don't re-raise here to process all rows

                        # If any row failed, raise an exception to rollback the transaction
                        if errors_list:
                            raise ValueError(f"{len(errors_list)} row(s) had errors during processing.")

                except Exception as transaction_error:
                    # Transaction was rolled back
                    messages.error(request, f"❌ Upload failed and rolled back. {len(errors_list)} row(s) had errors.")
                    # Store errors in session even after rollback for download
                    request.session['upload_errors'] = errors_list
                    error_report_url = reverse('leads:download_upload_errors')
                    messages.warning(request, f'⚠️ <a href="{error_report_url}" class="alert-link">Click here to download the error report</a>.', extra_tags='safe') # Use safe tag carefully
                    return render(request, 'leads/upload_leads.html', {'form': form})


                # --- Messages after successful processing (outside transaction block) ---
                if success_count > 0:
                    messages.success(request, f"✅ Successfully processed {success_count} leads.")
                
                if not errors_list and success_count == 0:
                     messages.info(request, "ℹ️ No leads were processed or saved (file might be empty or all rows skipped).")


                return redirect('leads:leads_list')

            except Exception as e:
                # Catch errors during file reading or initial processing
                import traceback
                print(traceback.format_exc()) # Print detailed traceback to console
                messages.error(request, f"❌ Error processing file: {str(e)}")
                return render(request, 'leads/upload_leads.html', {'form': form})

    else: # GET request
        form = LeadsUploadForm()

    return render(request, 'leads/upload_leads.html', {'form': form})

@login_required
def leads_list(request):
    
    # utils.py se import check karein
    try:
        from .utils import EMPLOYEE_RANGES, REVENUE_RANGES, check_range_overlap, parse_range_to_tuple
    except ImportError:
        messages.error(request, "CRITICAL ERROR: leads/utils.py file is missing or broken. Range filters will not work.")
        # Khali form ke saath render karein taaki page poora crash na ho
        return render(request, 'leads/leads_list.html', {'form': LeadFilterForm(EMPLOYEES_CHOICES=[], JOB_TITLE_CHOICES=[], INDUSTRY_CHOICES=[], PERSON_COUNTRY_CHOICES=[], COMPANY_COUNTRY_CHOICES=[])})

    leads_queryset = Lead.objects.all() 
    filter_choices = generate_filters(request)
    
    employee_range_choices = EMPLOYEE_RANGES 
    # revenue_range_choices = REVENUE_RANGES # Iski ab zaroorat nahi

    # --- YAHAN SE 'REVENUE_CHOICES' HATA DIYA GAYA HAI ---
    form = LeadFilterForm(
        request.GET or None, 
        EMPLOYEES_CHOICES=employee_range_choices,
        JOB_TITLE_CHOICES=filter_choices.get('JOB_TITLE_CHOICES', []),
        INDUSTRY_CHOICES=filter_choices.get('INDUSTRY_CHOICES', []),
        PERSON_COUNTRY_CHOICES=filter_choices.get('PERSON_COUNTRY_CHOICES', []),
        COMPANY_COUNTRY_CHOICES=filter_choices.get('COMPANY_COUNTRY_CHOICES', [])
    )

    if form.is_valid():
        
        query = Q()

        # 1. Company Name (Multiple - Text, Comma-separated)
        company_str = form.cleaned_data.get('company_name')
        if company_str:
            companies = [name.strip() for name in company_str.split(',') if name.strip()]
            company_query = Q()
            for name in companies:
                company_query |= Q(company_name__icontains=name)
            query &= company_query

        # 2. General Search (Text)
        search = form.cleaned_data.get('search')
        if search:
            query &= (
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(professional_email__icontains=search) |
                Q(personal_email__icontains=search) |
                Q(company_name__icontains=search)
            )

        # 3. Job Title (Multiple - Select)
        job_titles = form.cleaned_data.get('job_title')
        if job_titles:
            title_query = Q()
            for title in job_titles:
                title_query |= Q(job_title__iexact=title) # Exact match (case-insensitive)
            query &= title_query

        # 4. Industry (Multiple - Select)
        industries = form.cleaned_data.get('industry')
        if industries:
            industry_query = Q()
            for ind in industries:
                industry_query |= Q(industry__icontains=ind) # Contains (case-insensitive)
            query &= industry_query

        # 5. Person Country (Multiple - Select)
        person_countries = form.cleaned_data.get('person_country')
        if person_countries:
            p_country_query = Q()
            for c in person_countries:
                p_country_query |= Q(person_country__iexact=c) # Exact match
            query &= p_country_query

        # 6. Company Country (Multiple - Select)
        company_countries = form.cleaned_data.get('company_country')
        if company_countries:
            c_country_query = Q()
            for c in company_countries:
                c_country_query |= Q(company_country__iexact=c) # Exact match
            query &= c_country_query
        
        leads_queryset = leads_queryset.filter(query)

        # 7. Employee Range Filter (Dropdown + Text)
        employees_filters_dropdown = form.cleaned_data.get('employees_dropdown', [])
        employees_filter_text = form.cleaned_data.get('employees_text')
        
        all_employee_ranges = list(employees_filters_dropdown)
        if employees_filter_text:
            all_employee_ranges.append(employees_filter_text.strip())

        if all_employee_ranges:
            try:
                filtered_leads_ids = []
                for lead in leads_queryset: 
                    for filter_range in all_employee_ranges:
                        if check_range_overlap(filter_range_str=filter_range, db_value_str=lead.employees):
                            filtered_leads_ids.append(lead.id)
                            break 
                
                leads_queryset = leads_queryset.filter(id__in=filtered_leads_ids)
            except Exception as e:
                messages.error(request, f"⚠️ Error in 'Employees' filter. Check values. {e}")

        # 8. Revenue Range Filter (Text input)
        revenue_text = form.cleaned_data.get('revenue')
        if revenue_text:
            try:
                revenue_filters = [r.strip() for r in revenue_text.split(',') if r.strip()]
                filtered_leads_ids = []
                for lead in leads_queryset:
                    for filter_range in revenue_filters:
                         if check_range_overlap(filter_range_str=filter_range, db_value_str=lead.revenue):
                            filtered_leads_ids.append(lead.id)
                            break

                leads_queryset = leads_queryset.filter(id__in=filtered_leads_ids)
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
    
    try:
        from .utils import EMPLOYEE_RANGES, REVENUE_RANGES, check_range_overlap, parse_range_to_tuple
    except ImportError:
        messages.error(request, "Could not export: leads/utils.py file is missing.")
        return redirect('leads:leads_list')

    leads_queryset = Lead.objects.all()
    filter_choices = generate_filters(request)
    
    employee_range_choices = EMPLOYEE_RANGES 
    # revenue_range_choices = REVENUE_RANGES # Iski ab zaroorat nahi

    # --- YAHAN SE BHI 'REVENUE_CHOICES' HATA DIYA GAYA HAI ---
    form = LeadFilterForm(
        request.GET or None, 
        EMPLOYEES_CHOICES=employee_range_choices,
        JOB_TITLE_CHOICES=filter_choices.get('JOB_TITLE_CHOICES', []),
        INDUSTRY_CHOICES=filter_choices.get('INDUSTRY_CHOICES', []),
        PERSON_COUNTRY_CHOICES=filter_choices.get('PERSON_COUNTRY_CHOICES', []),
        COMPANY_COUNTRY_CHOICES=filter_choices.get('COMPANY_COUNTRY_CHOICES', [])
    )

    if form.is_valid():
        query = Q()

        company_str = form.cleaned_data.get('company_name')
        if company_str:
            companies = [name.strip() for name in company_str.split(',') if name.strip()]
            company_query = Q()
            for name in companies:
                company_query |= Q(company_name__icontains=name)
            query &= company_query
        
        search = form.cleaned_data.get('search')
        if search:
            query &= (
                Q(first_name__icontains=search) | Q(last_name__icontains=search) |
                Q(professional_email__icontains=search) | Q(personal_email__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        job_titles = form.cleaned_data.get('job_title')
        if job_titles:
            title_query = Q()
            for title in job_titles:
                title_query |= Q(job_title__iexact=title)
            query &= title_query

        industries = form.cleaned_data.get('industry')
        if industries:
            industry_query = Q()
            for ind in industries:
                industry_query |= Q(industry__icontains=ind)
            query &= industry_query

        person_countries = form.cleaned_data.get('person_country')
        if person_countries:
            p_country_query = Q()
            for c in person_countries:
                p_country_query |= Q(person_country__iexact=c)
            query &= p_country_query

        company_countries = form.cleaned_data.get('company_country')
        if company_countries:
            c_country_query = Q()
            for c in company_countries:
                c_country_query |= Q(company_country__iexact=c)
            query &= c_country_query
            
        leads_queryset = leads_queryset.filter(query)
        
        employees_filters_dropdown = form.cleaned_data.get('employees_dropdown', [])
        employees_filter_text = form.cleaned_data.get('employees_text')
        all_employee_ranges = list(employees_filters_dropdown)
        if employees_filter_text:
            all_employee_ranges.append(employees_filter_text.strip())

        if all_employee_ranges:
            try:
                filtered_ids = []
                for lead in leads_queryset:
                    for filter_range in all_employee_ranges:
                        if check_range_overlap(filter_range_str=filter_range, db_value_str=lead.employees):
                            filtered_ids.append(lead.id)
                            break
                leads_queryset = leads_queryset.filter(id__in=filtered_ids)
            except:
                 pass 

        revenue_text = form.cleaned_data.get('revenue')
        if revenue_text:
            try:
                revenue_filters = [r.strip() for r in revenue_text.split(',') if r.strip()]
                filtered_ids = []
                for lead in leads_queryset:
                    for filter_range in revenue_filters:
                        if check_range_overlap(filter_range_str=filter_range, db_value_str=lead.revenue):
                            filtered_ids.append(lead.id)
                            break
                leads_queryset = leads_queryset.filter(id__in=filtered_ids)
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
        '90210', 'USA', 'https://linkedin.com/company/sampleinc', '555-5678', 'Sample comment'
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
        error_data_for_df = []
        headers = list(upload_errors[0]['row_data'].keys()) if upload_errors else []

        for error_info in upload_errors:
            row_entry = {'Row Number': error_info['row_number'], 'Error Message': error_info['error_message']}
            for header in headers:
                row_entry[header] = error_info['row_data'].get(header, '')
            error_data_for_df.append(row_entry)

        column_order = ['Row Number', 'Error Message'] + headers

        df = pd.DataFrame(error_data_for_df)
        df = df.reindex(columns=column_order, fill_value='')


        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Upload Errors')
        output.seek(0)

        del request.session['upload_errors']

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="upload_errors.xlsx"'

        return response

    except Exception as e:
        messages.error(request, f"Could not generate error report: {e}")
        import traceback
        print(traceback.format_exc()) 
        if 'upload_errors' in request.session:
            del request.session['upload_errors']
        return redirect('leads:upload_leads')