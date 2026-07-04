FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files at build time with dummy env vars. Real values
# for SECRET_KEY / DATABASE_URL / BREVO_WEBHOOK_SECRET come from Cloud
# Run env at runtime; production.py raise-if-missing on those is fine
# because we pass placeholder values here.
RUN DATABASE_URL=sqlite:///tmp/db.sqlite3 SECRET_KEY=build-only-key \
    BREVO_WEBHOOK_SECRET=build-only-secret \
    python manage.py collectstatic --noinput --settings=sjktconnect.settings.production

CMD python manage.py migrate --noinput && \
    exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 120 sjktconnect.wsgi:application
