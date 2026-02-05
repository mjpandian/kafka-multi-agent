FROM python:3.11-slim
WORKDIR /app
# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy all agent scripts
COPY . .
# The command is defined in docker-compose.yaml per servicedock