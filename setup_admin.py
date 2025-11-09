
import os
import django

# Django ko setup karein
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leadgenpro.settings')
django.setup()

from django.contrib.auth.models import User

# Render ke Environment Variables se admin details lein
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'zakir_hussain')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'DLG@2026#database')  
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'zakirdataleadgen@gmail.com')

# Check karein ki user pehle se bana hua toh nahi hai
if not User.objects.filter(username=ADMIN_USERNAME).exists():
    print(f"Creating superuser: {ADMIN_USERNAME}")
    User.objects.create_superuser(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        email=ADMIN_EMAIL
    )
    print("Superuser created successfully.")
else:
    print(f"Superuser '{ADMIN_USERNAME}' already exists.")