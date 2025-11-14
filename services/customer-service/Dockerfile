FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY customer-service/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared /app/shared

# Copy application code (includes start.sh)
COPY customer-service/ .

# Set default service port and expose it
ENV SERVICE_PORT=8000
EXPOSE 8000

# Make start.sh executable
RUN chmod +x /app/start.sh

# Run the application using entrypoint script (JSON form for proper signal handling)
CMD ["/app/start.sh"]