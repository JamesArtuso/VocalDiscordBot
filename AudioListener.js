const net = require('net');
const { EventEmitter } = require('events');

class AudioListener extends EventEmitter {
    constructor(pipeName = "\\\\.\\pipe\\discord_response") {
        super();
        this.pipeName = pipeName;
        this.server = null;
    }

    start() {
        try {
            require('fs').unlinkSync(this.pipeName);
        } catch (error) {
            // Ignore error if pipe doesn't exist
        }

        this.server = net.createServer();
        this.server.listen(this.pipeName, () => {
            console.log("📡 Listening for Python responses on", this.pipeName);
        });

        this.server.on("connection", (sock) => {
            let lenBuf = Buffer.alloc(0);
            let wavBuf = Buffer.alloc(0);
            let expected = null;

            sock.on("data", (chunk) => {
                let offset = 0;
                while (offset < chunk.length) {
                    if (expected === null) {
                        // Accumulate 4‑byte length header
                        const needed = 4 - lenBuf.length;
                        lenBuf = Buffer.concat([lenBuf, chunk.slice(offset, offset + needed)]);
                        offset += needed;
                        if (lenBuf.length === 4) {
                            expected = lenBuf.readUInt32BE(0);
                            lenBuf = Buffer.alloc(0);
                        }
                    } else {
                        const toCopy = Math.min(expected - wavBuf.length, chunk.length - offset);
                        wavBuf = Buffer.concat([wavBuf, chunk.slice(offset, offset + toCopy)]);
                        offset += toCopy;
                        if (wavBuf.length === expected) {
                            // Emit the received audio data
                            this.emit('audio', wavBuf);
                            expected = null;
                            wavBuf = Buffer.alloc(0);
                        }
                    }
                }
            });
        });
    }

    stop() {
        if (this.server) {
            this.server.close();
            this.server = null;
        }
    }
}

module.exports = AudioListener; 