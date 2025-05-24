'''
TODO

 - Change the audio generation criteria
   - Currently it processes when discord VAD detects end of sentence
   - This is done by looking for an end of sentence packet from bot.js

 - Make smarter way to determine when to generate audio
'''

import os, queue, threading
import numpy as np
import torch, whisper
from scipy.signal import resample_poly
import time
from AIAgent import DiscordAIAgent
import io
import wave
import json
import base64



def numpy_audio_to_wav_bytes(audio: np.ndarray, sample_rate=24000) -> bytes:
    # Ensure it's mono float32 -> int16
    if audio.dtype != np.int16:
        audio = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)

    with io.BytesIO() as wav_io:
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
        return wav_io.getvalue()


class AudioProcessor:
    '''
    Transcribe streamed audio. Currently hard-coded to send processed text to AIAgent.
    '''
    def __init__(self, **kwargs):
        whisper_model = kwargs['whisper_model']

        print("Loading Whisper model …")
        model_dir = os.path.join(os.path.dirname(__file__), "whisper_models")
        os.makedirs(model_dir, exist_ok=True)
        self.model = whisper.load_model(whisper_model, download_root=model_dir)
        print("Whisper model ready ✔")

        self.GET_TIMEOUT = 0.05
        self.pause_evt = threading.Event()
        self.audio_queue = queue.Queue(maxsize=500)

        #Standard for Discord
        self.pipe_sr = 48_000
        self.pipe_channels = 2
        self.pipe_width = 2
        self.pipe_bps = self.pipe_width * self.pipe_channels
        self.chunk_bytes = 960 * self.pipe_bps

        self.window_frames = 2 * self.pipe_sr
        self.window_bytes = self.window_frames * self.pipe_bps
        self.buffer = bytearray()

        self.sent_buf = []

        self.output_callback = None

        self.worker = threading.Thread(target=self._process_audio, daemon=True)
        self.worker.start()

        self.AI = DiscordAIAgent(**kwargs)

    def set_output_callback(self, callback):
        self.output_callback = callback

    def _transcribe_bytes(self, pcm_bytes: bytes):
        if not pcm_bytes:
            return
        print(f"Transcribing {len(pcm_bytes)} bytes")
        pcm = np.frombuffer(pcm_bytes, np.int16).astype(np.float32)
        pcm = pcm.reshape(-1, self.pipe_channels).mean(1) / 32768.0
        pcm_16k = resample_poly(pcm, 1, 3)

        try:
            res = self.model.transcribe(pcm_16k, language="en", fp16=torch.cuda.is_available())
            txt = res["text"].strip()
            if txt:
                print(f"Transcribed: {txt}")
                self.sent_buf.append(txt)
        except Exception as e:
            print("Transcription error:", e)

    def _process_audio(self):
        print("Audio worker running …")
        while True:
            try:
                chunk = self.audio_queue.get(timeout=self.GET_TIMEOUT)
            except queue.Empty:
                continue

            if self.pause_evt.is_set():
                #print("Audio processor paused, dropping chunk")
                continue

            if chunk is None or len(chunk) == 0:
                print("Received end marker")
                if self.buffer:
                    print(f"Processing final buffer of size: {len(self.buffer)}")
                    self._transcribe_bytes(self.buffer)
                    self.buffer.clear()  # Clear buffer after processing
                    if self.sent_buf: #Need a way to see check if there has been silence.
                        self.pause()
                        sentence = " ".join(self.sent_buf)
                        print(f"Processing: {sentence}")
                        response_numpy = self.AI.generate_voice_response(sentence)
                        response_audio = numpy_audio_to_wav_bytes(response_numpy)
                        if self.output_callback:
                            self.output_callback(response_audio)
                        self.sent_buf.clear()
                        self.buffer.clear()  # Clear buffer again after response
                        self.resume()
                continue

            # Add chunk to buffer
            self.buffer.extend(chunk)
            #print(f"Buffer size after adding chunk: {len(self.buffer)}")

    def add_audio(self, chunk: bytes):
        if self.pause_evt.is_set():
            #print("Audio processor paused, dropping incoming chunk")
            return

        while True:
            try:
                self.audio_queue.put(chunk, block=False)
                return
            except queue.Full:
                print("Audio queue full, dropping oldest chunk")
                try:
                    _ = self.audio_queue.get_nowait()
                except queue.Empty:
                    pass

    def stop(self):
        self.add_audio(None)
        self.worker.join(timeout=2)

    def pause(self):
        self.pause_evt.set()
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        self.buffer.clear()
        print("🔇 AudioProcessor paused. Incoming chunks will be dropped.")

    def resume(self):
        self.pause_evt.clear()
        print("🎙️  AudioProcessor resumed.")
