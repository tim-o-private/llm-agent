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

# Copy chatServer as a proper Python package at /app/chatServer/
# Preserves the same import structure as local dev: `from chatServer.xxx`
COPY chatServer/ /app/chatServer/

# Copy agent configuration files (settings.yaml, agents/*.yaml)
# These live at /app/config/ — separate from chatServer/config/ (Python modules)
COPY config/ /app/config/

# Copy the global_context data
COPY data/global_context /app/data/global_context

# Expose the port the app runs on
EXPOSE 3001

# Run as a module so chatServer is a proper package and relative imports work
CMD ["python", "-m", "chatServer.main"]