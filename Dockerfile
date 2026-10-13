# ========================================================
# Stage 1: Build Frontend (React + Vite)
# ========================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ========================================================
# Stage 2: Linux Runner (Python 3.12 + FFmpeg + FastAPI)
# ========================================================
FROM python:3.12-slim AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Jakarta \
    PORT=7080 \
    MULTICAST_IP=239.255.0.1 \
    MULTICAST_PORT=5004

WORKDIR /app

# Install system dependencies:
# - ffmpeg: audio decoding & multicast RTP streaming
# - iputils-ping: ICMP ping telemetry for speaker monitoring
# - tzdata: timezone support for APScheduler (WIB / Asia/Jakarta)
# - curl: container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    iputils-ping \
    tzdata \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set local system timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install Python backend dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code & launcher
COPY backend ./backend
COPY run_server.py ./

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose ports:
# 7080: Web Dashboard & REST/WebSocket API
# 5004/udp: RTP Multicast / Unicast Audio Stream
EXPOSE 7080
EXPOSE 5004/udp

# Storage volume for SQLite DB and uploaded audio files
VOLUME ["/app/backend/storage"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7080/api/health || exit 1

CMD ["python", "run_server.py"]
