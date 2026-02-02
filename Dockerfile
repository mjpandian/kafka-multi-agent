FROM python:3.11-slim
WORKDIR /app
# Install dependencies
RUN pip install --no-cache-dir kafka-python-ng openai flask qdrant-client ollama
 
# Copy all agent scripts
COPY . .
# The command is defined in docker-compose.yaml per servicedock