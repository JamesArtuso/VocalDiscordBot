const fs = require('fs');

class AudioSender {
    constructor(pipeName = "\\\\.\\pipe\\discord_audio") {
        this.pipeName = pipeName;
        this.pipeHandle = null;
        this.connected = false;
    }

    connect() {
        if (!this.connected) {
            try {
                this.pipeHandle = fs.openSync(this.pipeName, "w");
                this.connected = true;
                console.log("📤 Connected to Python audio pipe");
            } catch (error) {
                console.error("Failed to connect to Python pipe:", error);
                setTimeout(() => this.connect(), 1000);
            }
        }
    }

    sendAudioData(data) {
        if (!this.connected) {
            console.log("Not connected to Python process");
            return;
        }

        if (data === null) {
            // Send end marker as empty buffer
            console.log("Sending end marker to Python");
            const size = Buffer.alloc(4);
            size.writeUInt32BE(0, 0);  // size of 0 indicates end marker
            try {
                fs.writeSync(this.pipeHandle, size);
            } catch (error) {
                console.error("Failed to send end marker:", error);
            }
            return;
        }

        if (!data || data.length === 0) {
            console.log("Empty audio data, skipping");
            return;
        }

        try {
            const size = Buffer.alloc(4);
            size.writeUInt32BE(data.length, 0);
            fs.writeSync(this.pipeHandle, size);
            fs.writeSync(this.pipeHandle, data);
        } catch (error) {
            console.error("Failed to send audio data:", error);
            this.connected = false;
            try { fs.closeSync(this.pipeHandle); } catch {}
            setTimeout(() => this.connect(), 1000);
        }
    }

    close() {
        if (this.connected) {
            try {
                fs.closeSync(this.pipeHandle);
            } catch (error) {
                console.error("Error closing pipe:", error);
            }
            this.connected = false;
        }
    }
}

module.exports = AudioSender; 