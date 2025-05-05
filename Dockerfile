FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install netcat (for waiting on ports) and clean up apt cache
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
# Copy requirements files and install Python dependencies
COPY requirements.txt voice_cloning/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r voice_cloning/requirements.txt


# Copy the rest of the application code into the container
COPY . .

# Compile all .proto files in proto_files/ into Python modules
RUN python -m grpc_tools.protoc -I proto_files \
    --python_out=proto_files --grpc_python_out=proto_files proto_files/*.proto

# Expose FastAPI and gRPC ports
EXPOSE 5000 50051 50052

# Copy and set executable permissions on the startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Set the default command to the startup script
CMD ["/app/start.sh"]
