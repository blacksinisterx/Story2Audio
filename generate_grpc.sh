#!/bin/bash

# Generate Python code from proto files
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto_files/story_service.proto
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/audio_service.proto
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto_files/image_service.proto

echo "gRPC code generated successfully!"