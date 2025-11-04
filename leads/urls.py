from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    path('', views.leads_list, name='leads_list'),
    path('upload/', views.upload_leads, name='upload_leads'),
    path('export/', views.export_leads, name='export_leads'),
    path('sample/', views.download_sample_csv, name='download_sample_csv'),
    
    # Quick View drawer ke liye JSON data fetch karne ka URL
    path('detail/<int:pk>/json/', views.get_lead_detail_json, name='get_lead_detail_json'),
    
    # --- YEH LINE NAYI ADD HUI HAI ---
    # Selected leads ko export karne ke liye naya URL
    path('export-selected/', views.export_selected_leads, name='export_selected_leads'),
    path('download-upload-errors/', views.download_upload_errors, name='download_upload_errors'),
]