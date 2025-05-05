import os
import gradio as gr
import requests
import json
from pydub import AudioSegment
import tempfile
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI backend URL
BACKEND_URL = "http://localhost:5000"  # Change this if your FastAPI runs on a different port

def story2Audio(storyline, genre, use_user_audio, *emotion_audio_files):
    """
    Generate audio from storyline by connecting to FastAPI backend
    """
    try:
        # Create a dictionary of emotion audio files
        emotion_names = ["Angry", "Calm", "Disgust", "Fear", "Happy", "Neutral", "Sad", "Surprise"]
        emotion_audio_dict = {emotion: audio_file for emotion, audio_file in zip(emotion_names, emotion_audio_files) if audio_file}
        
        logger.info(f"Processing storyline: '{storyline}' in genre: '{genre}'")
        
        # If user wants to use their own voice
        if use_user_audio and emotion_audio_dict:
            logger.info("Using custom voice samples")
            # Save the user's emotion audio files and collect paths for the API
            emotion_audio_paths = {}
            for emotion, audio_file in emotion_audio_dict.items():
                save_folder = os.path.join(os.getcwd(), "user_emotions")
                os.makedirs(save_folder, exist_ok=True)
                save_path = os.path.join(save_folder, f"{emotion}_audio.wav")
                
                # If it's already a path string, use it directly
                if isinstance(audio_file, str):
                    emotion_audio_paths[emotion.lower()] = audio_file
                else:
                    # Otherwise it's a file-like object from Gradio
                    emotion_audio_paths[emotion.lower()] = save_path
            
            # Custom voice API call
            payload = {
                "storyline": storyline,
                "genre": genre,
                "use_custom_voice": True,
                "emotion_files": emotion_audio_paths
            }
            
            # We'd need to implement file uploads for a real solution
            # For now, let's just use the API without custom voices
            logger.warning("Custom voice upload not fully implemented - using default voice instead")
            payload["use_custom_voice"] = False
        else:
            # Standard API call
            logger.info("Using default voice")
            payload = {
                "storyline": storyline,
                "genre": genre
            }
        
        # Call the FastAPI backend
        logger.info(f"Sending request to {BACKEND_URL}/story-to-audio")
        response = requests.post(
            f"{BACKEND_URL}/story-to-audio",
            json=payload,
            timeout=600  # Longer timeout since story generation can take time
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            logger.info("Successfully received response from API")
            
            # Get the story text
            story_text = result.get("story", "Story text not available")
            
            # Process the audio file
            try:
                if "audio_file_path" in result:
                    api_audio_path = result["audio_file_path"]
                    logger.info(f"Audio file path from API: {api_audio_path}")
                    
                    # Check if the file exists and is accessible
                    if os.path.exists(api_audio_path) and os.access(api_audio_path, os.R_OK):
                        # Copy the file to a location accessible to Gradio
                        temp_dir = tempfile.gettempdir()
                        local_audio_path = os.path.join(temp_dir, f"story_audio_{os.path.basename(api_audio_path)}")
                        
                        # Copy the file
                        shutil.copy2(api_audio_path, local_audio_path)
                        logger.info(f"Copied audio file to: {local_audio_path}")
                        
                        # Return the local path to the audio file
                        return local_audio_path, story_text
                    else:
                        logger.warning(f"Audio file from API not accessible: {api_audio_path}")
                        # Fall back to placeholder if can't access the actual file
                        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        temp_audio.close()
                        
                        # Create a silent audio segment as placeholder
                        audio = AudioSegment.silent(duration=3000)
                        audio.export(temp_audio.name, format="mp3")
                        
                        logger.info(f"Generated placeholder audio at {temp_audio.name}")
                        gr.Warning("Could not access the audio file from the API. Using a placeholder instead.")
                        
                        return temp_audio.name, story_text
                else:
                    logger.warning("No audio file path in API response")
                    gr.Warning("No audio file path was returned by the API.")
                    return None, story_text
            except Exception as e:
                logger.error(f"Error processing audio file: {str(e)}")
                gr.Warning(f"Audio processing error: {str(e)}")
                return None, story_text
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            gr.Warning(error_msg)
            return None, "Error: Failed to get a response from the API."
            
    except requests.RequestException as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        gr.Warning(f"Couldn't connect to the backend API. Is it running? Error: {str(e)}")
        return None, f"Connection error: {str(e)}"
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        gr.Warning(error_msg)
        return None, f"Unexpected error: {str(e)}"

def check_backend_status():
    """Check if the backend API is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return f"✅ Connected to backend API. Image generation: {'enabled' if data.get('image_service_enabled') else 'disabled'}"
        else:
            return "❌ Backend API responded with an error."
    except:
        return "❌ Can't connect to the backend API. Is it running?"

# Define the Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("""
    # 🎭 Story to Audio Generator
    Transform your creative storylines into immersive audio experiences. Select a genre and let the magic happen! 🎶
    """)
    
    # Backend status indicator
    status_indicator = gr.Textbox(label="Backend Status", value="Checking backend connection...", interactive=False)
    
    with gr.Row():
        storyline_input = gr.Textbox(
            label="✍️ Storyline",
            placeholder="Enter your storyline here...",
            lines=3
        )
        genre_input = gr.Dropdown(
            label="🎭 Genre",
            choices=["Fantasy", "Adventure", "Romance", "Horror", "Sci-Fi", "Mystery", "Comedy", "Drama", "Other"],
            value="Fantasy"
        )

    use_user_audio = gr.Checkbox(label="Use Your Own Voice (Experimental)", value=False)

    with gr.Row(visible=False) as emotion_audio_section:
        gr.Markdown("""
        ## 🎙️ Emotion Audio Collector
        Upload or record audio for different emotions like Angry, Calm, Disgust, Fear, Happy, Neutral, Sad, and Surprise.
        """)

        emotion_audio_inputs = {
            emotion: gr.Audio(label=f"{emotion} Audio", type="filepath")
            for emotion in ["Angry", "Calm", "Disgust", "Fear", "Happy", "Neutral", "Sad", "Surprise"]
        }

    def toggle_emotion_audio_section(use_user_audio):
        return gr.update(visible=use_user_audio)

    use_user_audio.change(toggle_emotion_audio_section, inputs=use_user_audio, outputs=emotion_audio_section)

    with gr.Row():
        generate_button = gr.Button("🎧 Generate Audio", variant="primary")
    
    with gr.Row():
        audio_output = gr.Audio(label="🔊 Generated Audio")
    
    # Make the story text box always visible
    with gr.Row():
        story_text_output = gr.Textbox(label="Generated Story", lines=10, interactive=False)

    # Update status on load
    demo.load(check_backend_status, outputs=status_indicator)
    
    def generate_full_output(storyline, genre, use_user_audio, *emotion_audio_files):
        # This function now directly returns both the audio path and story text
        return story2Audio(storyline, genre, use_user_audio, *emotion_audio_files)

    generate_button.click(
        generate_full_output,
        inputs=[storyline_input, genre_input, use_user_audio] + list(emotion_audio_inputs.values()),
        outputs=[audio_output, story_text_output]
    )

if __name__ == "__main__":
    # Launch the Gradio app
    demo.launch()