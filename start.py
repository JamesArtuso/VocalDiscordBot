import argparse
from PipelinePlanner import PipelinePlanner

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Discord Vocal Chatbot", add_help = True)
    
    # HuggingFace arguments
    parser.add_argument('--hf_token', help='Huggingface token. Leave empty if you are already logged in.',default=None)
    parser.add_argument('--LLM_model_id', help='Language model from Huggingface', default="meta-llama/Llama-3.2-1B-Instruct")
    parser.add_argument('--system_message', help='Initial system prompt for the LLM.', default = 'You are a helpful chatbot. You have been given a voice and are talking in Discord. You should respond as if you are in a conversation. Keep responses short.')
    parser.add_argument('--max_generation_tokens', help = 'Max number of tokens the LLM can generate.', default = 256)
    parser.add_argument('--max_context_window', help = 'Number of previous messages to remember. Includes initial context, user input, and bot responses. This is NOT the number of tokens.', default = 20)
    
    # Whisper arguments
    parser.add_argument('--whisper_model', help = 'Which OpenAI Whisper model to use. https://github.com/openai/whisper', default = 'base.en')
    
    # TTS arguments
    parser.add_argument('--speaker_path', help='TTS speaker sample. Put all .wav files in folder and pass path to folder. ie "voices\person1\sample1.wav" would pass as "voices\person1"', default = r'voices\vader')
    args = parser.parse_args()
    
    # Organize kwargs by module
    llm_kwargs = {
        'hf_token': args.hf_token,
        'LLM_model_id': args.LLM_model_id,
        'system_message': args.system_message,
        'max_generation_tokens': int(args.max_generation_tokens),
        'max_context_window': int(args.max_context_window)
    }
    
    whisper_kwargs = {
        'whisper_model': args.whisper_model
    }
    
    tts_kwargs = {
        'speaker_path': args.speaker_path,
    }
    
    # Combine all kwargs for the pipeline
    pipeline_kwargs = {
        **llm_kwargs,
        **whisper_kwargs,
        **tts_kwargs
    }
    
    # Initialize pipeline
    pipeline = PipelinePlanner(**pipeline_kwargs)
    pipeline.start()
