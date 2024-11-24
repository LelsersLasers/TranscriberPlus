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

# Set the working directory for the backend
WORKDIR /app/backend

# Copy backend files
COPY backend/ /app/backend/

# Install Python dependencies
RUN pip install flask flask_cors flask_socketio openai-whisper

# Set the working directory for the frontend
WORKDIR /app/frontend

# Copy frontend files
COPY frontend/ /app/frontend/

# Install Node.js dependencies and build the frontend
RUN npm install -g rollup \
    && npm install \
    && npm run build

# Expose the port Flask will run on
EXPOSE 3004

# Set the working directory back to the backend
WORKDIR /app/backend

# Command to start the Flask app
CMD ["python", "main.py"]
