# Story2Audio

## 🎙️ Turn Text Stories into Emotionally Expressive Audio Narratives

![Story2Audio Banner](https://github.com/user-attachments/assets/090b4632-332f-4388-b243-a2ebc868c08e)


## Table of Contents
- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation & Setup](#installation--setup)
  - [Prerequisites](#prerequisites)
  - [Docker Setup](#docker-setup)
  - [Manual Setup](#manual-setup)
- [API Documentation](#api-documentation)
  - [gRPC Endpoints](#grpc-endpoints)
  - [Request/Response Formats](#requestresponse-formats)
- [Usage Guide](#usage-guide)
  - [Gradio UI](#gradio-ui)
  - [Postman Collection](#postman-collection)
- [Model Information](#model-information)
  - [Story Generation](#story-generation)
  - [Emotion Detection](#emotion-detection)
  - [Voice Cloning & TTS](#voice-cloning--tts)
- [Testing & Performance](#testing--performance)
  - [Test Cases](#test-cases)
  - [Performance Metrics](#performance-metrics)
- [Limitations](#limitations)
- [Future Work](#to-do) 
- [Contributers](#contributers)
  


## Project Overview

Story2Audio is an AI-powered microservice that transforms simple storylines into rich, emotionally expressive audio narratives, similar to professional audiobooks. The system leverages state-of-the-art LLM technology to enhance storylines, segment them into emotionally distinct parts, and then renders them as audio using either custom voice recordings or default voices enhanced with emotional expression.

This project was developed as part of an Natural Language Processing course requirement, focusing on creating a scalable, reliable, and performant microservice with thorough documentation and testing.

## Features

- **Story Enhancement**: Transform basic storylines into fully developed narratives
- **Genre Selection**: Choose from 8 different genres to influence story development
  - Fantasy, Adventure, Romance, Horror, Sci-Fi, Mystery, Comedy, Drama
- **Voice Customization**: Use your own voice recordings or default voices
- **Emotional Expression**: Automatic emotion detection and mapping to appropriate voice styles
- **Concurrent Processing**: Handle multiple story-to-audio requests simultaneously
- **API-First Design**: Fully featured gRPC API with proper error handling
- **Containerized Deployment**: Simple setup via Docker

## Architecture

The Story2Audio system consists of the following key components:

1. **gRPC API Layer**: Handles incoming requests and manages concurrent processing
2. **Story Enhancement Module**: Uses Ollama LLM to develop storylines based on genre
3. **Emotion Detection & Segmentation**: Analyzes text to identify emotional segments
4. **Voice Processing**: Handles voice cloning with F5TTS technology
5. **Audio Generation**: Creates final audio output with appropriate emotional expressions
6. **Gradio Frontend**: User-friendly interface for interacting with the service

![Architecture Diagram](https://github.com/user-attachments/assets/3be3487c-3093-40ce-98a6-43a26ea34c1f)


### Data Flow

1. User submits a storyline and selects genre through Gradio UI or API
2. Story Enhancement Module expands the storyline into a complete narrative
3. Emotion Detection segments the story by emotional content
4. Voice Processing maps emotions to appropriate voice recordings
5. Audio Generation creates the final audio file
6. Response is returned to the user with the generated audio story

## Installation & Setup

### Prerequisites

- Python 3.10.0 
- Docker and Docker Compose (for containerized setup)
- ffmpeg for audio processing
- 8GB+ RAM recommended for optimal performance
- GPU support recommended but not required

### Docker Setup

The easiest way to run Story2Audio is using Docker:

```bash
# Clone the repository
git clone https://github.com/yourusername/story2audio.git
cd story2audio

# Build and run the Docker container
docker-compose up --build

# The service will be available at:
# - gRPC API: localhost:50051
# - Gradio UI: http://localhost:7860
```

### Manual Setup

For development or custom installations:

```bash
# Clone the repository
git clone https://github.com/yourusername/story2audio.git
cd story2audio

# Create and activate a virtual environment
conda create -n story_to_audio  # create environment
conda activate story_to_audio   # activate environment

# Install dependencies
pip install -r requirements.txt
pip install -r voice_cloning.requirements.txt

# Download the TTS weights from and place them in voice_cloning/ckpts/F5TTS
https://huggingface.co/SWivid/F5-TTS

# Run ollama by typing the command below in cmd:
ollama serve

# Start the individual gRPC servers for below in different terminals
python story_service.py
python audio_service.py

# open a new terminal and run main.py (the api that would listen requests from gradio app and other clients)
python main.py
# In a separate terminal, start the Gradio UI
python frontend.py
```

## API Documentation

### gRPC Endpoints

The Story2Audio service exposes the following gRPC endpoints:

#### `/story-to-audio` (Primary Endpoint)

Generates an audio story from a given storyline.

**Input Parameters:**
- `storyline` (string, required): The basic story outline or prompt
- `genre` (string, optional): One of the supported genres
- `use_custom_voice` (boolean, optional): Whether to use custom voice recordings
- `voice_recordings` (binary[], optional): Array of 8 audio files for emotions if `use_custom_voice` is true

**Response:**
- `audio_story` (binary): The generated audio file
- `enhanced_story` (string): The LLM-enhanced story text
- `segments` (object[]): List of story segments with emotion labels
- `status` (object): Status information and any errors

### Request/Response Formats

Example request in pseudo-protobuf format:

```protobuf
message GenerateRequest {
  string storyline = 1;
  string genre = 2;
  bool use_custom_voice = 3;
  repeated bytes voice_recordings = 4;
}

message GenerateResponse {
  bytes audio_story = 1;
  string enhanced_story = 2;
  repeated Segment segments = 3;
  Status status = 4;
}

message Segment {
  string text = 1;
  string emotion = 2;
  float start_time = 3;
  float end_time = 4;
}

message Status {
  int32 code = 1;
  string message = 2;
}
```

## Usage Guide

### Gradio UI

The Gradio interface provides a user-friendly way to interact with the Story2Audio service:

1. Enter your storyline in the text input field
2. Select genre of choice from the dropdown menu
3. Choose whether to use your own voice recordings or the default voice
4. If using custom voice, upload 8 audio recordings corresponding to different emotions:
   - Angry
   - Sad
   - Calm
   - Happy
   - Fear
   - Disgust
   - Surprise
   - Neutral
5. Click "Generate" and wait for the story processing to complete
6. Listen to the generated audio story and view the enhanced text

![Gradio UI Screenshot](https://github.com/user-attachments/assets/643592da-b948-4564-afb3-82f53904276e)

### Postman Collection

A Postman collection is provided for testing the gRPC API directly:

1. Import the `Story2Audio.postman_collection.json` file into Postman
2. Select the "Generate Audio Story" request
3. Modify the request body as needed
4. Send the request and receive the audio story response

## Model Information

### Story Generation

- **Model**: Ollama LLM
- **Purpose**: Enhances basic storylines into fully developed narratives based on selected genre
- **Implementation**: The system uses a context-aware prompt to guide the LLM in generating appropriate content
- **Customization**: Genre selection influences the tone, plot development, and themes

### Emotion Detection

- **Purpose**: Segments the enhanced story into emotionally distinct parts
- **Implementation**: Uses natural language processing to identify emotional context in each segment
- **Emotions Detected**: Angry, Sad, Calm, Happy, Fear, Disgust, Surprise, Neutral

### Voice Cloning & TTS

- **Model**: F5TTS (Fifth Text-to-Speech)
- **Purpose**: Converts text to speech with emotional expression
- **Implementation**: 
  - For custom voices: Uses voice cloning technology to mimic the user's voice with emotional variations
  - For default voices: Uses pre-trained voice models with emotion parameters
- **Voice Samples**: Requires 8 different emotion recordings for optimal voice cloning

## Testing & Performance

### Test Cases

The repository includes comprehensive test cases covering:

1. **Unit Tests**: Validating individual component functionality
2. **Integration Tests**: Ensuring proper interaction between components
3. **API Tests**: Verifying correct gRPC endpoint behavior
4. **Performance Tests**: Measuring system behavior under various loads

To run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/api/
python -m pytest tests/performance/
```

### Performance Metrics

The Story2Audio service has been rigorously tested for performance and scalability:

#### Concurrent Request Handling

The system was tested with varying numbers of concurrent requests to measure performance degradation:


| Concurrency | Avg Time (s) | CPU (%) | Mem (%) | GPU (%) |
|-------------:|-------------:|--------:|--------:|--------:|
|            1 |       81.58 |    17.2 |    84.3 |    39.5 |
|            5 |      241.88 |    22.2 |    81.6 |    54.0 |
|           10 |      372.85 |    25.3 |    78.7 |    58.9 |
|           20 |      593.69 |    26.9 |    82.2 |    57.9 |

![Performance Graphs](https://github.com/user-attachments/assets/474e0e95-e8f9-4771-a891-08af3a35a3de)

# Limitations 
Current limitations of the Story2Audio system include:

- Story Length: Currently optimized for short to medium-length stories (up to ~1000 words)
- Language Support: Currently supports English text only
- Emotion Granularity: Limited to 8 basic emotions
- Processing Time: Audio generation can take several minutes for longer stories
- Voice Quality: Custom voice cloning quality depends on recording clarity and consistency

# TODO:
 Convert this to story to video

## Contributers
- Sammar Kaleem
- Malaika Saleem
- Aiza Ali



