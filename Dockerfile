# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir is good practice for smaller images
# Using --default-timeout to prevent pip hanging indefinitely on slow networks (optional)
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy the rest of the application code (app directory, static, templates) into the container at /app
COPY ./app ./app
COPY ./static ./static
COPY ./templates ./templates
# .github directory is not typically needed for runtime, so not copied.

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables
# An empty default value for OPENAI_API_KEY means it's expected to be provided at runtime.
ENV OPENAI_API_KEY=""
ENV APP_MODULE="app.main:app" # Retained from original subtask, though uvicorn command below specifies module directly
ENV HOST="0.0.0.0"
ENV PORT="8000"

# Run app.main:app when the container launches.
# Using environment variables for host and port.
# The app module is specified directly here, making APP_MODULE env var somewhat redundant for this CMD,
# but it can be useful if other scripts or tools within the container need to know the app module.
CMD ["uvicorn", "app.main:app", "--host", "${HOST}", "--port", "${PORT}"]
