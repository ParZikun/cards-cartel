# 1. Start from an official, lightweight Python base image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy only the requirements file first to leverage Docker's caching
COPY worker/requirements.txt .

# 4. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the shared database module
COPY database/ ./database/

# 6. Copy the worker application code
COPY worker/ ./worker/

# 7. Specify the command to run when the container starts
CMD ["python3", "worker/main.py"]