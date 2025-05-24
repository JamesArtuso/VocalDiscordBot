from AudioProcessing.AudioReceiver import AudioReceiver
from AudioProcessing.AudioProcessor import AudioProcessor
from AudioProcessing.AudioSender import AudioSender


class PipelinePlanner:
    """
    Centralized object to interact with Discord bot. Handles audio processing pipeline.
    """

    def __init__(self, **kwargs):
        self.processor = AudioProcessor(**kwargs)
        self.sender = AudioSender()
        self.processor.set_output_callback(self.sender.send)
        self.receiver = AudioReceiver(on_audio_callback=self.processor.add_audio)

    def start(self):
        self.receiver.start()


if __name__ == "__main__":
    #This should not work. Starting process moved to start.py
    try:
        planner = PipelinePlanner()
        planner.start()
    except KeyboardInterrupt:
        print("\nExiting …")