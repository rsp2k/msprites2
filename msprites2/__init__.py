from .montage_sprites import MontageSprites

# Build __all__ dynamically based on available optional dependencies
__all__ = ["MontageSprites"]

# Audio transcription (optional, requires faster-whisper)
try:
    from .audio_transcription import (
        AudioTranscriber,
        TranscriptionSegment,
        WordTimestamp,
        transcribe_video,
    )

    __all__.extend(["AudioTranscriber", "TranscriptionSegment", "WordTimestamp", "transcribe_video"])
except ImportError:
    pass

# Transcript enhancers (optional, requires ollama for OllamaTextEnhancer)
try:
    from .enhancers import (
        TranscriptEnhancer,
        OllamaTextEnhancer,
        SimpleEnhancer,
        create_enhancer,
    )

    __all__.extend(["TranscriptEnhancer", "OllamaTextEnhancer", "SimpleEnhancer", "create_enhancer"])
except ImportError:
    pass

# Visual analysis (optional, requires ollama)
try:
    from .visual_analysis import (
        VisualAnalyzer,
        FrameDescription,
        analyze_video_frames,
    )

    __all__.extend(["VisualAnalyzer", "FrameDescription", "analyze_video_frames"])
except ImportError:
    pass
