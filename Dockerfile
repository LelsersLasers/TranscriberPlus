# Use Fedora 40 as the base image
FROM fedora:40

# Set environment variables
ENV FLASK_APP=main.py \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=3004 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production

# Install required dependencies
RUN dnf install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    git \
	ffmpeg-free \
	sqlite \
    && dnf clean all

# Install Python dependencies
RUN python3 -m pip install flask flask_cors flask_socketio openai-whisper

# Set up backend
WORKDIR /app/backend
COPY backend/ /app/backend/

# Set up frontend
WORKDIR /app/frontend
COPY frontend/ /app/frontend/
RUN npm install -g rollup \
    && npm install \
    && npm run build

# Expose the port Flask will run on
EXPOSE 3004


WORKDIR /app/backend
CMD ["python3", "main.py"]
