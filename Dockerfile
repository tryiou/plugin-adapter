FROM python:3.11-slim
LABEL maintainer="Blocknet"
LABEL description="Plugin Adapter Cryptocurrency Service - Secure Container"

# Install security updates and required system packages
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directory with proper permissions
RUN mkdir -p /app && chown -R root:root /app
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements.txt \
    && pip check

# Copy application code
COPY . /app

# Set proper file permissions
RUN chmod +r /app/* && chmod +x /app/plugin-adapter.py

# Use non-root user for security (optional enhancement)
# RUN groupadd -r appgroup && useradd -r -g appgroup appuser
# RUN chown -R appuser:appgroup /app
# USER appuser

EXPOSE 5000
ENTRYPOINT [ "python" ]
CMD [ "plugin-adapter.py" ]
