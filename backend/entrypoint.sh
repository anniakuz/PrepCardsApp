#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py seed_questions
if [ "${DJANGO_DEBUG:-1}" = "1" ]; then
  python manage.py seed_demo
fi
python manage.py runserver 0.0.0.0:8000
