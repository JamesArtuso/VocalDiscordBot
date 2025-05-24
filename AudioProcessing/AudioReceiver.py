import win32pipe, win32file, struct

class AudioReceiver:
    def __init__(self, on_audio_callback, pipe_name=r"\\.\pipe\discord_audio"):
        self.pipe_name = pipe_name
        self.on_audio_callback = on_audio_callback

    def _read_exact(self, handle, n):
        data = bytearray()
        while len(data) < n:
            try:
                chunk = win32file.ReadFile(handle, n - len(data))[1]
            except win32file.error:
                return None
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)

    def start(self):
        print("Waiting for Discord audio on", self.pipe_name)
        while True:
            pipe = win32pipe.CreateNamedPipe(
                self.pipe_name,
                win32pipe.PIPE_ACCESS_INBOUND,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                1, 65536, 65536, 0, None)

            try:
                win32pipe.ConnectNamedPipe(pipe, None)
                print("Client connected ✔")

                while True:
                    size_hdr = self._read_exact(pipe, 4)
                    if size_hdr is None:
                        break
                    (size,) = struct.unpack('!I', size_hdr)
                    audio_bytes = self._read_exact(pipe, size)
                    if audio_bytes is None:
                        break
                    self.on_audio_callback(audio_bytes)

            except Exception as e:
                print("Pipe error:", e)

            finally:
                try:
                    win32file.CloseHandle(pipe)
                except:
                    pass
                print("Client disconnected")