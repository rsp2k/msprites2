"""Audio transcription module for generating WebVTT captions from video files.

This module uses faster-whisper to transcribe audio and generate WebVTT caption files
that comply with the W3C WebVTT specification for captions/subtitles.

Example:
    >>> from msprites2.audio_transcription import AudioTranscriber
    >>> transcriber = AudioTranscriber(model_size="base")
    >>> transcriber.transcribe_to_webvtt("video.mp4", "captions.vtt")
"""

import os
import json
from typing import Optional, Literal, Callable, List, Dict, Any
from dataclasses import dataclass, field, asdict

# Check if faster-whisper is available
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    WhisperModel = None


@dataclass
class WordTimestamp:
    """Represents a word with precise timing information."""

    word: str
    start: float
    end: float
    probability: float = 0.0


@dataclass
class TranscriptionSegment:
    """Represents a transcription segment with timing, text, and optional metadata.

    Attributes:
        start: Segment start time in seconds
        end: Segment end time in seconds
        text: Original transcribed text from Whisper
        enhanced_text: Optional enhanced/corrected text from post-processing
        confidence: Segment-level confidence score (0.0-1.0)
        words: Optional word-level timestamps and probabilities
        speaker_id: Optional speaker identification
        language: Detected or specified language code
        metadata: Additional custom metadata
    """

    start: float
    end: float
    text: str
    enhanced_text: Optional[str] = None
    confidence: Optional[float] = None
    words: List[WordTimestamp] = field(default_factory=list)
    speaker_id: Optional[str] = None
    language: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_webvtt_timestamp(self, seconds: float) -> str:
        """Convert seconds to WebVTT timestamp format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def to_webvtt_cue(self, use_enhanced: bool = False) -> str:
        """Format segment as a WebVTT cue block.

        Args:
            use_enhanced: Use enhanced_text if available, otherwise use text
        """
        start_ts = self.to_webvtt_timestamp(self.start)
        end_ts = self.to_webvtt_timestamp(self.end)
        content = self.enhanced_text if (use_enhanced and self.enhanced_text) else self.text
        return f"{start_ts} --> {end_ts}\n{content.strip()}\n"

    def to_srt_cue(self, index: int, use_enhanced: bool = False) -> str:
        """Format segment as an SRT cue block.

        Args:
            index: 1-based cue index for SRT format
            use_enhanced: Use enhanced_text if available
        """
        start_ts = self.to_webvtt_timestamp(self.start).replace(".", ",")
        end_ts = self.to_webvtt_timestamp(self.end).replace(".", ",")
        content = self.enhanced_text if (use_enhanced and self.enhanced_text) else self.text
        return f"{index}\n{start_ts} --> {end_ts}\n{content.strip()}\n"

    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert WordTimestamp objects to dicts
        if self.words:
            data["words"] = [asdict(w) for w in self.words]
        return data


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
        enhancer: Optional["TranscriptEnhancer"] = None,
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
            enhancer: Optional TranscriptEnhancer for post-processing transcripts
        """
        if not FASTER_WHISPER_AVAILABLE:
            raise ImportError(
                "faster-whisper is required for audio transcription. "
                "Install it with: pip install msprites2[transcription]"
            )

        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.enhancer = enhancer
        self._post_processors: List[Callable] = []
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

    def register_post_processor(self, processor_func: Callable):
        """Register a custom post-processing function for transcript enhancement.

        Post-processors are called in order after the enhancer (if present).
        Each processor should be an async function that takes (text, context) and returns enhanced text.

        Args:
            processor_func: Async function with signature (text: str, context: str) -> str

        Example:
            >>> async def remove_profanity(text: str, context: str) -> str:
            ...     # Custom filtering logic
            ...     return text.replace("bad_word", "***")
            >>>
            >>> transcriber.register_post_processor(remove_profanity)
        """
        self._post_processors.append(processor_func)

    async def transcribe_enhanced(
        self,
        video_path: str,
        context: str = "general",
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> tuple[list[TranscriptionSegment], Optional[str]]:
        """Transcribe with enhancement pipeline using enhancer and post-processors.

        This method runs the full enhancement pipeline:
        1. Base Whisper transcription
        2. Enhancer processing (if configured)
        3. Custom post-processors (if registered)

        Args:
            video_path: Path to video file
            context: Domain context for enhancement (technical, educational, medical, etc.)
            language: Override language detection
            beam_size: Beam size for decoding
            vad_filter: Use Voice Activity Detection
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (segments, enhanced_text) where enhanced_text may be None if no enhancer

        Example:
            >>> from msprites2.enhancers import OllamaTextEnhancer
            >>> enhancer = OllamaTextEnhancer(model="llama3.1:8b")
            >>> transcriber = AudioTranscriber(enhancer=enhancer)
            >>> segments, enhanced = await transcriber.transcribe_enhanced(
            ...     "video.mp4",
            ...     context="technical"
            ... )
            >>> print(f"Raw: {segments[0].text}")
            >>> print(f"Enhanced: {enhanced[:100]}")
        """
        import asyncio

        # Step 1: Base transcription
        segments = self.transcribe(
            video_path,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            progress_callback=progress_callback,
        )

        # Step 2: Apply enhancer if available
        enhanced_text = None
        if self.enhancer:
            raw_text = " ".join([seg.text for seg in segments])
            enhanced_text = await self.enhancer.enhance(raw_text, context)

        # Step 3: Apply custom post-processors
        current_text = enhanced_text or " ".join([seg.text for seg in segments])
        for processor in self._post_processors:
            current_text = await processor(current_text, context)

        # Update enhanced_text if post-processors were applied
        if self._post_processors:
            enhanced_text = current_text

        # Store enhanced text in segments for easy access
        if enhanced_text:
            for seg in segments:
                seg.metadata["enhanced_full_text"] = enhanced_text

        return segments, enhanced_text

    def save_all_formats(
        self,
        segments: list[TranscriptionSegment],
        output_dir: str,
        base_name: str = "transcript",
        formats: list[str] = None,
        enhanced_text: Optional[str] = None,
        use_enhanced: bool = True,
    ):
        """Save transcription in multiple formats.

        Args:
            segments: List of TranscriptionSegment objects
            output_dir: Directory to save output files
            base_name: Base filename (without extension)
            formats: List of formats to generate (default: ["json", "txt", "webvtt", "srt"])
            enhanced_text: Optional enhanced full text
            use_enhanced: Whether to use enhanced_text in output files

        Supported formats:
            - json: Full JSON with metadata
            - txt: Plain text with timestamps
            - webvtt: WebVTT caption file
            - srt: SubRip (SRT) caption file

        Example:
            >>> segments, enhanced = await transcriber.transcribe_enhanced("video.mp4")
            >>> transcriber.save_all_formats(
            ...     segments,
            ...     "output/",
            ...     formats=["json", "webvtt", "srt"],
            ...     enhanced_text=enhanced
            ... )
        """
        if formats is None:
            formats = ["json", "txt", "webvtt", "srt"]

        os.makedirs(output_dir, exist_ok=True)

        if "json" in formats:
            self._save_json(
                segments,
                enhanced_text,
                os.path.join(output_dir, f"{base_name}.json"),
            )
        if "txt" in formats:
            self._save_txt(
                segments,
                enhanced_text,
                os.path.join(output_dir, f"{base_name}.txt"),
                use_enhanced=use_enhanced,
            )
        if "webvtt" in formats:
            self._save_webvtt_enhanced(
                segments,
                os.path.join(output_dir, f"{base_name}.vtt"),
                use_enhanced=use_enhanced,
            )
        if "srt" in formats:
            self._save_srt(
                segments,
                os.path.join(output_dir, f"{base_name}.srt"),
                use_enhanced=use_enhanced,
            )

    def _save_json(
        self,
        segments: list[TranscriptionSegment],
        enhanced_text: Optional[str],
        path: str,
    ):
        """Save transcription as JSON with full metadata."""
        data = {
            "enhanced_text": enhanced_text,
            "raw_text": " ".join([seg.text for seg in segments]),
            "segments": [seg.to_dict() for seg in segments],
            "metadata": {
                "model_size": self.model_size,
                "device": self.device,
                "language": self.language,
                "segment_count": len(segments),
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_txt(
        self,
        segments: list[TranscriptionSegment],
        enhanced_text: Optional[str],
        path: str,
        use_enhanced: bool = True,
    ):
        """Save transcription as formatted text file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Transcript\n\n")

            if enhanced_text and use_enhanced:
                f.write("## Enhanced Version\n\n")
                f.write(enhanced_text)
                f.write("\n\n## Raw Segments\n\n")
            else:
                f.write("## Transcript Segments\n\n")

            for seg in segments:
                start_time = f"{int(seg.start//60):02d}:{int(seg.start%60):02d}"
                end_time = f"{int(seg.end//60):02d}:{int(seg.end%60):02d}"
                text = seg.enhanced_text if (use_enhanced and seg.enhanced_text) else seg.text
                f.write(f"**[{start_time} - {end_time}]**: {text}\n\n")

    def _save_webvtt_enhanced(
        self, segments: list[TranscriptionSegment], path: str, use_enhanced: bool = True
    ):
        """Save WebVTT with option to use enhanced text."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.WEBVTT_HEADER)
            for i, segment in enumerate(segments, 1):
                f.write(f"{i}\n")
                f.write(segment.to_webvtt_cue(use_enhanced=use_enhanced))
                f.write("\n")

    def _save_srt(
        self, segments: list[TranscriptionSegment], path: str, use_enhanced: bool = True
    ):
        """Save as SRT (SubRip) format."""
        with open(path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                f.write(segment.to_srt_cue(index=i, use_enhanced=use_enhanced))
                f.write("\n")


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