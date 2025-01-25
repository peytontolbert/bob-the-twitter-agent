# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft Edge
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg \
    && install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/ \
    && echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge-dev.list \
    && apt-get update \
    && apt-get install -y microsoft-edge-stable

# Install Edge WebDriver
RUN EDGE_VERSION=$(microsoft-edge --version | cut -d ' ' -f 3) \
    && wget https://msedgedriver.azureedge.net/$EDGE_VERSION/edgedriver_linux64.zip \
    && unzip edgedriver_linux64.zip \
    && mv msedgedriver /usr/local/bin/ \
    && rm edgedriver_linux64.zip

# Set up working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create necessary directories
RUN mkdir -p data/conversations logs

# Create entrypoint script
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 &\nexport DISPLAY=:99\nuvicorn api_server:app --host 0.0.0.0 --port 8000 & python mainwithautotweet.py' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Expose the FastAPI port
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"] 