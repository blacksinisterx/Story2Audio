from voice_cloning.utils import *
from voice_cloning.api import F5TTS

model_type = "F5-TTS" 
f5tts = F5TTS(  
        model_type = model_type,                                                                                         # working 215
        ckpt_file= f"voice_cloning\ckpts\F5_TTS\model_1200000.safetensors",
        vocab_file="voice_cloning\\vocab\\vocab.txt"
                )

script = "As he looked out at the vast, complicated future stretching before him, Elias understood that the greatest threat to temporal stability wasn’t the unpredictable nature of the past, but the anxieties of the present"
audio_path = 'output_calm.wav'
wav, sr, spect = f5tts.infer(
                    ref_file="reference_audios\\emotions\\calm.wav",
                    ref_text="",
                    gen_text=script,
                    file_wave=audio_path,
                    # file_spect=spect_path,
                    speed = 1,
                    seed=-1  # Random seed
                )