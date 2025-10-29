#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating superuser if not exists..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: username=admin, password=admin123')
else:
    print('Superuser already exists')
EOF

echo "Loading initial data if needed..."
python manage.py shell << EOF
from reservations.models import RentalItem
if RentalItem.objects.count() == 0:
    import os
    os.system('python manage.py loaddata fixtures/initial_items.json')
    print('Initial items loaded')
else:
    print('Items already exist, skipping loaddata')
EOF

echo "Starting gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 config.wsgi:application
