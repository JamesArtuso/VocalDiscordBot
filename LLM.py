import torch
from transformers import pipeline
from collections import deque
from huggingface_hub import login

class ChatContext():
    def __init__(self, context, max_context_window = 20):
        self.MAX_CONTEXT_WINDOW = max_context_window
        self._first = {'role':'system', 'content': context}
        self.messages = deque(maxlen = self.MAX_CONTEXT_WINDOW)

    def add_text(self, role: str, txt:str):
        self.messages.append({'role': role, 'content': txt})
    
    def remind(self):
        self.messages.append(self._first)

    def pop_oldest(self):
        return self.messages.popleft()
    
    def __len__(self):
        return 1 + len(self.messages)
    def to_list(self):
        items = [self._first, *self.messages]
        return items
    def generate_prompt(self):
        items = [self._first, *self.messages]
        returnString = ''
        for i in items:
            returnString = returnString + '<|'+i['role']+'|>\n' + i['content'] + '\n'
        return returnString + '<|assistant|>'
            


class ChatBot():
    def __init__(self, **kwargs):
        # Extract LLM-specific kwargs
        self.model_id = kwargs['LLM_model_id']
        self.hf_token = kwargs['hf_token']
        self.system_message = kwargs['system_message']
        self.max_generation_length = kwargs['max_generation_tokens']
        self.max_context_window = kwargs['max_context_window']
        
        # Initialize the LLM pipeline
        if self.hf_token:
            self.LLM = pipeline(
                "text-generation", 
                model=self.model_id, 
                torch_dtype=torch.bfloat16, 
                device_map="cuda",
                token=self.hf_token
            )
        else:
            self.LLM = pipeline(
                "text-generation", 
                model=self.model_id, 
                torch_dtype=torch.bfloat16, 
                device_map="cuda"
            )
            
        # Initialize chat context
        self.context = ChatContext(
            context=self.system_message, 
            max_context_window=self.max_context_window
        )

    def generate_text(self, txt):
        self.context.add_text(role='user', txt=txt)
        outputs = self.LLM(
            self.context.to_list(), 
            max_new_tokens=self.max_generation_length, 
            do_sample=True, 
            temperature=0.7, 
            top_k=50, 
            top_p=0.95, 
            pad_token_id=self.LLM.tokenizer.eos_token_id
        )
        return outputs[0]['generated_text'][-1]['content']


    
    
    
if __name__ == "__main__":
    model_id = "meta-llama/Llama-3.2-1B-Instruct"
    hf_token = None #Insert your token here
    login(token=hf_token)
    chatbot = ChatBot(model_id=model_id, hf_token=hf_token, system_message='You are a having a casual conversation. Never say you are an AI. Keep reply to one to three sentences.', max_generation_tokens=256, max_context_window=20)
    print("Hello, I am the test ChatBot, here is my initalization context:")
    print(chatbot.context._first)
    while True:
        txt = input('Your Message: ')
        print('')
        if(txt.lower() == 'q'):
            break
        result = chatbot.generate_text(txt)
        print('Chatbot: ' + result)
        print('')