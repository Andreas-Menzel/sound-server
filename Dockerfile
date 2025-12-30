FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies including PulseAudio client tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    pulseaudio-utils \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Download and install Piper TTS
ARG PIPER_VERSION=2023.11.14-2
ARG TARGETARCH

RUN ARCH=$(case ${TARGETARCH:-amd64} in \
        amd64) echo "x86_64" ;; \
        arm64) echo "aarch64" ;; \
        *) echo "x86_64" ;; \
    esac) && \
    wget -q "https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_${ARCH}.tar.gz" -O /tmp/piper.tar.gz && \
    tar -xzf /tmp/piper.tar.gz -C /usr/local/bin && \
    rm /tmp/piper.tar.gz && \
    chmod +x /usr/local/bin/piper/piper

# Add piper to PATH
ENV PATH="/usr/local/bin/piper:${PATH}"

# Download voice models - English
RUN mkdir -p /app/models && \
    # Lessac - US English, neutral (default)
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx" \
        -O /app/models/lessac.onnx && \
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" \
        -O /app/models/lessac.onnx.json && \
    # Amy - US English, female
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx" \
        -O /app/models/amy.onnx && \
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json" \
        -O /app/models/amy.onnx.json && \
    # Joe - US English, male
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/joe/medium/en_US-joe-medium.onnx" \
        -O /app/models/joe.onnx && \
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/joe/medium/en_US-joe-medium.onnx.json" \
        -O /app/models/joe.onnx.json && \
    # Alan - British English, male
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx" \
        -O /app/models/alan.onnx && \
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json" \
        -O /app/models/alan.onnx.json && \
    # Alba - Scottish English, female
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/medium/en_GB-alba-medium.onnx" \
        -O /app/models/alba.onnx && \
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/medium/en_GB-alba-medium.onnx.json" \
        -O /app/models/alba.onnx.json

# Download voice models - German
RUN \
    # Thorsten - German, male
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx" \
        -O /app/models/thorsten.onnx && \
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx.json" \
        -O /app/models/thorsten.onnx.json && \
    # Karlsson - German, male
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/karlsson/low/de_DE-karlsson-low.onnx" \
        -O /app/models/karlsson.onnx && \
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/karlsson/low/de_DE-karlsson-low.onnx.json" \
        -O /app/models/karlsson.onnx.json && \
    # Kerstin - German, female
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/kerstin/low/de_DE-kerstin-low.onnx" \
        -O /app/models/kerstin.onnx && \
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/kerstin/low/de_DE-kerstin-low.onnx.json" \
        -O /app/models/kerstin.onnx.json

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create audio directory
RUN mkdir -p /app/audio

# Expose FastAPI port
EXPOSE 8000

# Set PulseAudio server to connect to host
ENV PULSE_SERVER=tcp:host.docker.internal:4713

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
