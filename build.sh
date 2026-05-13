#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Seed business data from Excel if the table is empty
cat << 'PYEOF' | python manage.py shell
from inspections.models import Business
if Business.objects.count() == 0:
    import subprocess
    result = subprocess.run(['python', 'manage.py', 'seed_data'], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
else:
    print(f"Skipping seed — {Business.objects.count()} businesses already in DB.")
PYEOF

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
