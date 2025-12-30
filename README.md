# Piper TTS Docker Service

A Dockerized Text-to-Speech service using [Piper](https://github.com/rhasspy/piper) with a FastAPI REST API. Works on both **macOS** and **Linux** via PulseAudio TCP bridge.

## Features

- Fast, local TTS using Piper (no cloud APIs)
- REST API with FastAPI
- Cross-platform audio playback (macOS/Linux)
- Pre-installed English voice model (en_US-lessac-medium)

## Project Structure

```
.
├── Dockerfile
├── docker-compose.yml
├── main.py
├── requirements.txt
├── audio_files/          # Mounted volume for audio files
└── README.md
```

## Prerequisites

- Docker and Docker Compose
- PulseAudio installed on the host

---

## Host Setup Instructions

### macOS Setup

1. **Install PulseAudio via Homebrew:**

   ```bash
   brew install pulseaudio
   ```

2. **Start PulseAudio with TCP module enabled:**

   ```bash
   # Start PulseAudio daemon with TCP module on port 4713
   pulseaudio --load="module-native-protocol-tcp port=4713 auth-anonymous=1" --exit-idle-time=-1 --daemon
   ```

   Or add to your PulseAudio config permanently:
   ```bash
   # Add to ~/.config/pulse/default.pa (create if doesn't exist)
   echo "load-module module-native-protocol-tcp port=4713 auth-anonymous=1" >> ~/.config/pulse/default.pa
   ```

3. **Verify PulseAudio is running:**

   ```bash
   pulseaudio --check && echo "PulseAudio is running" || echo "PulseAudio not running"
   ```

4. **To stop PulseAudio:**

   ```bash
   pulseaudio --kill
   ```

### Linux Setup

1. **Install PulseAudio (if not already installed):**

   ```bash
   # Debian/Ubuntu
   sudo apt-get install pulseaudio pulseaudio-utils

   # Fedora
   sudo dnf install pulseaudio pulseaudio-utils

   # Arch
   sudo pacman -S pulseaudio pulseaudio-alsa
   ```

2. **Load the TCP module:**

   ```bash
   # Load TCP module on port 4713 (allows connections from Docker network)
   pactl load-module module-native-protocol-tcp port=4713 auth-ip-acl=127.0.0.1;172.17.0.0/16;192.168.0.0/16
   ```

   For persistent configuration, add to `/etc/pulse/default.pa` or `~/.config/pulse/default.pa`:
   ```
   load-module module-native-protocol-tcp port=4713 auth-ip-acl=127.0.0.1;172.17.0.0/16;192.168.0.0/16
   ```

3. **Verify the module is loaded:**

   ```bash
   pactl list modules short | grep tcp
   ```

4. **Restart PulseAudio if needed:**

   ```bash
   systemctl --user restart pulseaudio
   # or
   pulseaudio --kill && pulseaudio --start
   ```

---

## Running the Service

1. **Create the audio files directory:**

   ```bash
   mkdir -p audio_files
   ```

2. **Build and start the container:**

   ```bash
   docker-compose up --build -d
   ```

3. **Check logs:**

   ```bash
   docker-compose logs -f tts
   ```

4. **Stop the service:**

   ```bash
   docker-compose down
   ```

---

## API Endpoints

### Health Check

```bash
curl http://localhost:8000/health
```

### POST /say - Generate and Play Speech

```bash
# Basic usage - generates TTS and plays through speakers
curl -X POST http://localhost:8000/say \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, world! This is a test of the Piper TTS service."}'

# Save to file while playing
curl -X POST http://localhost:8000/say \
  -H "Content-Type: application/json" \
  -d '{"text": "This will be saved", "save_file": "greeting.wav"}'
```

### POST /play - Play Existing Audio File

```bash
# Play a file from the mounted audio_files directory
curl -X POST http://localhost:8000/play \
  -H "Content-Type: application/json" \
  -d '{"filename": "greeting.wav"}'
```

### GET /files - List Audio Files

```bash
curl http://localhost:8000/files
```

---

## API Documentation

Once the service is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Troubleshooting

### "Connection refused" when playing audio

1. Ensure PulseAudio is running on the host with TCP module loaded
2. Check the port is correct (4713)
3. On Linux, verify the auth-ip-acl includes Docker networks

### Test PulseAudio connectivity from container

```bash
docker-compose exec tts bash -c 'PULSE_SERVER=tcp:host.docker.internal:4713 paplay --help'
```

### Check if host.docker.internal resolves

```bash
docker-compose exec tts getent hosts host.docker.internal
```

### View container environment

```bash
docker-compose exec tts env | grep PULSE
```

### Linux: Alternative using Docker Gateway IP

If `host.docker.internal` doesn't work, you can use the Docker gateway IP directly:

```bash
# Find the gateway IP
docker network inspect bridge | grep Gateway

# Update PULSE_SERVER in docker-compose.yml
# e.g., PULSE_SERVER=tcp:172.17.0.1:4713
```

---

## Adding More Voice Models

Download additional Piper voices from: https://huggingface.co/rhasspy/piper-voices

```bash
# Example: Download a different voice
wget -P ./models/ https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/medium/en_GB-alba-medium.onnx
wget -P ./models/ https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/medium/en_GB-alba-medium.onnx.json
```

Then mount the models directory in docker-compose.yml:
```yaml
volumes:
  - ./audio_files:/app/audio
  - ./models:/app/models
```

---

## License

This project uses:
- [Piper TTS](https://github.com/rhasspy/piper) - MIT License
- [FastAPI](https://fastapi.tiangolo.com/) - MIT License
