from django.shortcuts import render
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse # JsonResponse add hua
from django.db.models import Q, F
from django.contrib.auth.models import Group, User # User add hua
from .models import Lead
from .forms import LeadFilterForm, LeadsUploadForm
from accounts import models # Yeh import abhi use nahi ho raha, par rakh sakte hain
from generate_lead_filters import generate_filters
import csv
import io # Yeh naya import hai
from django.forms.models import model_to_dict # Yeh naya import hai
from django.urls import reverse # Error report URL ke liye naya import
from django.db import transaction # Transaction ke liye naya import

# --- NAYE IMPORTS ---
# Apne naye utils.py file se functions ko import karein
# Agar utils.py file aapke project mein hai, toh ise uncomment karein
# from .utils import EMPLOYEE_RANGES, check_range_overlap


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
                    # Force string data type for all columns
                    df = pd.read_csv(file, dtype=str, keep_default_na=False)
                else:
                    df = pd.read_excel(file, dtype=str, keep_default_na=False)

                # Replace any potential None/NaN back to empty strings
                df.fillna('', inplace=True)

                COLUMN_MAPPING = {
                    # Person/Contact Info
                    'Full Name': 'full_name', 'First Name': 'first_name', 'Last Name': 'last_name',
                    'Job Title': 'job_title', 'Professional Email': 'professional_email', 'Email': 'professional_email',
                    'Email Status': 'email_status', 'Personal Email': 'personal_email',
                    'Person Linkedin Url': 'person_linkedin_url', 'Linkedin Url': 'person_linkedin_url',
                    'Person City': 'person_city', 'Person State': 'person_state', 'Person Country': 'person_country',
                    'Person Direct Phone Number': 'person_direct_phone', 'Phone': 'person_direct_phone',
                    # Company Info
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
                processed_columns = set()
                original_df_columns = list(df.columns)

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
                        if mapped_field not in processed_columns:
                            column_map[col] = mapped_field
                            processed_columns.add(mapped_field)
                        else:
                            print(f"Ignoring duplicate mapping for '{mapped_field}' from column '{col}'")

                success_count = 0
                error_count = 0
                errors_list = [] # List to store detailed errors

                try:
                    with transaction.atomic(): # Start transaction
                        for index, row in df.iterrows():
                            original_row_data = row.to_dict()

                            try:
                                lead_data = {
                                    'source': f'Uploaded File: {file.name}',
                                    'created_by': request.user
                                }
                                missing_required = []

                                for original_col, model_field in column_map.items():
                                    value = original_row_data.get(original_col, '')
                                    value = str(value).strip() if value not in [None, ''] else ''
                                    lead_data[model_field] = value

                                # *** Simple Validations ***
                                email = lead_data.get('professional_email', '')
                                if not email:
                                    missing_required.append('Professional Email')
                                # Add more required field checks if needed
                                # if not lead_data.get('first_name'): missing_required.append('First Name')

                                if missing_required:
                                    raise ValueError(f"Required field(s) missing: {', '.join(missing_required)}")
                                # *** End Validations ***

                                existing_lead = Lead.objects.filter(professional_email=email).first()

                                if existing_lead:
                                    if overwrite:
                                        for key, value in lead_data.items():
                                            if key != 'created_by':
                                                if value != '' or getattr(existing_lead, key) is None:
                                                    setattr(existing_lead, key, value)
                                        existing_lead.save()
                                        success_count += 1
                                    else:
                                        raise ValueError("Lead with this Professional Email already exists (Overwrite is OFF).")
                                else:
                                    Lead.objects.create(**lead_data)
                                    success_count += 1

                            except Exception as e:
                                error_count += 1
                                errors_list.append({
                                    'row_number': index + 2,
                                    'error_message': str(e),
                                    'row_data': original_row_data
                                })
                                # Don't re-raise here to process all rows

                        # If any row failed after processing all, raise exception to rollback
                        if errors_list:
                             # Use a generic error message for the final rollback trigger
                            raise ValueError(f"{len(errors_list)} row(s) had errors during processing.")


                except Exception as transaction_error:
                    # Transaction was rolled back
                    # The actual errors are already in errors_list
                    messages.error(request, f"❌ Upload failed and rolled back due to errors in {len(errors_list)} row(s). No leads were saved.")
                    request.session['upload_errors'] = errors_list
                    error_report_url = reverse('leads:download_upload_errors')
                    messages.warning(request, f'⚠️ <a href="{error_report_url}" class="alert-link">Click here to download the detailed error report</a>.', extra_tags='safe')
                    return render(request, 'leads/upload_leads.html', {'form': form})


                # --- Messages after successful commit (no errors occurred) ---
                if success_count > 0:
                    messages.success(request, f"✅ Successfully processed and saved {success_count} leads.")
                else:
                    # Should not happen if transaction logic is correct, but as a fallback
                    messages.info(request, "ℹ️ No leads were processed or saved.")


                # Redirect only on complete success
                return redirect('leads:leads_list')

            except Exception as e:
                # Catch errors during file reading or initial setup before transaction
                import traceback
                print(traceback.format_exc()) # Print detailed traceback to console
                messages.error(request, f"❌ Critical error processing file before saving: {str(e)}")
                return render(request, 'leads/upload_leads.html', {'form': form})

    else: # GET request
        form = LeadsUploadForm()

    return render(request, 'leads/upload_leads.html', {'form': form})

@login_required
def leads_list(request):
    leads_queryset = Lead.objects.all() # Start with all leads

    # Fetch filter choices using the imported function
    filter_choices = generate_filters(request)

    # Use EMPLOYEE_RANGES if available from utils.py, otherwise provide default
    try:
        from .utils import EMPLOYEE_RANGES
        employee_range_choices = EMPLOYEE_RANGES
    except ImportError:
        employee_range_choices = [('', 'Any')] # Default if utils or EMPLOYEE_RANGES is missing

    form = LeadFilterForm(request.GET or None, EMPLOYEES_CHOICES=employee_range_choices)

    if form.is_valid():
        company = form.cleaned_data.get('company_name')
        job_title = form.cleaned_data.get('job_title')
        industry = form.cleaned_data.get('industry')
        search = form.cleaned_data.get('search')
        person_country = form.cleaned_data.get('person_country')
        company_country = form.cleaned_data.get('company_country')
        employees = form.cleaned_data.get('employees')
        revenue = form.cleaned_data.get('revenue')

        if company:
            leads_queryset = leads_queryset.filter(company_name__icontains=company)
        if job_title:
            leads_queryset = leads_queryset.filter(job_title__icontains=job_title)
        if industry:
            leads_queryset = leads_queryset.filter(industry__icontains=industry)
        if person_country:
            leads_queryset = leads_queryset.filter(person_country__icontains=person_country)
        if company_country:
            leads_queryset = leads_queryset.filter(company_country__icontains=company_country)
        if revenue:
            leads_queryset = leads_queryset.filter(revenue__icontains=revenue)
        if search:
            leads_queryset = leads_queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(professional_email__icontains=search) |
                Q(personal_email__icontains=search) |
                Q(company_name__icontains=search)
            )

        # Apply employee range filter if utils.py function is available
        if employees:
            try:
                from .utils import check_range_overlap
                filtered_leads_list = []
                for lead in leads_queryset: # Filter the already filtered queryset
                    if check_range_overlap(range_str=employees, db_emp_str=lead.employees):
                        filtered_leads_list.append(lead.id)
                leads_queryset = leads_queryset.filter(id__in=filtered_leads_list)
            except ImportError:
                messages.warning(request, "Employee range filtering is currently unavailable.")


    # Pagination applied to the final filtered queryset
    paginator = Paginator(leads_queryset.order_by('-created_at'), 25) # Add default ordering
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'leads/leads_list.html', {
        'leads': page_obj, # Pass page_obj as 'leads' to template
        'form': form,
        'page_obj': page_obj, # Pass page_obj also for pagination controls
        'filter_choices': filter_choices
    })


@login_required
def export_leads(request):
    """
    Exports ALL currently filtered leads (based on GET parameters) to a CSV file.
    (Note: This exports based on filters applied in the URL, similar to leads_list)
    """
    leads_queryset = Lead.objects.all()

    # --- Re-apply filters based on GET parameters ---
    try:
        from .utils import EMPLOYEE_RANGES
        employee_range_choices = EMPLOYEE_RANGES
    except ImportError:
        employee_range_choices = [('', 'Any')]

    form = LeadFilterForm(request.GET or None, EMPLOYEES_CHOICES=employee_range_choices)

    if form.is_valid(): # Validate the GET params using the form
        company = form.cleaned_data.get('company_name')
        job_title = form.cleaned_data.get('job_title')
        industry = form.cleaned_data.get('industry')
        search = form.cleaned_data.get('search')
        person_country = form.cleaned_data.get('person_country')
        company_country = form.cleaned_data.get('company_country')
        employees = form.cleaned_data.get('employees')
        revenue = form.cleaned_data.get('revenue')

        if company:
            leads_queryset = leads_queryset.filter(company_name__icontains=company)
        if job_title:
            leads_queryset = leads_queryset.filter(job_title__icontains=job_title)
        if industry:
            leads_queryset = leads_queryset.filter(industry__icontains=industry)
        if person_country:
            leads_queryset = leads_queryset.filter(person_country__icontains=person_country)
        if company_country:
            leads_queryset = leads_queryset.filter(company_country__icontains=company_country)
        if revenue:
            leads_queryset = leads_queryset.filter(revenue__icontains=revenue)
        if search:
            leads_queryset = leads_queryset.filter(
                Q(first_name__icontains=search) | Q(last_name__icontains=search) |
                Q(professional_email__icontains=search) | Q(personal_email__icontains=search) |
                Q(company_name__icontains=search)
            )
        if employees:
            try:
                from .utils import check_range_overlap
                filtered_ids = [lead.id for lead in leads_queryset if check_range_overlap(range_str=employees, db_emp_str=lead.employees)]
                leads_queryset = leads_queryset.filter(id__in=filtered_ids)
            except ImportError:
                 pass # Ignore if function not available
    # --- End re-applying filters ---

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="filtered_leads.csv"'

    writer = csv.writer(response)
    # Define fields to export in CSV
    # Match these with your model fields
    field_names = [
         'lead_id', 'full_name', 'first_name', 'last_name', 'job_title',
        'professional_email', 'email_status', 'personal_email', 'person_linkedin_url',
        'person_city', 'person_state', 'person_country', 'person_direct_phone',
        'company_id', 'company_name', 'company_website', 'industry', 'employees',
        'revenue', 'generic_email', 'full_address', 'first_address', 'company_city',
        'company_state', 'zip_code', 'company_country', 'company_linkedin_url',
        'company_phone', 'comments', 'source'
        # Add 'created_by__username' if you want the username instead of ID
    ]
    writer.writerow(field_names) # Write header row

    # Write data rows
    for lead in leads_queryset:
        writer.writerow([getattr(lead, field, '') for field in field_names])

    return response


@login_required
def download_sample_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leads_sample.csv"'

    writer = csv.writer(response)
    # Use column names consistent with COLUMN_MAPPING keys for user clarity
    writer.writerow([
        'Lead ID', 'Full Name', 'First Name', 'Last Name', 'Job Title',
        'Professional Email', 'Email Status', 'Personal Email', 'Person Linkedin Url',
        'Person City', 'Person State', 'Person Country', 'Person Direct Phone Number',
        'Company ID', 'Company Name', 'Company Website', 'Industry', 'Employees', 'Revenue',
        'Generic Email', 'Full Address', 'First Address', 'Company City', 'Company State',
        'Zip code', 'Company Country', 'Company Linkedin Url', 'Company Phone Numbers', 'Comments'
    ])
    # Example Row
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
    """
    Returns details of a single lead as JSON for the Quick View drawer.
    """
    try:
        lead = Lead.objects.get(pk=pk)
        # Convert model instance to dictionary
        lead_data = model_to_dict(lead)

        # Format datetime fields for better readability in JSON/JS
        lead_data['created_at'] = lead.created_at.strftime('%b %d, %Y, %I:%M %p %Z') if lead.created_at else None
        lead_data['updated_at'] = lead.updated_at.strftime('%b %d, %Y, %I:%M %p %Z') if lead.updated_at else None

        # Replace created_by ID with username
        lead_data['created_by'] = lead.created_by.username if lead.created_by else 'N/A'

        return JsonResponse({'status': 'success', 'lead': lead_data})

    except Lead.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Lead not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def export_selected_leads(request):
    """
    Exports selected leads (filtered by ID) to an Excel file.
    """
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

        # Define columns for the Excel export
        columns = [
            'lead_id', 'full_name', 'first_name', 'last_name', 'job_title',
            'professional_email', 'email_status', 'personal_email', 'person_linkedin_url',
            'person_city', 'person_state', 'person_country', 'person_direct_phone',
            'company_id', 'company_name', 'company_website', 'industry', 'employees',
            'revenue', 'generic_email', 'full_address', 'first_address', 'company_city',
            'company_state', 'zip_code', 'company_country', 'company_linkedin_url',
            'company_phone', 'comments', 'source', 'created_at', 'created_by'
            # Add 'updated_at' if needed
        ]

        # Fetch data using values for efficiency
        leads_data = list(leads_queryset.values(*columns, username=F('created_by__username'))) # Fetch username directly

        # Create DataFrame
        df = pd.DataFrame(leads_data)

        # Rename 'username' column fetched via F-expression to 'created_by'
        if 'username' in df.columns:
             df.rename(columns={'username': 'created_by'}, inplace=True)


        # Remove timezone info from datetime columns for Excel compatibility
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)
        # if 'updated_at' in df.columns: # Uncomment if exporting updated_at
        #     df['updated_at'] = pd.to_datetime(df['updated_at']).dt.tz_localize(None)

        # Improve column headers for the Excel file
        df.rename(columns={
            'professional_email': 'Email',
            'person_linkedin_url': 'LinkedIn (Person)',
            'company_linkedin_url': 'LinkedIn (Company)',
            'created_at': 'Date Added',
            'created_by': 'Added By',
            'person_direct_phone': 'Direct Phone',
            'company_phone': 'Company Phone'
            # Add more renames as desired
        }, inplace=True)

        # Generate Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Selected Leads')
        output.seek(0)

        # Prepare HTTP response for file download
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="selected_leads.xlsx"'

        return response

    except Exception as e:
        messages.error(request, f"Error exporting selected leads: {e}")
        import traceback
        print(traceback.format_exc()) # Log detailed error for debugging
        return redirect('leads:leads_list')


# --- YEH FUNCTION ERROR REPORT DOWNLOAD KE LIYE HAI ---
@login_required
def download_upload_errors(request):
    """
    Generates and serves an Excel file containing errors from the last upload attempt.
    """
    upload_errors = request.session.get('upload_errors', None)

    if not upload_errors:
        messages.error(request, "No error report found for the previous upload.")
        return redirect('leads:upload_leads') # Redirect to upload page

    try:
        # Prepare data for DataFrame
        error_data_for_df = []
        # Get headers from the first row's data if available
        headers = list(upload_errors[0]['row_data'].keys()) if upload_errors else []

        for error_info in upload_errors:
            row_entry = {'Row Number': error_info['row_number'], 'Error Message': error_info['error_message']}
            # Add original row data using original headers
            for header in headers:
                row_entry[header] = error_info['row_data'].get(header, '')
            error_data_for_df.append(row_entry)

        # Define column order (Error details first, then original data)
        column_order = ['Row Number', 'Error Message'] + headers

        # Create DataFrame
        df = pd.DataFrame(error_data_for_df)
        # Reorder columns according to defined order, handling potential missing original columns
        df = df.reindex(columns=column_order, fill_value='')


        # Generate Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Upload Errors')
        output.seek(0)

        # Clean up session data *after* successfully preparing the file
        del request.session['upload_errors']

        # Prepare HTTP response
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="upload_errors.xlsx"'

        return response

    except Exception as e:
        messages.error(request, f"Could not generate error report: {e}")
        import traceback
        print(traceback.format_exc()) # Log detailed error
        # Optionally clear session data even if report generation failed
        if 'upload_errors' in request.session:
            del request.session['upload_errors']
        return redirect('leads:upload_leads')