# 1. Start from an official, lightweight Python base image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy only the requirements file first to leverage caching
COPY api/requirements.api.txt .

# 4. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.api.txt

# 5. Copy your API code into the container
COPY api/ /app

# 6. Specify the command to run when the container starts
# The '-u' flag is a best practice for Python in Docker. It ensures
# logs are printed immediately without being buffered.
CMD ["python3", "-u", "api.py"]