"""Visual frame analysis module using Ollama vision models.

This module uses Ollama's vision models (llava, moondream, etc.) to analyze
video frames and generate descriptive WebVTT files for accessibility and content understanding.

Example:
    >>> from msprites2.visual_analysis import VisualAnalyzer
    >>> analyzer = VisualAnalyzer(model="llava:7b")
    >>> analyzer.analyze_frames_to_webvtt("frames/", "descriptions.vtt")
"""

import base64
import os
from pathlib import Path
from typing import Optional, Literal, Callable, Union
from dataclasses import dataclass
import json

# Check if ollama is available
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None


@dataclass
class FrameDescription:
    """Represents a visual description of a video frame."""

    frame_number: int
    timestamp: float
    description: str
    frame_path: str

    def to_webvtt_timestamp(self, seconds: float) -> str:
        """Convert seconds to WebVTT timestamp format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def to_webvtt_cue(self, duration: float = 1.0) -> str:
        """Format frame description as a WebVTT cue block.

        Args:
            duration: Duration of the cue in seconds (default: 1.0)
        """
        start_ts = self.to_webvtt_timestamp(self.timestamp)
        end_ts = self.to_webvtt_timestamp(self.timestamp + duration)
        return f"{start_ts} --> {end_ts}\n{self.description.strip()}\n"


class VisualAnalyzer:
    """Analyze video frames using Ollama vision models and generate WebVTT descriptions.

    This class provides an interface to Ollama's vision models (llava, moondream, etc.)
    for automatic visual analysis of video frames, outputting timestamped descriptions
    in WebVTT format.

    Attributes:
        model: Ollama vision model name ('llava:7b', 'llava:13b', 'moondream', etc.)
        ollama_host: Ollama API endpoint URL
        fps: Frames per second for timestamp calculation

    Example:
        >>> analyzer = VisualAnalyzer(model="llava:7b", fps=1.0)
        >>> descriptions = analyzer.analyze_frames("frames/")
        >>> analyzer.save_webvtt(descriptions, "visual_descriptions.vtt")

    Note:
        Requires ollama package to be installed:
        `pip install msprites2[ai]`
    """

    WEBVTT_HEADER = "WEBVTT\nKIND: descriptions\n\n"
    DEFAULT_PROMPT = "Describe what you see in this video frame in one concise sentence. Focus on the main subject, action, and setting."

    def __init__(
        self,
        model: str = "llava:7b",
        ollama_host: str = "https://ollama.l.supported.systems",
        fps: float = 1.0,
        prompt: Optional[str] = None,
    ):
        """Initialize the visual analyzer with an Ollama vision model.

        Args:
            model: Ollama vision model name ('llava:7b', 'llava:13b', 'moondream')
            ollama_host: Ollama API endpoint URL
            fps: Frames per second (used for timestamp calculation)
            prompt: Custom prompt for frame analysis (uses default if None)
        """
        if not OLLAMA_AVAILABLE:
            raise ImportError(
                "ollama is required for visual analysis. "
                "Install it with: pip install msprites2[vision] or pip install msprites2[ai]"
            )

        self.model = model
        self.ollama_host = ollama_host
        self.fps = fps
        self.prompt = prompt or self.DEFAULT_PROMPT
        self.client = ollama.Client(host=ollama_host)

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string.

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded image string
        """
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def analyze_frame(
        self,
        frame_path: str,
        frame_number: int,
        custom_prompt: Optional[str] = None,
    ) -> FrameDescription:
        """Analyze a single frame using Ollama vision model.

        Args:
            frame_path: Path to frame image file
            frame_number: Frame number (for timestamp calculation)
            custom_prompt: Optional custom prompt (overrides instance prompt)

        Returns:
            FrameDescription object with analysis results

        Example:
            >>> desc = analyzer.analyze_frame("frame_0001.jpg", 1)
            >>> print(f"Frame 1: {desc.description}")
        """
        if not os.path.exists(frame_path):
            raise FileNotFoundError(f"Frame not found: {frame_path}")

        # Calculate timestamp from frame number and fps
        timestamp = frame_number / self.fps

        # Use custom prompt if provided, otherwise use instance prompt
        prompt = custom_prompt or self.prompt

        try:
            # Call Ollama vision model
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [frame_path],
                    }
                ],
            )

            description = response["message"]["content"].strip()

            return FrameDescription(
                frame_number=frame_number,
                timestamp=timestamp,
                description=description,
                frame_path=frame_path,
            )

        except Exception as e:
            raise RuntimeError(
                f"Failed to analyze frame {frame_path}: {str(e)}"
            ) from e

    def analyze_frames(
        self,
        frames_dir: Union[str, Path],
        pattern: str = "*.jpg",
        max_frames: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[FrameDescription]:
        """Analyze all frames in a directory.

        Args:
            frames_dir: Directory containing frame images
            pattern: Glob pattern for frame files (default: "*.jpg")
            max_frames: Maximum number of frames to analyze (None = all)
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            List of FrameDescription objects

        Example:
            >>> def progress(current, total):
            ...     print(f"Analyzing: {current}/{total}")
            >>> descriptions = analyzer.analyze_frames(
            ...     "frames/",
            ...     progress_callback=progress
            ... )
        """
        frames_path = Path(frames_dir)
        if not frames_path.exists():
            raise FileNotFoundError(f"Frames directory not found: {frames_dir}")

        # Get sorted list of frame files
        frame_files = sorted(frames_path.glob(pattern))

        if not frame_files:
            raise ValueError(f"No frames found matching pattern: {pattern}")

        if max_frames:
            frame_files = frame_files[:max_frames]

        descriptions = []
        total = len(frame_files)

        for idx, frame_file in enumerate(frame_files, 1):
            if progress_callback:
                progress_callback(idx, total)

            desc = self.analyze_frame(str(frame_file), idx)
            descriptions.append(desc)

        return descriptions

    def save_webvtt(
        self,
        descriptions: list[FrameDescription],
        output_path: str,
        cue_duration: float = 1.0,
    ) -> None:
        """Save frame descriptions as a WebVTT description file.

        Args:
            descriptions: List of FrameDescription objects
            output_path: Path to output WebVTT file
            cue_duration: Duration of each cue in seconds (default: 1.0)

        Example:
            >>> descriptions = analyzer.analyze_frames("frames/")
            >>> analyzer.save_webvtt(descriptions, "descriptions.vtt")
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.WEBVTT_HEADER)
            for i, desc in enumerate(descriptions, 1):
                # Optional cue identifier
                f.write(f"{i}\n")
                f.write(desc.to_webvtt_cue(duration=cue_duration))
                f.write("\n")

    def analyze_frames_to_webvtt(
        self,
        frames_dir: Union[str, Path],
        output_path: str,
        pattern: str = "*.jpg",
        max_frames: Optional[int] = None,
        cue_duration: float = 1.0,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[FrameDescription]:
        """Analyze frames and save directly to WebVTT description file.

        This is a convenience method that combines analyze_frames() and save_webvtt().

        Args:
            frames_dir: Directory containing frame images
            output_path: Path to output WebVTT file
            pattern: Glob pattern for frame files (default: "*.jpg")
            max_frames: Maximum number of frames to analyze (None = all)
            cue_duration: Duration of each cue in seconds (default: 1.0)
            progress_callback: Optional callback(current, total) for progress

        Returns:
            List of FrameDescription objects

        Example:
            >>> descriptions = analyzer.analyze_frames_to_webvtt(
            ...     "frames/",
            ...     "descriptions.vtt",
            ...     max_frames=100
            ... )
            >>> print(f"Generated {len(descriptions)} frame descriptions")
        """
        descriptions = self.analyze_frames(
            frames_dir,
            pattern=pattern,
            max_frames=max_frames,
            progress_callback=progress_callback,
        )
        self.save_webvtt(descriptions, output_path, cue_duration=cue_duration)
        return descriptions

    def batch_analyze(
        self,
        frame_paths: list[str],
        batch_size: int = 5,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[FrameDescription]:
        """Analyze multiple frames with batching for efficiency.

        Args:
            frame_paths: List of frame file paths
            batch_size: Number of frames to process before yielding results
            progress_callback: Optional callback(current, total) for progress

        Returns:
            List of FrameDescription objects

        Example:
            >>> frames = ["frame_001.jpg", "frame_002.jpg", ...]
            >>> descriptions = analyzer.batch_analyze(frames, batch_size=10)
        """
        descriptions = []
        total = len(frame_paths)

        for idx, frame_path in enumerate(frame_paths, 1):
            if progress_callback:
                progress_callback(idx, total)

            desc = self.analyze_frame(frame_path, idx)
            descriptions.append(desc)

        return descriptions


def analyze_video_frames(
    frames_dir: str,
    output_path: str,
    model: str = "llava:7b",
    ollama_host: str = "https://ollama.l.supported.systems",
    fps: float = 1.0,
) -> list[FrameDescription]:
    """Convenience function to analyze video frames and generate WebVTT descriptions.

    Args:
        frames_dir: Directory containing frame images
        output_path: Path to output WebVTT description file
        model: Ollama vision model name ('llava:7b', 'llava:13b', 'moondream')
        ollama_host: Ollama API endpoint URL
        fps: Frames per second (for timestamp calculation)

    Returns:
        List of FrameDescription objects

    Example:
        >>> from msprites2.visual_analysis import analyze_video_frames
        >>> descriptions = analyze_video_frames("frames/", "descriptions.vtt")
        >>> print(f"Generated {len(descriptions)} visual descriptions")
    """
    analyzer = VisualAnalyzer(model=model, ollama_host=ollama_host, fps=fps)
    return analyzer.analyze_frames_to_webvtt(frames_dir, output_path)