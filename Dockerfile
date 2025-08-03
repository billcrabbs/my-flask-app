# Use a minimal base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y gcc libgrpc++-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy dependencies first and install them
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port used by Flask
EXPOSE 8080

# Run the app
CMD ["python", "app.py"]

