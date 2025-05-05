import grpc
import time
from concurrent import futures
from proto_files import story_service_pb2
from proto_files import story_service_pb2_grpc
from utils.llm import OllamaModel

class StoryGeneratorServicer(story_service_pb2_grpc.StoryGeneratorServicer):
    def __init__(self):
        self.generator_llm = OllamaModel(model_name="gemma3:4b-it-qat")
        self.story_breakerLM = OllamaModel(model_name="gemma3:4b-it-qat")
        self.scene_prompt_makerLM = OllamaModel(model_name="gemma3:4b-it-qat")
        self.generator_llm.create_assistant("You are a story generator. Generate stories sync to genre and donot exceed length limit")
        
    def GenerateStory(self, request, context):
        print(f"Received request to generate a {request.genre} story with storyline: {request.storyline}")        
        prompt = f"""
        Generate a compelling {request.genre} story based on the following storyline:
        
        {request.storyline}
        
        The story should have a clear beginning, middle, and end. Be creative but stay within the {request.genre} genre.
        CRITICAL: DONT EXCEED 100 WORDS
        CRITICAL: DONOT ADD ANY OTHER LINE THAN STORY IN THE RESPONSE. MEAN THE RESPONSE SHOULD JUST BE THE STORY
        NO STARTING OR ENDING STATEMENTS LIKE "HERE IS THE STORY..."
        """        
        story = self.generator_llm.generate_response(prompt)
        
        return story_service_pb2.StoryResponse(story=story)
    
    def ProcessStoryEmotions(self, request, context):
        print(f"Received request to break story into sentences with emotions")
        
        prompt = f"""
        Below is a story. Break it down into individual sentences and assign an appropriate emotion to each sentence.
        Return the result as a list of sentences with their corresponding emotions.
        Format each line as: "Sentence: [sentence text] | Emotion: [emotion]"
        Emotions should only be the following [angry,calm,disgust,feat,happy,neutral,sad,surprise]
        CRITICAL: DONOT ADD ANY OTHER LINE THAN THE RESPONSE. MEAN THE RESPONSE SHOULD JUST BE THE ABOVE FORMAT
        NO STARTING OR ENDING STATEMENTS LIKE "HERE IS THE STORY...
        Story:
        {request.story}
        """
        
        result = self.story_breakerLM.generate_response(prompt)
        
        # Parse the response into sentence-emotion pairs
        temp_sentences = []
        for line in result.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) == 2:
                    sentence_part = parts[0].strip()
                    emotion_part = parts[1].strip()
                    
                    # Extract the actual sentence and emotion
                    sentence = sentence_part.replace("Sentence:", "").strip()
                    emotion = emotion_part.replace("Emotion:", "").strip()
                    
                    if sentence and emotion:
                        temp_sentences.append(story_service_pb2.SentenceEmotion(
                            text=sentence,
                            emotion=emotion
                        ))
        merged_sentences = []
        print("Merging redundant ones")
        if temp_sentences:
            current_group = temp_sentences[0]
            
            for i in range(1, len(temp_sentences)):
                print("here")
                current_sentence = temp_sentences[i]
                print(f"current sentence {current_sentence}")
                # If this sentence has the same emotion as our current group
                if current_sentence.emotion == current_group.emotion:
                    # Merge the texts with appropriate spacing/punctuation
                    last_char = current_group.text[-1] if current_group.text else ""
                    if last_char in ['.', '!', '?', ':', ';']:
                        current_group.text += " " + current_sentence.text
                    else:
                        # Add a period if needed before joining
                        current_group.text += ". " + current_sentence.text
                else:
                    # Different emotion, add the current group to our results
                    merged_sentences.append(story_service_pb2.SentenceEmotion(
                        text=current_group.text,
                        emotion=current_group.emotion
                    ))
                    # Start a new group with this sentence
                    current_group = current_sentence
        
              # Don't forget to add the last group
            merged_sentences.append(story_service_pb2.SentenceEmotion(
                text=current_group.text,
                emotion=current_group.emotion
            ))
    
        print("Original sentence count:", len(temp_sentences))
        print("Merged sentence count:", len(merged_sentences))
        
        for i, sentence in enumerate(merged_sentences):
            print(f"Merged {i+1}: {sentence.text} | {sentence.emotion}")
        
        return story_service_pb2.ProcessResponse(sentences=merged_sentences, success=1, error='none')

    
    def GenerateScenePrompts(self, request, context):
        print(f"Received request to generate scene prompts")
        
        prompt = f"""
        Below is a story with a total audio duration of {request.audio_duration} seconds. Divide it into distinct scenes (around 3-5 scenes) and for each scene create an image prompt that captures the visual essence of that scene.
        For each scene, specify the time ranges in seconds that the scene covers and provide a detailed image prompt.
        The entire story runs from 0 seconds to {request.audio_duration} seconds. Divide the duration based on the length and content of the story sections.
        Format:
        
        Scene 1 (Duration 0-X seconds):
        Image prompt: [detailed description for image generation]
        
        Scene 2 (Duration X+1-Y seconds):
        Image prompt: [detailed description for image generation]
        
        And so on.
        CRITICAL: DO NOT ADD ANY OTHER LINE THAN ABOVE FORMAT IN THE RESPONSE. MEAN THE RESPONSE SHOULD JUST BE THE FORMAT ABOVE
        NO STARTING OR ENDING STATEMENTS LIKE "HERE IS THE STORY...
        Story:
        {request.story}
        """
        
        result = self.scene_prompt_makerLM.generate_response(prompt)
        
        # Parse the response to extract scenes
        scenes = []
        current_scene = None
        i=0
        for line in result.strip().split('\n'):
            line = line.strip()
            
            # Check if this is a scene header
            if line.startswith("Scene ") and "Duration" in line:
                i+=1
                try:
                    # Extract durations from the header (Scene X (Duration A-B seconds):)
                    duration_range = line.split("(Duration ")[1].split(" seconds)")[0]
                    start_line, end_line = map(float, duration_range.split("-"))
                    
                    current_scene = {
                        "start_line": start_line,  # keeping variable name but it represents start_duration
                        "end_line": end_line,      # keeping variable name but it represents end_duration
                        "prompt": ""
                    }
                except Exception as e:
                    print(f"Error parsing scene header: {e}")
                    continue
            
            # Check if this is an image prompt line
            elif line.startswith("Image prompt:") and current_scene is not None:
                prompt_text = line.replace("Image prompt:", "").strip()
                current_scene["prompt"] = prompt_text
                
                # Add the complete scene to our list
                scenes.append(story_service_pb2.ScenePrompt(
                    scene_number = i,
                    start_line=current_scene["start_line"],  # now represents start_duration in seconds
                    end_line=current_scene["end_line"],      # now represents end_duration in seconds
                    image_prompt=current_scene["prompt"]
                ))
                current_scene = None
            
            # If we're already collecting a prompt, add to it
            elif current_scene is not None and "prompt" in current_scene and current_scene["prompt"]:
                current_scene["prompt"] += " " + line
        
        return story_service_pb2.SceneResponse(scenes=scenes,sucess=1,error='none')


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    story_service_pb2_grpc.add_StoryGeneratorServicer_to_server(
        StoryGeneratorServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Story Generator Server started on port 50051...")
    try:
        while True:
            time.sleep(86400)  # One day in seconds
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()