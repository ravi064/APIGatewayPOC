FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY authz-service/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared /app/shared

# Copy application code
COPY authz-service/ .

# Set default service port and expose it (for documentation)
ENV SERVICE_PORT=9000
EXPOSE 9000

# Copy entrypoint script
COPY authz-service/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run the application using entrypoint script (JSON form for proper signal handling)
CMD ["/app/start.sh"]
