FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared/ ./shared/

# Copy service code
COPY services/distribution/ ./services/distribution/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8010

# Run the service
CMD ["uvicorn", "services.distribution.main:app", "--host", "0.0.0.0", "--port", "8010"]
