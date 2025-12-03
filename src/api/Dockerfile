# 1. Start from an official, lightweight Python base image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Set the Python path to include the source root
ENV PYTHONPATH /app

# 4. Copy requirements
COPY src/api/requirements.txt .

# 5. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the contents of the src directory
COPY src/database /app/database
COPY src/api /app/api

# 7. Remove __pycache__
RUN find . -type d -name "__pycache__" -exec rm -r {} +

# 8. Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
