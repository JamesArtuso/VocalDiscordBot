import win32file, struct

class AudioSender:
    def __init__(self, pipe_name=r"\\.\pipe\discord_response"):
        self.pipe_name = pipe_name

    def send(self, audio_bytes: bytes):
        try:
            print("🔄 Connecting to response pipe...")
            pipe = win32file.CreateFile(
                self.pipe_name,
                win32file.GENERIC_WRITE,
                0, None,
                win32file.OPEN_EXISTING,
                0, None
            )

            size_hdr = struct.pack('!I', len(audio_bytes))
            print(f'Wav Lenght: {len(audio_bytes)}')
            win32file.WriteFile(pipe, size_hdr + audio_bytes)
            win32file.CloseHandle(pipe)
            print("✅ AudioSender sent response.")
        except Exception as e:
            print("❌ AudioSender error:", e)
