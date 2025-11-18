FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers and system dependencies
RUN playwright install --with-deps chromium

# Copy application files
COPY ring_monitor.py .
COPY ring_browser_auth.py .
COPY server.py .
COPY templates/ templates/

# Copy config template
COPY config.json .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "server.py"]
