# Base Python image
FROM python:3.12-slim-bullseye
WORKDIR /app
# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER="true"
ENV PYTHONPATH="/app/src"

# Set the working directory in the container
WORKDIR /app

# Copy chatServer requirements and install dependencies
COPY chatServer/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the src directory (core agent logic)
COPY src /app/src

# Copy the config directory (agent configurations)
COPY config /app/config

# Copy the global_context data
COPY data/global_context /app/data/global_context

# Copy the chatServer application code
COPY chatServer/main.py /app/main.py

# Expose the port the app runs on
EXPOSE 3001

# Command to run the application
# main.py already calls uvicorn.run, so we just execute the script.
CMD ["python", "main.py"] 