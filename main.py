import argparse
import logging
import time
import os
import json
from typing import Dict, List, Optional, Any, Union

import grpc.aio
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import the proto generated files
from proto_files import story_service_pb2
from proto_files import story_service_pb2_grpc
from proto_files import audio_service_pb2
from proto_files import audio_service_pb2_grpc
from proto_files import image_service_pb2
from proto_files import image_service_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Story to Audio Orchestration Service",
    description="An API that orchestrates story generation, audio synthesis, and image creation services",
    version="1.0.0"
)

# Global flag to determine if image generation should be enabled
ENABLE_IMAGE_GENERATION = False

# Global stubs for gRPC services
story_stub = None
audio_stub = None
image_stub = None

# Define data models for API requests and responses
class StoryRequest(BaseModel):
    storyline: str = Field(..., description="The storyline idea for the story")
    genre: str = Field(..., description="The genre of the story")

class TextEmotionPair(BaseModel):
    text: str
    emotion: str

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "Story to Audio API"
    image_service_enabled: bool
    timestamp: float

class StoryToAudioResponse(BaseModel):
    status: str = "success"
    story: str
    sentences: List[TextEmotionPair]
    audio_file_path: str
    image_paths: Optional[List[str]] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str

# Initialize gRPC service stubs
async def setup_grpc_services():
    """Set up gRPC service stubs with async channels"""
    global story_stub, audio_stub, image_stub
    
    logger.info("Setting up gRPC services...")
    
    # Create async gRPC channels
    story_channel = grpc.aio.insecure_channel('localhost:50051')
    story_stub = story_service_pb2_grpc.StoryGeneratorStub(story_channel)
    logger.info("Story generator service configured")
    
    audio_channel = grpc.aio.insecure_channel('localhost:50052')
    audio_stub = audio_service_pb2_grpc.AudioGeneratorStub(audio_channel)
    logger.info("Audio generator service configured")
    
    if ENABLE_IMAGE_GENERATION:
        image_channel = grpc.aio.insecure_channel('localhost:50053')
        image_stub = image_service_pb2_grpc.ImageGeneratorStub(image_channel)
        logger.info("Image generation service enabled and configured")
    else:
        logger.info("Image generation service is disabled")

# FastAPI startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await setup_grpc_services()

# FastAPI shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down services...")
    # Close channels if needed

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "ok",
        "service": "Story to Audio API",
        "image_service_enabled": ENABLE_IMAGE_GENERATION,
        "timestamp": time.time()
    }

# Echo endpoint for testing
@app.post("/echo")
async def echo(request: Request):
    """Echo back the request data for testing"""
    try:
        data = await request.json()
        return {
            "status": "success",
            "received_data": data,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing request: {str(e)}")

# Main endpoint to convert storyline to audio
@app.post("/story-to-audio", response_model=StoryToAudioResponse)
async def story_to_audio(story_request: StoryRequest):
    """
    Convert a storyline and genre into an audio story
    
    This endpoint orchestrates:
    1. Story generation based on storyline and genre
    2. Emotion analysis of the story
    3. Audio generation with appropriate emotions
    4. (Optional) Image generation for key scenes
    """
    try:
        storyline = story_request.storyline
        genre = story_request.genre
        
        # Step 1: Generate the story
        logger.info(f"Generating {genre} story...")
        story_response = await story_stub.GenerateStory(
            story_service_pb2.StoryRequest(storyline=storyline, genre=genre)
        )
        story = story_response.story
        logger.info(f"Story generated successfully ({len(story)} characters)")
        
        # Step 2: Process story emotions
        logger.info("Processing story emotions...")
        process_request = story_service_pb2.ProcessRequest(story=story)
        emotion_response = await story_stub.ProcessStoryEmotions(process_request)
        sentences = emotion_response.sentences
        logger.info(f"Story broken into {len(sentences)} sentence-emotion pairs")
        
        # Step 3: Generate audio from sentences with emotions
        logger.info("Generating audio...")
        audio_request = audio_service_pb2.AudioRequest()
        for pair in sentences:
            text_emotion = audio_service_pb2.TextEmotion(
                text=pair.text,
                emotion=pair.emotion
            )
            audio_request.segments.append(text_emotion)
            
        audio_response = await audio_stub.GenerateAudio(audio_request)
        
        if audio_response.success:
            audio_file_path = audio_response.audio_file_path
            logger.info(f"Audio generated successfully: {audio_file_path}")
        else:
            logger.error(f"Audio generation failed: {audio_response.error}")
            raise HTTPException(
                status_code=500, 
                detail=f"Audio generation failed: {audio_response.error}"
            )
        
        # Step 4 (Optional): Generate scene prompts and images
        image_paths = []
        if ENABLE_IMAGE_GENERATION and image_stub is not None:
            try:
                # Generate scene prompts
                logger.info("Generating scene prompts...")
                scene_request = story_service_pb2.SceneRequest(story=story)
                scene_response = await story_stub.GenerateScenePrompts(scene_request)
                scenes = scene_response.scenes
                logger.info(f"Generated {len(scenes)} scene prompts")
                
                # Generate images for scenes
                logger.info("Generating images for scenes...")
                image_request = image_service_pb2.ImageRequest(
                    scenes=[
                        image_service_pb2.Scene(
                            start_line=scene.start_line,
                            end_line=scene.end_line,
                            prompt=scene.prompt
                        ) for scene in scenes
                    ]
                )
                image_response = await image_stub.GenerateImages(image_request)
                image_paths = [img.image_file_path for img in image_response.images]
                logger.info(f"Generated {len(image_paths)} images")
            except Exception as e:
                logger.error(f"Error in image generation process: {str(e)}")
                # Continue with just the audio if image generation fails
        
        # Prepare and return the response
        result = {
            "status": "success",
            "story": story,
            "sentences": [
                {"text": pair.text, "emotion": pair.emotion}
                for pair in sentences
            ],
            "audio_file_path": audio_file_path
        }
        
        if image_paths:
            result["image_paths"] = image_paths
        
        return result
    
    except grpc.aio.AioRpcError as rpc_error:
        logger.error(f"gRPC error: {rpc_error.code()}: {rpc_error.details()}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {rpc_error.details()}"
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

# Add a file serving endpoint to serve generated files
@app.get("/files/{file_path:path}")
async def get_file(file_path: str):
    """Serve generated files"""
    # This is a placeholder. In a real implementation, you would:
    # 1. Validate the file_path
    # 2. Check if the file exists
    # 3. Return the file with appropriate MIME type
    # For now, we'll just return a 501 Not Implemented
    raise HTTPException(status_code=501, detail="File serving not implemented yet")

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Story to Audio Orchestration Service')
    parser.add_argument('--disable-images', action='store_true', help='Disable image generation')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind the server to')
    args = parser.parse_args()
    
    global ENABLE_IMAGE_GENERATION
    ENABLE_IMAGE_GENERATION = not args.disable_images
    
    # Start the FastAPI server
    logger.info(f"Starting FastAPI server on {args.host}:{args.port}")
    uvicorn.run(
        "main:app",  # Assumes this file is named main.py
        host=args.host,
        port=args.port,
        reload=True,  # Enable auto-reload (like debug=True in Flask)
        log_level="info"
    )

if __name__ == '__main__':
    main()