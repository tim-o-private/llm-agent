# Base Python image
FROM python:3.12-slim-bullseye
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER="true"
ENV PYTHONPATH="/app/src"
ENV CHAT_SERVER_BASE_URL="https://clarity-chatserver.fly.dev"

# Copy chatServer requirements and install dependencies
COPY chatServer/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the src directory (core agent logic — available via PYTHONPATH)
COPY src /app/src

# Copy the entire chatServer package (main.py + all sub-packages)
# This places config/, routers/, services/, database/, etc. at /app/
# so bare imports like `from config.constants import ...` resolve correctly.
COPY chatServer/ /app/

# Copy agent configuration files (settings.yaml, agents/*.yaml)
# Merges into /app/config/ alongside chatServer's Python config modules.
# No file conflicts: repo root has .yaml files, chatServer has .py files.
COPY config/ /app/config/

# Copy the global_context data
COPY data/global_context /app/data/global_context

# Expose the port the app runs on
EXPOSE 3001

# Command to run the application
# main.py already calls uvicorn.run, so we just execute the script.
CMD ["python", "main.py"]