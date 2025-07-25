# Use official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY src/ ./src/

# Expose the port FastAPI will run on
EXPOSE 8000

# Define volumes for input and SQLite database
VOLUME ["/app/input"]
VOLUME ["/app/sqlite"]

# Set environment variables for input and SQLite database path
ENV INPUT_DIR=/app/input \
    MY_MONEY_SQLITE_PATH=/app/sqlite/my_money.db

# Run the FastAPI app with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"] 