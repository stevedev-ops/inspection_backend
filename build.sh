#!/usr/bin/env bash
# exit on error
set -o errexit
set -o xtrace

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Migration only
python manage.py migrate

# Automatically create a super admin on deployment if it doesn't exist
cat << EOF | python manage.py shell
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    if not User.objects.filter(email='admin@example.com').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'AdminUser123!', role='super_admin')
        print("Super admin created: admin@example.com / AdminUser123!")
except Exception as e:
    print(f"Error creating superuser: {str(e)}")
EOF
