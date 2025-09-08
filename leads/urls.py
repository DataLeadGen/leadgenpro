from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    path('upload/', views.upload_leads, name='upload_leads'),
    path('', views.leads_list, name='leads_list'),
    path('download-sample/', views.download_sample_csv, name='download_sample'),
]