# 1. Start from an official, lightweight Python base image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 2. Set the Python path to include the source root
ENV PYTHONPATH /app

# 3. Copy only the requirements file first to leverage Docker's caching
COPY src/worker/requirements.txt .

# 4. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the entire source code into the container
COPY src/ .

# 7. Specify the command to run when the container starts
CMD ["python3", "-m", "worker.app.main"]