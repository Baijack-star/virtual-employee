# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code (app directory, static, templates) into the container at /app
COPY ./app ./app
COPY ./static ./static
COPY ./templates ./templates

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable (optional, can be useful)
ENV APP_MODULE="app.main:app"
ENV HOST="0.0.0.0"
ENV PORT="8000"

# Run app.main.py when the container launches
# Use uvicorn directly for production is common, ensure all necessary flags are present
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
