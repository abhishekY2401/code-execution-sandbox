#!/bin/sh

echo "Waiting for database..."
sleep 3

# Initialize migrations folder if not exists
if [ ! -d "migrations" ]; then
  echo "Initializing migrations..."
  flask db init
fi

echo "Creating migration (if needed)..."
flask db migrate -m "auto migration" || true

echo "Applying migrations..."
flask db upgrade

echo "Starting Gunicorn..."
exec gunicorn run:app --bind 0.0.0.0:5000