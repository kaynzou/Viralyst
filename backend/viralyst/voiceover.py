"""Text-to-speech: turn a suggested opening line into a voiceover, using Supertonic on your Mac.

Supertonic runs locally and for free. The first run downloads its model from Hugging Face.
"""

from pathlib import Path


def speak(text: str, out: Path, voice: str | None = None, lang: str = "en", tts=None) -> Path:
    if tts is None:
        from supertonic import TTS  # imported here because it's slow to load
        tts = TTS()
    style = tts.get_voice_style(voice or tts.voice_style_names[0])
    wav, _ = tts.synthesize(text, voice_style=style, lang=lang)
    tts.save_audio(wav, str(out))
    return out
