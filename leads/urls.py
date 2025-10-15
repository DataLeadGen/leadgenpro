from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    path('', views.leads_list, name='leads_list'),
    path('upload/', views.upload_leads, name='upload_leads'),
    path('export/', views.export_leads, name='export_leads'),
    path('sample/', views.download_sample_csv, name='download_sample_csv'),
]