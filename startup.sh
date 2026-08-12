#!/bin/bash
set -e

echo "Starting LSS Invoice Automation App Service initialization..."

# Update pip
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install additional production dependencies
echo "Installing production dependencies..."
pip install gunicorn flask

# Set Python to unbuffered mode
export PYTHONUNBUFFERED=1

# Collect environment info
echo "Environment configuration:"
echo "- Python version: $(python --version)"
echo "- Pip version: $(pip --version)"
echo "- Platform: $(uname -a)"
echo "- Port: ${PORT:-5000}"

# Start the application
echo "Starting Flask application with Gunicorn..."
exec gunicorn \
  --bind=0.0.0.0 \
  --timeout=600 \
  --workers=1 \
  --worker-class=sync \
  --access-logfile=- \
  --error-logfile=- \
  --log-level=info \
  app:app
