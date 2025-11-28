FROM python:3.10-slim

WORKDIR /app

# Install system libs needed by matplotlib
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential gcc g++ \
        libfreetype6-dev libpng-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy scripts and requirements
COPY scripts /app/scripts
COPY requirements.txt /app/requirements.txt

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
