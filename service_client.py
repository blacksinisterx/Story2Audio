import grpc
import logging
from typing import List, Dict, Optional, Union

# Import generated gRPC modules
from proto_files import story_service_pb2
from proto_files import story_service_pb2_grpc
from proto_files import audio_service_pb2
from proto_files import audio_service_pb2_grpc
from proto_files import image_service_pb2
from proto_files import image_service_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



class ServiceClient:
    """Client for interacting with all services."""
    
    def __init__(
        self, 
        story_service_addr: str = "localhost:50051", 
        audio_service_addr: str = "localhost:50052",
        image_service_addr: Optional[str] = "localhost:50053"
    ):
        """
        Initialize connections to all services.
        
        Args:
            story_service_addr: Address of the Story Generator Service
            audio_service_addr: Address of the Audio Generator Service
            image_service_addr: Address of the Image Generator Service (optional)
        """
        # Setup story service client
        self.story_channel = grpc.insecure_channel(story_service_addr)
        self.story_client = story_service_pb2_grpc.StoryGeneratorStub(self.story_channel)
        logger.info(f"Connected to Story Service at {story_service_addr}")
        
        # Setup audio service client
        self.audio_channel = grpc.insecure_channel(audio_service_addr)
        self.audio_client = audio_service_pb2_grpc.AudioGeneratorStub(self.audio_channel)
        logger.info(f"Connected to Audio Service at {audio_service_addr}")
        
        # Setup image service client (if provided)
        self.image_service_enabled = image_service_addr is not None
        if self.image_service_enabled:
            self.image_channel = grpc.insecure_channel(image_service_addr)
            self.image_client = image_service_pb2_grpc.ImageGeneratorStub(self.image_channel)
            logger.info(f"Connected to Image Service at {image_service_addr}")
        else:
            logger.info("Image Service is disabled")
    
    def generate_story(self, storyline: str, genre: str) -> dict:
        """
        Generate a story based on storyline and genre.
        
        Args:
            storyline: Brief description of the story
            genre: Genre of the story (e.g., fantasy, sci-fi)
            
        Returns:
            Dictionary with story text and success status
        """
        request = story_service_pb2.StoryRequest(storyline=storyline, genre=genre)
        try:
            response = self.story_client.GenerateStory(request)
            if response.success:
                logger.info("Story generated successfully")
                return {
                    "success": True,
                    "story": response.story
                }
            else:
                logger.error(f"Failed to generate story: {response.error}")
                return {
                    "success": False,
                    "error": response.error
                }
        except Exception as e:
            logger.error(f"Error calling story service: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_story_emotions(self, story: str) -> dict:
        """
        Process a story to get sentences with emotions.
        
        Args:
            story: The story text
            
        Returns:
            Dictionary with sentences and their emotions
        """
        request = story_service_pb2.ProcessRequest(story=story)
        try:
            response = self.story_client.ProcessStoryEmotions(request)
            if response.success:
                logger.info(f"Processed {len(response.sentences)} sentences with emotions")
                sentences = [
                    {"text": sentence.text, "emotion": sentence.emotion}
                    for sentence in response.sentences
                ]
                return {
                    "success": True,
                    "sentences": sentences
                }
            else:
                logger.error(f"Failed to process story emotions: {response.error}")
                return {
                    "success": False,
                    "error": response.error
                }
        except Exception as e:
            logger.error(f"Error calling process emotions: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_scene_prompts(self, story: str) -> dict:
        """
        Generate scene prompts for a story (for image generation).
        
        Args:
            story: The story text
            
        Returns:
            Dictionary with scene information and image prompts
        """
        if not self.image_service_enabled:
            logger.warning("Image service is disabled, skipping scene prompt generation")
            return {
                "success": False,
                "error": "Image service is disabled"
            }
        
        request = story_service_pb2.SceneRequest(story=story)
        try:
            response = self.story_client.GenerateScenePrompts(request)
            if response.success:
                logger.info(f"Generated {len(response.scenes)} scene prompts")
                scenes = [
                    {
                        "scene_number": scene.scene_number,
                        "start_line": scene.start_line,
                        "end_line": scene.end_line,
                        "image_prompt": scene.image_prompt
                    }
                    for scene in response.scenes
                ]
                return {
                    "success": True,
                    "scenes": scenes
                }
            else:
                logger.error(f"Failed to generate scene prompts: {response.error}")
                return {
                    "success": False,
                    "error": response.error
                }
        except Exception as e:
            logger.error(f"Error calling generate scene prompts: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_audio(self, sentences_with_emotions: List[Dict[str, str]]) -> dict:
        """
        Generate audio from sentences with emotions.
        
        Args:
            sentences_with_emotions: List of dicts with 'text' and 'emotion' keys
            
        Returns:
            Dictionary with path to generated audio file
        """
        # Convert dict to proto format
        segments = [
            audio_service_pb2.TextEmotion(text=item["text"], emotion=item["emotion"])
            for item in sentences_with_emotions
        ]
        
        request = audio_service_pb2.AudioRequest(segments=segments)
        try:
            response = self.audio_client.GenerateAudio(request)
            if response.success:
                logger.info(f"Audio generated successfully: {response.audio_file_path}")
                return {
                    "success": True,
                    "audio_file_path": response.audio_file_path
                }
            else:
                logger.error(f"Failed to generate audio: {response.error}")
                return {
                    "success": False,
                    "error": response.error
                }
        except Exception as e:
            logger.error(f"Error calling audio service: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_images(self, scenes: List[Dict]) -> dict:
        """
        Generate images for scenes based on prompts.
        
        Args:
            scenes: List of scene information with prompts
            
        Returns:
            Dictionary with paths to generated image files
        """
        if not self.image_service_enabled:
            logger.warning("Image service is disabled, skipping image generation")
            return {
                "success": False,
                "error": "Image service is disabled"
            }
        
        # Convert dict to proto format
        scene_prompts = [
            image_service_pb2.ScenePrompt(
                scene_number=scene["scene_number"],
                image_prompt=scene["image_prompt"]
            )
            for scene in scenes
        ]
        
        request = image_service_pb2.ImageRequest(scenes=scene_prompts)
        try:
            response = self.image_client.GenerateImages(request)
            if response.success:
                logger.info(f"Generated {len(response.images)} images")
                images = [
                    {
                        "scene_number": image.scene_number,
                        "image_path": image.image_path
                    }
                    for image in response.images
                ]
                return {
                    "success": True,
                    "images": images
                }
            else:
                logger.error(f"Failed to generate images: {response.error}")
                return {
                    "success": False,
                    "error": response.error
                }
        except Exception as e:
            logger.error(f"Error calling image service: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def close(self):
        """Close all gRPC channel connections."""
        self.story_channel.close()
        self.audio_channel.close()
        if self.image_service_enabled:
            self.image_channel.close()
        logger.info("All service connections closed")