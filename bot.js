//TODO: Clean this up. Better seperation of interaction with python.
// This way the interactive audio can just be one component of a larger bot
//TODO: Change to TCP connections instead
//TODO: Add more bot commands. 

const { Client, GatewayIntentBits, Partials } = require("discord.js");
const { joinVoiceChannel, createAudioPlayer, createAudioResource, StreamType } = require("@discordjs/voice");
const prism = require("prism-media");
const { Readable } = require("stream");
const AudioSender = require("./AudioSender");
const AudioListener = require("./AudioListener");
const fs = require("fs");
const TOKEN = '';//Insert your Discord bot token here


//const TOKEN = process.env.DISCORD_TOKEN;
//if (!TOKEN) {
//    console.error("Error: DISCORD_TOKEN environment variable is not set");
//    process.exit(1);
//}


const PREFIX = "!";
const CHUNK_SIZE = 960 * 4; // 20 ms of 48 kHz stereo s16le

class DiscordBot {
    constructor() {
        this.client = new Client({
            intents: [
                GatewayIntentBits.Guilds,
                GatewayIntentBits.GuildMessages,
                GatewayIntentBits.GuildVoiceStates,
                GatewayIntentBits.MessageContent,
            ],
            partials: [Partials.Channel],
        });

        this.audioSender = new AudioSender();
        this.audioListener = new AudioListener();
        this.connection = null;
        this.player = null;
        
        // Audio state management
        this.currentSpeaker = null;  // Current user ID being recorded
        this.isListening = false;    // Whether we're currently recording someone
        this.isSpeaking = false;     // Whether the bot is speaking
        this.currentPCM = null;      // Current PCM stream
        this.currentBuffer = null;   // Current audio buffer

        this.setupEventListeners();
    }

    setupEventListeners() {
        this.client.once("ready", () => {
            console.log(`🤖 Logged in as ${this.client.user.tag}`);
            this.audioListener.start();
            this.audioSender.connect();
        });

        this.client.on("messageCreate", this.handleMessage.bind(this));
        this.audioListener.on("audio", this.handleAudioResponse.bind(this));
    }

    async handleMessage(msg) {
        if (msg.author.bot || !msg.content.startsWith(PREFIX)) return;
        const [command, ...args] = msg.content.slice(PREFIX.length).trim().split(/ +/);

        switch (command) {
            case "join":
                await this.handleJoin(msg);
                break;
            case "leave":
                await this.handleLeave(msg);
                break;
            case "volume":
                await this.handleVolume(msg, args[0]);
                break;
        }
    }

    // Helper to check if we can start recording
    canStartRecording(uid) {
        if (this.isSpeaking) {
            console.log("Cannot record: Bot is speaking");
            return false;
        }
        if (this.isListening) {
            console.log("Cannot record: Already listening to someone else");
            return false;
        }
        return true;
    }

    // Helper to start recording a user
    startRecording(uid, rx) {
        if (!this.canStartRecording(uid)) return;

        console.log(`Starting to record user ${uid}`);
        this.isListening = true;
        this.currentSpeaker = uid;

        const opus = rx.subscribe(uid, { end: { behavior: "manual" } });
        const pcm = opus.pipe(new prism.opus.Decoder({ rate: 48000, channels: 2, frameSize: 960 }));
        
        let buf = Buffer.alloc(0);
        pcm.on("data", (c) => {
            // Check if bot is speaking before processing any audio
            if (this.isSpeaking) {
                console.log("Bot is speaking, dropping audio chunk");
                return;
            }
            
            // Double check speaking state before adding to buffer
            if (this.isSpeaking) {
                console.log("Bot started speaking while processing chunk, dropping");
                return;
            }
            
            buf = Buffer.concat([buf, c]);
            
            // Check speaking state again before processing chunks
            if (this.isSpeaking) {
                console.log("Bot started speaking while in buffer, clearing buffer");
                buf = Buffer.alloc(0);
                return;
            }
            
            while (buf.length >= CHUNK_SIZE) {
                // Final check before sending each chunk
                if (this.isSpeaking) {
                    console.log("Bot started speaking while sending chunks, stopping");
                    buf = Buffer.alloc(0);
                    return;
                }
                
                const chunk = buf.subarray(0, CHUNK_SIZE);
                buf = buf.subarray(CHUNK_SIZE);
                console.log("Sending audio chunk of size:", chunk.length);
                this.audioSender.sendAudioData(chunk);
            }
        });

        pcm.on("error", (error) => {
            console.error("PCM stream error:", error);
            this.stopRecording();
        });

        this.currentPCM = pcm;
        this.currentBuffer = buf;
    }

    // Helper to stop recording and process final audio
    stopRecording() {
        if (!this.isListening || !this.currentPCM) return;

        console.log("Stopping recording and processing final audio");
        
        // Only process final audio if bot is not speaking
        if (this.isSpeaking) {
            console.log("Bot is speaking, skipping final audio processing");
            // Just cleanup without sending any audio
            this.currentPCM.destroy();
            this.currentPCM = null;
            this.currentBuffer = Buffer.alloc(0);
            this.isListening = false;
            this.currentSpeaker = null;
            return;
        }
        
        // Process any remaining complete chunks
        let buf = this.currentBuffer;
        console.log("Final buffer size:", buf.length);
        
        while (buf.length >= CHUNK_SIZE) {
            // Check speaking state before each chunk
            if (this.isSpeaking) {
                console.log("Bot started speaking during final processing, stopping");
                buf = Buffer.alloc(0);
                break;
            }
            
            const chunk = buf.subarray(0, CHUNK_SIZE);
            buf = buf.subarray(CHUNK_SIZE);
            console.log("Sending final regular chunk of size:", chunk.length);
            this.audioSender.sendAudioData(chunk);
        }
        
        // Check speaking state before padding
        if (!this.isSpeaking && buf.length > 0) {
            console.log("Padding final chunk from size:", buf.length, "to:", CHUNK_SIZE);
            const paddedChunk = Buffer.concat([buf, Buffer.alloc(CHUNK_SIZE - buf.length, 0)]);
            this.audioSender.sendAudioData(paddedChunk);
        }

        // Only send end marker if not speaking
        if (!this.isSpeaking) {
            console.log("Sending end marker");
            this.audioSender.sendAudioData(null);
        }

        // Cleanup
        this.currentPCM.destroy();
        this.currentPCM = null;
        this.currentBuffer = Buffer.alloc(0);
        this.isListening = false;
        this.currentSpeaker = null;
        console.log("Recording stopped and cleaned up");
    }

    async handleAudioResponse(wavBytes) {
        if (!this.connection || !this.player) {
            console.log("⚠️ No VC to play in.");
            return;
        }

        try {
            // Stop recording if we are
            if (this.isListening) {
                console.log("Bot starting to speak, stopping current recording");
                this.stopRecording();
            }

            // Set speaking flag before any other operations
            this.isSpeaking = true;
            console.log("Bot speaking state set to true");
            
            // Small delay to ensure speaking state is set
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const convertedData = await this.testFFmpegConversion(wavBytes);
            if (convertedData.length === 0) {
                console.error("Cannot play audio: FFmpeg produced no output data");
                this.isSpeaking = false;
                return;
            }

            const pcmStream = Readable.from(convertedData);
            const resource = createAudioResource(pcmStream, {
                inputType: StreamType.Raw,
                inlineVolume: true
            });

            resource.volume.setVolume(1.0);
            this.player.setMaxListeners(20);

            // Remove any existing error and state change listeners
            this.player.removeAllListeners("error");
            this.player.removeAllListeners("stateChange");

            const errorHandler = (error) => {
                console.error("Player error:", error);
                this.isSpeaking = false;
                console.log("Bot speaking state set to false due to error");
                this.player.removeListener("error", errorHandler);
            };

            const stateChangeHandler = (oldState, newState) => {
                if (newState.status === "idle") {
                    this.isSpeaking = false;
                    console.log("Bot speaking state set to false (finished speaking)");
                    // Remove this listener after it's handled
                    this.player.removeListener("stateChange", stateChangeHandler);
                }
            };

            // Add the new listeners
            this.player.on("error", errorHandler);
            this.player.on("stateChange", stateChangeHandler);

            this.player.play(resource);

        } catch (error) {
            console.error("Error in audio processing:", error);
            this.isSpeaking = false;
            console.log("Bot speaking state set to false due to error");
        }
    }

    async handleJoin(msg) {
        const vc = msg.member.voice.channel;
        if (!vc) {
            return msg.reply("❌ Join a VC first.");
        }

        try {
            this.connection = joinVoiceChannel({
                channelId: vc.id,
                guildId: vc.guild.id,
                adapterCreator: vc.guild.voiceAdapterCreator,
                selfDeaf: false,
            });

            this.connection.on('error', (error) => {
                console.error('Voice connection error:', error);
                this.handleVoiceError(msg, error);
            });

            this.connection.on('stateChange', (oldState, newState) => {
                console.log(`Connection state changed from ${oldState.status} to ${newState.status}`);
                if (newState.status === 'disconnected') {
                    this.handleVoiceError(msg, new Error('Voice connection disconnected'));
                }
            });

            this.player = createAudioPlayer();
            this.connection.subscribe(this.player);

            const rx = this.connection.receiver;
            console.log("Voice receiver set up");

            rx.speaking.on("start", (uid) => {
                console.log(`User ${uid} started speaking`);
                this.startRecording(uid, rx);
            });

            rx.speaking.on("end", (uid) => {
                console.log(`User ${uid} stopped speaking`);
                if (uid === this.currentSpeaker) {
                    this.stopRecording();
                }
            });

            //msg.reply("🎧 Joined VC and ready.");
        } catch (error) {
            console.error('Error joining voice channel:', error);
            msg.reply("❌ Failed to join voice channel. Please try again.");
            this.cleanupVoiceConnection();
        }
    }

    handleVoiceError(msg, error) {
        console.error('Voice error occurred:', error);
        msg.reply("❌ Voice connection error. Reconnecting...");
        this.cleanupVoiceConnection();
        
        // Try to reconnect after a short delay
        setTimeout(() => {
            if (msg.member.voice.channel) {
                this.handleJoin(msg);
            }
        }, 2000);
    }

    cleanupVoiceConnection() {
        if (this.connection) {
            try {
                this.connection.destroy();
            } catch (error) {
                console.error('Error destroying connection:', error);
            }
        }
        this.connection = null;
        this.player = null;
        this.isListening = false;
        this.isSpeaking = false;
        this.currentSpeaker = null;
        this.currentPCM = null;
        this.currentBuffer = Buffer.alloc(0);
    }

    async handleLeave(msg) {
        if (!this.connection) {
            return msg.reply("❌ Not in VC.");
        }

        this.cleanupVoiceConnection();
        msg.reply("👋 Left VC.");
    }

    async handleVolume(msg, volume) {
        if (!this.player) {
            return msg.reply("❌ Bot is not in a voice channel.");
        }

        const newVolume = parseFloat(volume);
        if (isNaN(newVolume) || newVolume < 0 || newVolume > 2) {
            return msg.reply("❌ Please provide a volume between 0 and 2 (e.g., 0.5 for 50%, 1 for 100%, 2 for 200%).");
        }

        this.player.state.resource.volume.setVolume(newVolume);
        msg.reply(`🔊 Volume set to ${Math.round(newVolume * 100)}%`);
    }

    async testFFmpegConversion(wavBytes) {
        const inputFile = `input_${Date.now()}.wav`;
        const outputFile = `output_${Date.now()}.pcm`;
        fs.writeFileSync(inputFile, wavBytes);

        return new Promise((resolve, reject) => {
            const { spawn } = require('child_process');
            const ffmpeg = spawn('ffmpeg', [
                '-i', inputFile,
                '-f', 's16le',
                '-ar', '48000',
                '-ac', '2',
                '-acodec', 'pcm_s16le',
                outputFile
            ]);

            let errorOutput = '';

            ffmpeg.stderr.on('data', (data) => {
                errorOutput += data.toString();
            });

            ffmpeg.on('error', (err) => {
                console.error('FFmpeg process error:', err);
                try { fs.unlinkSync(inputFile); } catch {}
                try { fs.unlinkSync(outputFile); } catch {}
                reject(err);
            });

            ffmpeg.on('close', (code) => {
                if (code !== 0) {
                    console.error('FFmpeg error output:', errorOutput);
                    try { fs.unlinkSync(inputFile); } catch {}
                    try { fs.unlinkSync(outputFile); } catch {}
                    reject(new Error(`FFmpeg process exited with code ${code}`));
                    return;
                }

                try {
                    if (fs.existsSync(outputFile)) {
                        const outputData = fs.readFileSync(outputFile);
                        try { fs.unlinkSync(inputFile); } catch {}
                        try { fs.unlinkSync(outputFile); } catch {}
                        resolve(outputData);
                    } else {
                        reject(new Error('Output file was not created'));
                    }
                } catch (err) {
                    console.error("Error reading output file:", err);
                    reject(err);
                }
            });
        });
    }

    login() {
        this.client.login(TOKEN);
    }
}

// Start the bot
const bot = new DiscordBot();
bot.login(); 