FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY src/ /app/

# Expose port
EXPOSE 8000

# Run server
CMD ["python3", "server.py"]
