# leads/urls.py
from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    path('', views.leads_list, name='leads_list'),
    path('upload/', views.upload_leads, name='upload_leads'),
    path('export/', views.export_leads, name='export_leads'),
    path('export-selected/', views.export_selected_leads, name='export_selected_leads'),
    path('download-sample/', views.download_sample_csv, name='download_sample_csv'),
    path('get-lead-detail/<int:pk>/', views.get_lead_detail_json, name='get_lead_detail_json'),
    path('download-upload-errors/', views.download_upload_errors, name='download_upload_errors'),
    
    # Debug route (temporary)
    path('₹/', views.debug_filters, name='debug_filters'),
]