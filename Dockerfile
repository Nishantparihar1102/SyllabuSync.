FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/templates /app/static/css /app/static/js

# Copy application files
COPY . .

EXPOSE 5000

# Use gunicorn as the WSGI HTTP Server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
