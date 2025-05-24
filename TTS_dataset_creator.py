from LLM import ChatBot
import sounddevice as sd
import soundfile as sf
import keyboard
import numpy
import queue, threading, time, itertools, sys
from pathlib import Path

SAMPLERATE = 48_000
CHANNELS = 1
BLOCKSIZE = 2048
FMT = 'PCM_16'

audio_q = queue.Queue()
is_record = threading.Event()
stop_flag = threading.Event()
skip_flag = threading.Event()


def flip(event: threading.Event):
    if event.is_set():
        event.clear()
    else:
        event.set()


def audio_callback(indata, frames, time_info, status):
    if status:
        print(status, file = sys.stderr)
    if is_record.is_set():
        audio_q.put(indata.copy())

def writer_thread(LLM: ChatBot, datasetName):
    file_index = itertools.count(1)
    metadata = Path(datasetName+"/metadata.txt")
    out_file = None
    curr_name = None
    curr_text = None
    print('Begin Dataset Creation')
    while not stop_flag.is_set():
        if skip_flag.is_set():
            generated_text = LLM.generate_text('Generate a random sentence. Completly change topics every time.')
            try:
                #curr_text = generated_text.split('"')[1]
                curr_text = generated_text
            except IndexError:
                curr_text = generated_text.strip()
            print(curr_text)
            skip_flag.clear()

        if is_record.is_set() and out_file is None:
            curr_name = f'audio{next(file_index)}'
            out_file = sf.SoundFile(datasetName+"/wavs/"+curr_name+'.wav', mode='w',
                                   samplerate=SAMPLERATE,
                                   channels=CHANNELS,
                                   subtype=FMT)
            print(f"⏺  Recording → {curr_name}")
        try:
            data = audio_q.get(timeout=0.1)
        except queue.Empty:
            if not is_record.is_set() and out_file is not None:
                out_file.close()
                out_file = None
                if curr_name and curr_text:
                    with metadata.open('a', encoding = 'utf-8') as m:
                        line = f"{curr_name}|{curr_text}|{curr_text}\n"
                        m.write(line)
                print("⏹️  Saved.")
                out_file = None
                curr_name = None
                curr_text = None
                skip_flag.set()
            continue

        if out_file:
            out_file.write(data)
    if out_file:
        out_file.close()
        if curr_name and curr_text:
            with metadata.open('a', encoding='utf-8') as m:
                m.write(f"{curr_name}|{curr_text}|{curr_text}")

def main():
    datasetName = 'TTSDataset'
    root = Path(datasetName)/'wavs'
    root.mkdir(parents=True, exist_ok=True)
    print('Dataset Path Created')
    llm_kwargs = {
        'hf_token': None,
        'LLM_model_id': "meta-llama/Llama-3.2-1B-Instruct",
        'system_message': 'Only generate a single random sentence.',
        'max_generation_tokens': 256,
        'max_context_window': 5
    }
    chatbot = ChatBot(**llm_kwargs)
    print('Chatbot loaded')

    INPUT_ID = 2 #Change to your desired input device
    sd.check_input_settings(
        device=INPUT_ID, samplerate=SAMPLERATE, channels=CHANNELS, dtype='int16'
    )


    print("Press  R  to toggle recording,  Q  to quit, S to regenerate sentence")
    t = threading.Thread(target=writer_thread, daemon=True, args=(chatbot,datasetName, ))
    t.start()
    skip_flag.set()

    with sd.InputStream(device = INPUT_ID,
                        samplerate=SAMPLERATE,
                        blocksize=BLOCKSIZE,
                        channels=CHANNELS,
                        callback=audio_callback):
        keyboard.add_hotkey('r', lambda: flip(is_record))
        keyboard.add_hotkey('s', lambda: skip_flag.set())
        keyboard.wait('q')            # blocks until Q pressed
        stop_flag.set()               # tell writer to finish
        print("Exiting …")

if __name__ == "__main__":
    main()