# The Viralyst API in a container: Python, ffmpeg and every library, ready to run on any server.
# Hugging Face Spaces builds this file automatically (see deploy/README.md).

# Start from a small Linux with Python 3.12 and uv already installed.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# ffmpeg pulls frames and audio out of uploaded videos.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Hugging Face runs containers as a normal user (id 1000), never as the all-powerful root.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /home/user/app

# Install the libraries first. Docker reuses this step until pyproject.toml or uv.lock change,
# so editing code doesn't re-download everything.
COPY --chown=user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Then copy the code.
COPY --chown=user . .
RUN uv sync --frozen --no-dev

# Download the speech-to-text model now, so the first video upload doesn't wait for it.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# Hugging Face sends visitors to port 7860.
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "fastapi run viralyst/api.py --host 0.0.0.0 --port $PORT"]
