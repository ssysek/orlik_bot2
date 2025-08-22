# Dockerfile
FROM python:3.12-slim

# Avoid interactive prompts & speed up installs
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-input -r requirements.txt

COPY . /app

# Default command (can be overridden)
CMD ["python", "bot.py"]
