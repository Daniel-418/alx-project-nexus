#!/bin/bash
# collect static files
set -e

# echo "collecting static"
# python manage.py collectstatic --noinput --clear || true
# echo "done collecting static"

# wait for postgres
echo "Waiting for postgres..."
while ! nc -z db 5432; do
	sleep 0.1
done

echo "PostgreSQL started"
# make migrations to database
echo "running migrations"
python manage.py migrate
echo "done running migrations"

# start the server
exec "$@"
