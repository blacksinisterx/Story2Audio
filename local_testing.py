import grpc

from proto_files import story_service_pb2,audio_service_pb2
from proto_files import story_service_pb2_grpc,audio_service_pb2_grpc

# Connect to the server
channel = grpc.insecure_channel('localhost:50051')
stub = story_service_pb2_grpc.StoryGeneratorStub(channel)   #

audio_channel = grpc.insecure_channel('localhost:50052')
audio_stub = audio_service_pb2_grpc.AudioGeneratorStub(audio_channel)

# Test story generation
request = story_service_pb2.StoryRequest(       # 1st 1 request//input structure bnta hy like this jo proto file my define hoa va 
    genre="science fiction",
    storyline="A time traveler visits Earth"
)
print("generating story")
response = stub.GenerateStory(request)          #ya request jaati hy respective function my using stub jo ky class ka object hota jismy functions hoty
print(f"Generated Story:\n{response.story}")

# Test breaking into sentences with emotions
print("generating emotions")

break_request = story_service_pb2.ProcessRequest(story=response.story)       #we cant pass a direct argument to stub,function rather hum usko rpc format my convert krty
emotion_response = stub.ProcessStoryEmotions(break_request)           # jo hymny define kiya .proto my.. Also jo request wahan define ki hoi for this rpc. wohi
print("emotion response ",emotion_response)                           
                                                                # yahan chaly gi, else error. or rpc ka naam same hona must
print("\nSentences with emotions:")
for pair in emotion_response.sentences:
    print(f"Sentence: {pair.text}")
    print(f"Emotion: {pair.emotion}")


print("\nGenerating audio for emotional sentences")
# Prepare AudioRequest with TextEmotion segments
audio_request = audio_service_pb2.AudioRequest()

for pair in emotion_response.sentences:
    segment = audio_service_pb2.TextEmotion()
    segment.text = pair.text
    segment.emotion = pair.emotion
    audio_request.segments.append(segment)
    
    # Debug output to verify segments are being added
    print(f"Added segment - Text: {segment.text}, Emotion: {segment.emotion}")

# Print the number of segments in the request
print(f"Total segments in request: {len(audio_request.segments)}")


# Call AudioGenerator service
audio_response = audio_stub.GenerateAudio(audio_request)
if audio_response.success:
    print(f"Audio generated successfully: {audio_response.audio_file_path}")
else:
    print(f"Audio generation failed: {audio_response.error}")
# Test scene prompts
# print("generating scenes")

# scene_request = story_service_pb2.SceneRequest(story=response.story)
# scene_response = stub.GenerateScenePrompts(scene_request)


# print("\nScene prompts:")
# for scene in scene_response.scenes:
#     print(f"Scene (Lines {scene.start_line}-{scene.end_line}):")
#     print(f"Prompt: {scene.prompt}")