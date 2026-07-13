# backend/Dockerfile
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your backend code
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Start the SSE server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]