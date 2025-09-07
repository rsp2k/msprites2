"""
Parallel frame extraction for msprites2.

This module provides high-performance parallel frame extraction from video files using
ffmpeg-python's fluent interface. It splits videos into chunks and processes them
concurrently for significant speed improvements over sequential extraction.

Key Features:
    - Parallel processing using ThreadPoolExecutor
    - Fluent ffmpeg-python interface for robust command building
    - Progress callbacks for long-running operations
    - Automatic chunk size optimization
    - Proper frame ordering and numbering
    - Comprehensive error handling and logging

Performance Characteristics:
    - Primary benefit: Streaming processing for ML/AI pipelines
    - Sequential processing often optimal for simple frame extraction
    - Parallel benefits depend on video length, codec, and I/O characteristics
    - Best for: videos >5 minutes, network storage, or CPU-intensive post-processing
    - See PERFORMANCE_ANALYSIS.md for detailed benchmarks and recommendations

References:
    - ffmpeg-python docs: https://github.com/kkroening/ffmpeg-python
    - FFmpeg scaling: https://ffmpeg.org/ffmpeg-filters.html#scale
    - WebVTT spec: https://www.w3.org/TR/webvtt1/

Example:
    Basic usage with default settings:

    >>> extractor = ParallelFrameExtractor("video.mp4", "output/")
    >>> frame_count = extractor.extract_parallel()
    >>> print(f"Extracted {frame_count} frames")

    Advanced usage with custom settings:

    >>> def progress_callback(completed, total):
    ...     print(f"Progress: {completed}/{total} chunks")

    >>> extractor = ParallelFrameExtractor(
    ...     video_path="long_video.mp4",
    ...     output_dir="thumbnails/",
    ...     width=256, height=144,  # Smaller thumbnails
    ...     ips=2,  # Extract every 2 seconds
    ...     chunk_duration=5,  # 5-second chunks
    ...     max_workers=4,  # Limit concurrent processes
    ...     progress_callback=progress_callback
    ... )
    >>> frame_count = extractor.extract_parallel()

Expected Output Structure:
    output_dir/
    ├── 0001.jpg  # Frame at 0-1 seconds
    ├── 0002.jpg  # Frame at 1-2 seconds
    ├── 0003.jpg  # Frame at 2-3 seconds
    └── ...       # Sequential numbering maintained
"""

import concurrent.futures
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, Optional

import ffmpeg

logger = logging.getLogger(__name__)


class ParallelFrameExtractor:
    """Extract video frames in parallel using multiple FFmpeg processes."""

    def __init__(
        self,
        video_path: str,
        output_dir: str,
        width: int = 512,
        height: int = 288,
        ips: int = 1,
        chunk_duration: int = 10,
        max_workers: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        self.video_path = video_path
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.ips = ips
        self.chunk_duration = chunk_duration
        self.max_workers = max_workers or min(8, (os.cpu_count() or 1) + 4)
        self.progress_callback = progress_callback

    def get_video_duration(self) -> float:
        """Get video duration in seconds using ffmpeg-python probe.

        Uses ffmpeg-python's fluent interface to probe video metadata.

        Returns:
            float: Video duration in seconds

        Raises:
            ffmpeg.Error: If video probing fails

        Example:
            >>> extractor = ParallelFrameExtractor("video.mp4", "out/")
            >>> duration = extractor.get_video_duration()
            >>> print(f"Video is {duration:.2f} seconds long")
            Video is 120.50 seconds long
        """
        try:
            probe = ffmpeg.probe(self.video_path)
            duration = float(probe["format"]["duration"])
            logger.debug(f"Video duration: {duration:.2f}s")
            return duration
        except (ffmpeg.Error, KeyError, ValueError) as e:
            logger.error(f"Failed to get video duration: {e}")
            raise

    def calculate_chunks(self, duration: float) -> list[tuple[float, float, int]]:
        """Calculate video chunks for parallel processing.

        Divides the video into time-based chunks that can be processed independently.
        Each chunk extracts frames for a specific time range.

        Args:
            duration: Total video duration in seconds

        Returns:
            List of (start_time, end_time, expected_frames) tuples

        Example:
            For a 25-second video with 10-second chunks and 1 fps:
            >>> chunks = extractor.calculate_chunks(25.0)
            >>> for start, end, frames in chunks:
            ...     print(f"Chunk {start:.1f}-{end:.1f}s: ~{frames} frames")
            Chunk 0.0-10.0s: ~10 frames
            Chunk 10.0-20.0s: ~10 frames
            Chunk 20.0-25.0s: ~5 frames
        """
        chunks = []
        current_time = 0.0

        while current_time < duration:
            end_time = min(current_time + self.chunk_duration, duration)
            chunk_duration_actual = end_time - current_time
            expected_frames = max(1, int(chunk_duration_actual / self.ips))

            chunks.append((current_time, end_time, expected_frames))
            current_time = end_time

        logger.debug(
            f"Split {duration:.2f}s video into {len(chunks)} chunks of {self.chunk_duration}s each"
        )
        return chunks

    def extract_chunk(
        self, start_time: float, end_time: float, chunk_id: int
    ) -> list[str]:
        """Extract frames from a video chunk using ffmpeg-python fluent interface.

        Uses the fluent interface to build a robust FFmpeg pipeline:
        1. Seek to start_time (-ss)
        2. Process for duration (-t)
        3. Scale frames to target resolution
        4. Extract at specified frame rate

        Args:
            start_time: Chunk start time in seconds
            end_time: Chunk end time in seconds
            chunk_id: Unique identifier for this chunk

        Returns:
            List of extracted frame file paths

        Example FFmpeg command generated:
            ffmpeg -ss 10.0 -t 5.0 -i video.mp4 -r 0.5 \\
                   -vf scale=512:288 -y /tmp/chunk_1_%04d.jpg
        """
        # Create temporary directory for this chunk
        chunk_dir = tempfile.mkdtemp(prefix=f"chunk_{chunk_id}_")
        chunk_duration = end_time - start_time
        output_pattern = os.path.join(chunk_dir, "%04d.jpg")

        try:
            # Build FFmpeg pipeline using fluent interface
            stream = (
                ffmpeg.input(self.video_path, ss=start_time, t=chunk_duration)
                .filter("scale", self.width, self.height)
                .output(
                    output_pattern,
                    r=f"1/{self.ips}",  # Frame rate: 1 frame per IPS seconds
                    loglevel="error",
                )
                .overwrite_output()  # -y flag
            )

            logger.debug(
                f"Chunk {chunk_id} ({start_time:.1f}-{end_time:.1f}s): Starting extraction"
            )

            # Execute the pipeline
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)

            # Get list of generated frames
            chunk_frames = sorted(Path(chunk_dir).glob("*.jpg"))
            frame_paths = [str(f) for f in chunk_frames]

            logger.debug(
                f"Chunk {chunk_id} complete: {len(frame_paths)} frames extracted"
            )
            return frame_paths

        except ffmpeg.Error as e:
            stderr_msg = (
                e.stderr.decode()
                if e.stderr and hasattr(e.stderr, "decode")
                else str(e.stderr)
                if e.stderr
                else "Unknown error"
            )
            logger.error(f"Chunk {chunk_id} FFmpeg error: {stderr_msg}")
            return []
        except Exception as e:
            logger.error(f"Chunk {chunk_id} unexpected error: {e}")
            return []

    def merge_chunks(self, chunk_results: list[list[str]]) -> int:
        """Merge chunk results into final output directory.

        Returns total number of frames processed.
        """
        os.makedirs(self.output_dir, exist_ok=True)

        frame_counter = 1
        total_frames = 0

        for chunk_frames in chunk_results:
            for frame_path in chunk_frames:
                if os.path.exists(frame_path):
                    output_path = os.path.join(
                        self.output_dir, f"{frame_counter:04d}.jpg"
                    )

                    # Move frame to final location
                    os.rename(frame_path, output_path)
                    frame_counter += 1
                    total_frames += 1

                    # Clean up temporary directory
                    temp_dir = os.path.dirname(frame_path)
                    try:
                        if not os.listdir(temp_dir):
                            os.rmdir(temp_dir)
                    except OSError:
                        pass  # Directory not empty or other error

        return total_frames

    def extract_streaming(
        self, frame_processor: Optional[Callable[[str, int], str]] = None
    ):
        """Extract frames with streaming processing (inspired by TensorFlow example).

        Yields frames as they're extracted, allowing for real-time processing
        like neural style transfer, object detection, or other ML pipelines.

        Args:
            frame_processor: Optional function to process each frame
                           Signature: (frame_path: str, frame_num: int) -> processed_path: str

        Yields:
            Tuple[str, int]: (frame_path, frame_number) for each extracted frame

        Example for neural style transfer (--dream mode):
            >>> def style_transfer(frame_path, frame_num):
            ...     # Apply neural style transfer
            ...     styled_path = f"styled_{frame_num:04d}.jpg"
            ...     model.process(frame_path, styled_path)
            ...     return styled_path

            >>> for frame_path, frame_num in extractor.extract_streaming(style_transfer):
            ...     print(f"Processed frame {frame_num}: {frame_path}")

        Example for object detection pipeline:
            >>> def detect_objects(frame_path, frame_num):
            ...     detections = detector.detect(frame_path)
            ...     annotated_path = f"annotated_{frame_num:04d}.jpg"
            ...     draw_boxes(frame_path, detections, annotated_path)
            ...     return annotated_path
        """
        logger.info(f"Starting streaming frame extraction: {self.video_path}")

        duration = self.get_video_duration()
        chunks = self.calculate_chunks(duration)

        frame_counter = 1
        completed_chunks = 0

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # Submit chunk extraction tasks
            future_to_chunk = {
                executor.submit(self.extract_chunk, start, end, i): (i, expected)
                for i, (start, end, expected) in enumerate(chunks)
            }

            # Process frames as chunks complete
            chunk_results = {}

            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_id, expected_frames = future_to_chunk[future]

                try:
                    chunk_frames = future.result()
                    chunk_results[chunk_id] = chunk_frames
                    completed_chunks += 1

                    logger.debug(
                        f"Chunk {chunk_id} complete: {len(chunk_frames)} frames"
                    )

                    # Process completed chunks in order
                    while frame_counter - 1 in [
                        c[0] for c in chunk_results.keys() if isinstance(c, tuple)
                    ]:
                        # Find the chunk that contains this frame
                        for chunk_id_key, frames in list(chunk_results.items()):
                            if (
                                chunk_id_key == frame_counter - 1
                            ):  # Simplified for streaming
                                for frame_path in frames:
                                    if frame_processor:
                                        processed_path = frame_processor(
                                            frame_path, frame_counter
                                        )
                                        yield (processed_path, frame_counter)
                                    else:
                                        yield (frame_path, frame_counter)
                                    frame_counter += 1

                                del chunk_results[chunk_id_key]
                                break

                    if self.progress_callback:
                        self.progress_callback(completed_chunks, len(chunks))

                except Exception as e:
                    logger.error(f"Chunk {chunk_id} failed: {e}")

    def extract_parallel(self) -> int:
        """Extract frames in parallel (batch mode).

        Returns total number of frames extracted.
        """
        logger.info(f"Starting parallel frame extraction: {self.video_path}")

        # Get video duration and calculate chunks
        duration = self.get_video_duration()
        chunks = self.calculate_chunks(duration)

        logger.info(
            f"Video duration: {duration:.2f}s, processing in {len(chunks)} chunks"
        )

        # Process chunks in parallel
        chunk_results = []
        completed_chunks = 0

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # Submit all chunk extraction tasks
            future_to_chunk = {
                executor.submit(self.extract_chunk, start, end, i): (i, expected)
                for i, (start, end, expected) in enumerate(chunks)
            }

            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_id, expected_frames = future_to_chunk[future]

                try:
                    chunk_frames = future.result()
                    chunk_results.append((chunk_id, chunk_frames))
                    completed_chunks += 1

                    logger.debug(
                        f"Chunk {chunk_id} complete: {len(chunk_frames)} frames"
                    )

                    # Report progress
                    if self.progress_callback:
                        self.progress_callback(completed_chunks, len(chunks))

                except Exception as e:
                    logger.error(f"Chunk {chunk_id} failed: {e}")
                    chunk_results.append((chunk_id, []))

        # Sort results by chunk_id to maintain frame order
        chunk_results.sort(key=lambda x: x[0])
        frame_lists = [frames for _, frames in chunk_results]

        # Merge all chunks into final output
        total_frames = self.merge_chunks(frame_lists)

        logger.info(f"Parallel extraction complete: {total_frames} frames")
        return total_frames


def extract_frames_parallel(
    video_path: str,
    output_dir: str,
    width: int = 512,
    height: int = 288,
    ips: int = 1,
    chunk_duration: int = 10,
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> int:
    """Convenience function for parallel frame extraction."""
    extractor = ParallelFrameExtractor(
        video_path=video_path,
        output_dir=output_dir,
        width=width,
        height=height,
        ips=ips,
        chunk_duration=chunk_duration,
        max_workers=max_workers,
        progress_callback=progress_callback,
    )

    return extractor.extract_parallel()
