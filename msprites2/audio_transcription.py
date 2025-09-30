"""Audio transcription module for generating WebVTT captions from video files.

This module uses faster-whisper to transcribe audio and generate WebVTT caption files
that comply with the W3C WebVTT specification for captions/subtitles.

Example:
    >>> from msprites2.audio_transcription import AudioTranscriber
    >>> transcriber = AudioTranscriber(model_size="base")
    >>> transcriber.transcribe_to_webvtt("video.mp4", "captions.vtt")
"""

import os
from typing import Optional, Literal, Callable
from dataclasses import dataclass


@dataclass
class TranscriptionSegment:
    """Represents a transcription segment with timing and text."""

    start: float
    end: float
    text: str

    def to_webvtt_timestamp(self, seconds: float) -> str:
        """Convert seconds to WebVTT timestamp format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def to_webvtt_cue(self) -> str:
        """Format segment as a WebVTT cue block."""
        start_ts = self.to_webvtt_timestamp(self.start)
        end_ts = self.to_webvtt_timestamp(self.end)
        return f"{start_ts} --> {end_ts}\n{self.text.strip()}\n"


class AudioTranscriber:
    """Transcribe audio from video files using Whisper and generate WebVTT captions.

    This class provides an interface to OpenAI's Whisper model (via faster-whisper)
    for automatic speech recognition, outputting timestamped captions in WebVTT format.

    Attributes:
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large-v3')
        device: Compute device ('cpu', 'cuda', 'auto')
        compute_type: Precision ('int8', 'float16', 'float32')

    Example:
        >>> transcriber = AudioTranscriber(model_size="base", device="cpu")
        >>> segments = transcriber.transcribe("video.mp4")
        >>> transcriber.save_webvtt(segments, "captions.vtt")

    Note:
        Requires faster-whisper to be installed:
        `pip install msprites2[transcription]`
    """

    WEBVTT_HEADER = "WEBVTT\n\n"

    def __init__(
        self,
        model_size: Literal["tiny", "base", "small", "medium", "large-v3"] = "base",
        device: Literal["cpu", "cuda", "auto"] = "auto",
        compute_type: Literal["int8", "float16", "float32"] = "int8",
        language: Optional[str] = None,
    ):
        """Initialize the transcriber with a Whisper model.

        Args:
            model_size: Model size (larger = more accurate but slower).
                       'tiny' - fastest, least accurate (~39M params)
                       'base' - good balance (~74M params) [DEFAULT]
                       'small' - better quality (~244M params)
                       'medium' - high quality (~769M params)
                       'large-v3' - best quality (~1550M params)
            device: Compute device ('cpu', 'cuda', or 'auto' for automatic detection)
            compute_type: Precision ('int8' for CPU, 'float16' for GPU)
            language: Force a specific language code (e.g., 'en', 'es', 'fr')
                     If None, language will be auto-detected
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError(
                "faster-whisper is required for audio transcription. "
                "Install it with: pip install msprites2[transcription]"
            ) from e

        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.model = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )

    def transcribe(
        self,
        video_path: str,
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> list[TranscriptionSegment]:
        """Transcribe audio from a video file.

        Args:
            video_path: Path to video file
            language: Override language detection (e.g., 'en', 'es', 'fr')
            beam_size: Beam size for decoding (higher = better but slower)
            vad_filter: Use Voice Activity Detection to filter silence
            progress_callback: Optional callback function(progress: float) for progress updates

        Returns:
            List of TranscriptionSegment objects with timing and text

        Example:
            >>> segments = transcriber.transcribe("video.mp4", language="en")
            >>> for seg in segments:
            ...     print(f"[{seg.start:.2f}s] {seg.text}")
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Use instance language if not overridden
        lang = language or self.language

        segments, info = self.model.transcribe(
            video_path,
            language=lang,
            beam_size=beam_size,
            vad_filter=vad_filter,
        )

        result = []
        for segment in segments:
            result.append(
                TranscriptionSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                )
            )
            if progress_callback:
                # Approximate progress based on segment end time
                progress_callback(segment.end)

        return result

    def save_webvtt(
        self,
        segments: list[TranscriptionSegment],
        output_path: str,
    ) -> None:
        """Save transcription segments as a WebVTT caption file.

        Args:
            segments: List of TranscriptionSegment objects
            output_path: Path to output WebVTT file

        Example:
            >>> segments = transcriber.transcribe("video.mp4")
            >>> transcriber.save_webvtt(segments, "captions.vtt")
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.WEBVTT_HEADER)
            for i, segment in enumerate(segments, 1):
                # Optional cue identifier
                f.write(f"{i}\n")
                f.write(segment.to_webvtt_cue())
                f.write("\n")

    def transcribe_to_webvtt(
        self,
        video_path: str,
        output_path: str,
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> list[TranscriptionSegment]:
        """Transcribe audio and save directly to WebVTT caption file.

        This is a convenience method that combines transcribe() and save_webvtt().

        Args:
            video_path: Path to video file
            output_path: Path to output WebVTT file
            language: Override language detection (e.g., 'en', 'es', 'fr')
            beam_size: Beam size for decoding (higher = better but slower)
            vad_filter: Use Voice Activity Detection to filter silence
            progress_callback: Optional callback function(progress: float)

        Returns:
            List of TranscriptionSegment objects

        Example:
            >>> segments = transcriber.transcribe_to_webvtt(
            ...     "video.mp4",
            ...     "captions.vtt",
            ...     language="en"
            ... )
            >>> print(f"Generated {len(segments)} caption segments")
        """
        segments = self.transcribe(
            video_path,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            progress_callback=progress_callback,
        )
        self.save_webvtt(segments, output_path)
        return segments


def transcribe_video(
    video_path: str,
    output_path: str,
    model_size: str = "base",
    language: Optional[str] = None,
    device: str = "auto",
) -> list[TranscriptionSegment]:
    """Convenience function to transcribe a video and generate WebVTT captions.

    Args:
        video_path: Path to video file
        output_path: Path to output WebVTT caption file
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large-v3')
        language: Optional language code (e.g., 'en', 'es', 'fr')
        device: Compute device ('cpu', 'cuda', 'auto')

    Returns:
        List of TranscriptionSegment objects

    Example:
        >>> from msprites2.audio_transcription import transcribe_video
        >>> segments = transcribe_video("video.mp4", "captions.vtt")
        >>> print(f"Generated {len(segments)} captions")
    """
    transcriber = AudioTranscriber(model_size=model_size, device=device)
    return transcriber.transcribe_to_webvtt(
        video_path, output_path, language=language
    )