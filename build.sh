#!/usr/bin/env bash
# build.sh

# Exit on error
set -o errexit

# Requirements install karein
pip install -r requirements.txt

# Static files collect karein
python manage.py collectstatic --no-input

# Database migrate karein
python manage.py migrate

# Admin user banayein
python setup_admin.py