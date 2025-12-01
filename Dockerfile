# Use a small Python base image
FROM python:3.12-slim

# Create and set working directory
WORKDIR /app

# Install system deps (optional but good for many Python libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# App Runner expects us to listen on a port, we'll use 5000
ENV PORT=5000
EXPOSE 5000

# Run the Flask app with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
