FROM python:3.11-slim

LABEL maintainer="erwinvol"
LABEL description="Automatic sync service between MyWhoosh and Garmin Connect with FIT device spoofing"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data \
    GARMIN_TOKEN_DIR=/root/.garminconnect

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create volume directories
RUN mkdir -p /data /root/.garminconnect

# Copy application source
COPY src/ /app/src/

VOLUME ["/data", "/root/.garminconnect"]

ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--daemon"]
