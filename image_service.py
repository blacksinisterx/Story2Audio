import grpc
import time
import os
import uuid
from concurrent import futures
from proto_files import image_service_pb2
from proto_files import image_service_pb2_grpc
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler


# This is a mock image generation service. In a real implementation,
# you would integrate with a proper text-to-image API like DALL-E or Stable Diffusion
class ImageGenerator:
    def __init__(self):
        self.pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5")

        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(self.pipe.scheduler.config)

        self.pipe = self.pipe.to("cuda")
        self.pipe.enable_attention_slicing()
        os.makedirs("generated_images", exist_ok=True)
    
    
    def generate_image(self, prompt):       
        image = self.pipe(prompt).images[0]


class ImageGeneratorServicer(image_service_pb2_grpc.ImageGeneratorServicer):
    def __init__(self):
        self.image_generator = ImageGenerator()
    
    def GenerateImages(self, request, context):
        print(f"Received request to generate images for {len(request.scenes)} scenes")
        
        generated_images = []
        
        # Process each scene prompt
        for i, scene in enumerate(request.scenes):
            prompt = scene.prompt
            start_line = scene.start_line
            end_line = scene.end_line
            
            print(f"Generating image for scene {i+1} (lines {start_line}-{end_line})")
            
            # Generate image for this scene
            image_path = self.image_generator.generate_image(prompt)
            
            # Add to our list of generated images
            generated_images.append(image_service_pb2.GeneratedImage(
                scene_index=i,
                image_file_path=image_path
            ))
        
        return image_service_pb2.ImageResponse(images=generated_images)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    image_service_pb2_grpc.add_ImageGeneratorServicer_to_server(
        ImageGeneratorServicer(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    print("Image Generator Server started on port 50053...")
    try:
        while True:
            time.sleep(86400)  # One day in seconds
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()