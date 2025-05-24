from TTS.tts.models.xtts import XttsAudioConfig
from TTS.tts.models.xtts import XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from torch.serialization import add_safe_globals
from scipy.io.wavfile import write
from os import listdir
from os.path import isfile, join


#Required due to torch >= 2.6.x
add_safe_globals({
    BaseDatasetConfig,
    XttsAudioConfig,
    XttsConfig,
    XttsArgs
})


class VoiceBox():
    def __init__(self, **kwargs):

        self.speaker_path = kwargs['speaker_path']
        
        self.config = XttsConfig()
        self.config.load_json("./XTTS-v2/config.json")
        self.model = Xtts.init_from_config(self.config)
        self.model.load_checkpoint(self.config, checkpoint_dir="./XTTS-v2/", eval=True)
        self.model.cuda()
        
        '''Expected dataset format
            speaker_path\wav1.wav
            speaker_path\wav1.wav
        
        '''
        onlyfiles = [f for f in listdir(self.speaker_path) if isfile(join(self.speaker_path, f))]
        mypaths = [self.speaker_path +'\\' + f for f in onlyfiles]
        self.mypaths = mypaths

    def generate_audio(self, text):
        outputs = self.model.synthesize(
            text,
            self.config,
            speaker_wav=self.mypaths,
            gpt_cond_len=3,
            language="en"
        )
        return outputs['wav']

if __name__ == '__main__':
    # Test configuration
    test_kwargs = {
        'speaker_path': r'voices\ariana',
    }
    
    voiceCreator = VoiceBox(**test_kwargs)
    outputAudio = voiceCreator.generate_audio("Hello World! I finally have a voice!")
    
    # Save the output audio to a file using scipy.io.wavfile.write
    write('output.wav', 24000, outputAudio)
    
    print("Audio has been saved to 'output.wav'")
    