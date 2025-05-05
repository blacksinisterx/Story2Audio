import grpc
import time
import os
import uuid
from concurrent import futures
from proto_files import  audio_service_pb2
from proto_files import  audio_service_pb2_grpc
from pydub import AudioSegment
import tempfile
from voice_cloning.utils import *
from voice_cloning.api import F5TTS
from utils.utils import *
import datetime



class AudioGeneratorServicer(audio_service_pb2_grpc.AudioGeneratorServicer):
    def __init__(self,refernce_audio_folder,output_folder):
        model_type = "F5-TTS" 
        self.refernce_audio_folder = refernce_audio_folder
        self.f5tts =F5TTS(  
                            model_type = "F5-TTS",                                                                                         # working 215
                            ckpt_file= f"voice_cloning\ckpts\F5_TTS\model_1200000.safetensors",
                            vocab_file="voice_cloning\\vocab\\vocab.txt"
                        )
        self.output_dir = output_folder
        self.emotion_files = get_files_with_extension(refernce_audio_folder,'wav')
        self.emotion_files_dict = {}
     
    
    def make_key_file_pairs(self):
        for file in self.emotion_files:
            filename = os.path.basename(file)
            base_name = os.path.splitext(filename)[0]
            self.emotion_files_dict[base_name] = file
        print("Emotion files dictionary: ",self.emotion_files_dict)

    # def generate_objects(self):
    #     self.f5tts_objects ={}
    #     for i,file_name in enumerate(self.emotion_files):
    #         filename = os.path.basename(file_name)
    #         base_name = filename.split('.')[0]
    #         print(f"File name  {base_name}")
    #         self.f5tts_objects[base_name] =
            
    

    def audio_generator(self,emotion,text_to_gen,output_path):
        print("F5tts object ")
        wav, sr, spect = self.f5tts.infer(
                    ref_file=self.emotion_files_dict[emotion],
                    ref_text="",
                    gen_text=text_to_gen,
                    file_wave=output_path,
                    # file_spect=spect_path,
                    speed = 0.8,
                    seed=-1  # Random seed
                )
        print("Audio generated successfully")

    def merge_audio_files(self,audio_files, output_file):
        for file in audio_files:
            if not os.path.exists(file):
                raise FileNotFoundError(f"Audio file not found: {file}")
        
        # Validate output file extension
        supported_formats = ['mp3', 'wav', 'ogg', 'flac']
        output_ext = os.path.splitext(output_file)[1].lower().lstrip('.')
        if output_ext not in supported_formats:
            raise ValueError(f"Unsupported output format: {output_ext}. Supported formats: {supported_formats}")

        try:
            # Initialize an empty AudioSegment
            merged_audio = AudioSegment.empty()
            
            # Read and append each audio file in order
            for file in audio_files:
                audio = AudioSegment.from_file(file)
                merged_audio += audio
            
            # Export the merged audio to the output file
            merged_audio.export(output_file, format=output_ext)
            return True
        
        except Exception as e:
            print(f"Error merging audio files: {e}")
            return False
    def GenerateAudio(self, request, context):
        print(f"Received request to generate audio for {len(request.segments)} sentences")
        
        # Create a unique file name for this audio
        audio_file_name = f"story_{uuid.uuid4().hex}.mp3"
        audio_file_path = os.path.join("generated_audio", audio_file_name)
        
        combined_audio = AudioSegment.silent(duration=0)
        # self.generate_objects()
        self.make_key_file_pairs()
        # Process each sentence with its emotion
        i=0
        all_outputs = []
        for pair in request.segments:
            sentence = pair.text
            emotion = pair.emotion.lower()
            print("Sentence: ",sentence,"\n Emotion ",emotion)
            output_path = os.path.join(self.output_dir,f"{str(i)}.wav")
            all_outputs.append(output_path)
            print(f"Generating audio {output_path}")
            self.audio_generator(emotion,sentence,output_path)
            i+=1
        #     pause = AudioSegment.silent(duration=500)
            
        #     # Append to our combined audio
        #     combined_audio += audio_segment + pause

        # # Export the combined audio to a file
        date_dir = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H%M%S")
        final_output = f'{date_dir}/story_generated_{timestamp}.wav'
        self.merge_audio_files(all_outputs,final_output)
        
        print(f"Audio generated and saved to {final_output}")
        return audio_service_pb2.AudioResponse(audio_file_path=final_output,success=1,error='None')


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    reference_audio_folder = f"reference_audios\\emotion"
    output_dir = "output_audios"
    os.makedirs(output_dir,exist_ok=True)
    audio_service_pb2_grpc.add_AudioGeneratorServicer_to_server(
        AudioGeneratorServicer(reference_audio_folder,output_dir), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("Audio Generator Server started on port 50052...")
    try:
        while True:
            time.sleep(86400)  # One day in seconds
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()