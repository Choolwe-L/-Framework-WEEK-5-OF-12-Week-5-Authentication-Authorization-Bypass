# Hardened FitTrack API container
FROM python:3.12-slim

# Run as a non-root user
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

USER appuser
EXPOSE 5000

# JWT_SECRET must be supplied at runtime (e.g. -e JWT_SECRET=... or a secret store)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
