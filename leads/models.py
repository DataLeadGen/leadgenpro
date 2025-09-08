from django.db import models

from django.contrib.auth.models import User
# Create your models here.

class Lead(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.IntegerField(blank=True, null=True)
    company = models.CharField(max_length=200)
    job_title = models.CharField(max_length=200, blank=True, null=True)
    industry = models.CharField(max_length=100, null=True, blank=True)
    website = models.URLField(unique=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    
    #additional fields
    status = models.CharField(max_length=50, default='New', 
                             choices=[('New', 'New'), ('Contacted', 'Contacted'), 
                                     ('Qualified', 'Qualified'), ('Lost', 'Lost')])

    source = models.CharField(max_length=100, blank=True, null=True)
    notes = models.CharField(blank=True, null=True)
    
    #leads add karne ka timings matlab leads kab add, update, create huyi hain,
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leads')
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.company}"