#!/usr/bin/env bash
set -o errexit

python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --noinput

if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
  python manage.py create_platform_admin
else
  echo "ADMIN_USERNAME/ADMIN_PASSWORD not set; skipping platform admin creation."
fi
