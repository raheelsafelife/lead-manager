# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Robust pip installation
RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy the rest of the application code
COPY . .

# Patch Streamlit Branding (Deep Fix to eliminate flash)
RUN STREAMLIT_PATH=$(python3 -c "import streamlit; import os; print(os.path.dirname(streamlit.__file__))") && \
    cp frontend_app/icon1.png "$STREAMLIT_PATH/static/favicon.png" && \
    sed -i 's/<title>Streamlit<\/title>/<title>Lead Manager<\/title>/g' "$STREAMLIT_PATH/static/index.html" && \
    sed -i 's/favicon.png/favicon.png?v=2/g' "$STREAMLIT_PATH/static/index.html"

# Create a data directory for the persistent database and set permissions
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

# The actual command will be handled by docker-compose
CMD ["python3"]
