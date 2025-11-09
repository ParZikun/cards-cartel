# 1. Start from an official, lightweight Python base image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Set the Python path to include the source root
ENV PYTHONPATH /app

# 4. Copy only the requirements file first to leverage Docker's caching
COPY src/worker/requirements.txt .

# 5. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the contents of the src directory into the container's /app directory
COPY src/database /app/database
COPY src/worker /app/worker

# 7. Remove __pycache__ directories to prevent using stale bytecode
RUN find . -type d -name "__pycache__" -exec rm -r {} +

# 8. Specify the command to run when the container starts
CMD ["python3", "-m", "worker.app.main"]