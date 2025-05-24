from LLM import ChatBot
from text_to_speech import VoiceBox
from scipy.io.wavfile import write

class DiscordAIAgent():
    '''
    Its a knick-knack, Patty Whack,
    Give that llama a voice!
    '''
    def __init__(self, **kwargs):
        llm_kwargs = {
            'LLM_model_id': kwargs['LLM_model_id'],
            'hf_token': kwargs['hf_token'],
            'system_message': kwargs['system_message'],
            'max_generation_tokens': kwargs['max_generation_tokens'],
            'max_context_window': kwargs['max_context_window']
        }
        
        tts_kwargs = {
            'speaker_path': kwargs['speaker_path'],
        }
        
        print('Loading Chatbot')
        self.chatbot = ChatBot(**llm_kwargs)
        
        print('Loading Voicebox')
        self.voice = VoiceBox(**tts_kwargs)
    
    def generate_voice_response(self, txt):
        print("Starting response")
        response = self.chatbot.generate_text(txt)
        response = self.voice.generate_audio(response)
        #output_file_path = f'output_audio.wav'
        #write(output_file_path, 24000, response)
        print('Ending Response')
        return response