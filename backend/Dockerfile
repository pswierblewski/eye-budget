# Use official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='en')"

# Copy the application code and migrations
COPY src/ ./src/
COPY migrations/ ./migrations/

# Expose the port FastAPI will run on
EXPOSE 8000

# Define volumes for input and SQLite database
VOLUME ["/app/input"]
VOLUME ["/app/sqlite"]

# Set environment variables for input and SQLite database path
ENV INPUT_DIR=/app/input

# Run the FastAPI app with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]