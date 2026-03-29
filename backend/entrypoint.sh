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
if [ "$RUN_MIGRATIONS" = "true" ]; then
	echo "Running migrations..."
	python manage.py migrate --noinput
	echo "done running migrations"
fi

# start the server
exec "$@"
