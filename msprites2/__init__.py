from .montage_sprites import MontageSprites

# Audio transcription (optional, requires faster-whisper)
try:
    from .audio_transcription import (
        AudioTranscriber,
        TranscriptionSegment,
        transcribe_video,
    )

    __all__ = [
        "MontageSprites",
        "AudioTranscriber",
        "TranscriptionSegment",
        "transcribe_video",
    ]
except ImportError:
    # faster-whisper not installed
    __all__ = [
        "MontageSprites",
    ]
