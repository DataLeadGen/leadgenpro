from django.db import models

from django.contrib.auth.models import User
# Create your models here.

class Lead(models.Model):
    # Person/Contact Information
    lead_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    job_title = models.CharField(max_length=200, blank=True, null=True)
    professional_email = models.EmailField(unique=True)
    email_status = models.CharField(max_length=100, blank=True, null=True)
    personal_email = models.EmailField(blank=True, null=True)
    person_linkedin_url = models.URLField(blank=True, null=True)
    person_city = models.CharField(max_length=100, blank=True, null=True)
    person_state = models.CharField(max_length=100, blank=True, null=True)
    person_country = models.CharField(max_length=100, blank=True, null=True)
    person_direct_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Company Information
    company_id = models.CharField(max_length=100, blank=True, null=True)
    company_name = models.CharField(max_length=200)
    company_website = models.URLField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    employees = models.CharField(max_length=50, blank=True, null=True)
    generic_email = models.EmailField(blank=True, null=True)
    full_address = models.TextField(blank=True, null=True)
    first_address = models.CharField(max_length=200, blank=True, null=True)
    company_city = models.CharField(max_length=100, blank=True, null=True)
    company_state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    company_country = models.CharField(max_length=100, blank=True, null=True)
    company_linkedin_url = models.URLField(blank=True, null=True)
    company_phone = models.CharField(max_length=20, blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    revenue = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional fields
    status = models.CharField(max_length=50, default='New', 
                             choices=[('New', 'New'), ('Contacted', 'Contacted'), 
                                     ('Qualified', 'Qualified'), ('Lost', 'Lost')])
    source = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leads')
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.company_name}"
    
    def save(self, *args, **kwargs):
        # Automatically generate full_name if not provided
        if not self.full_name and self.first_name and self.last_name:
            self.full_name = f"{self.first_name} {self.last_name}"
        super().save(*args, **kwargs)