import logging
import os
import shlex
import shutil
import subprocess
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


FFMPEG_THUMBNAIL_COMMAND = """
    ffmpeg -loglevel error -i {input} -r 1/{ips} -vf scale={width}:{height} {output}
"""

MONTAGE_COMMAND = """montage -background '#336699' -tile {rows}x{cols} -geometry {width}x{height}+0+0 {input}/* {output}"""
# Check for imagemagick6
if shutil.which("magick"):
    MONTAGE_COMMAND = "magick " + MONTAGE_COMMAND


class MontageSprites:
    IPS = 1  #  will be used as 1 in every 5 sec
    WIDTH = 512
    HEIGHT = 288
    ROWS = 30
    COLS = 30
    FILENAME_FORMAT = "%04d.jpg"

    WEBVTT_HEADER = "WEBVTT\n"
    WEBVTT_TIME_FORMAT = "%H:%M:%S"
    WEBVTT_TIMELINE_FORMAT = "{start} --> {end}\n"
    WEBVTT_IMAGE_TITLE_FORMAT = "{filename}#xywh={x},{y},{w},{h}\n\n"

    video_path = None
    thumbnail_dir = None
    sprite_file = None

    def __init__(self, video_path, thumbnail_dir):
        self.video_path = video_path
        self.thumbnail_dir = thumbnail_dir
        if not os.path.isdir(self.thumbnail_dir):
            os.mkdir(self.thumbnail_dir, mode=0o777)

    def frame_filename(self, number):
        return self.sprite_file

    def count_files(self):
        count = 0
        for path in os.scandir(self.thumbnail_dir):
            if path.is_file():
                count += 1
        return count

    def generate_thumbs(
        self,
        parallel: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        """Generate thumbnail frames from video.

        Args:
            parallel: Use parallel extraction for better performance (default: False for compatibility)
            progress_callback: Optional callback for progress reporting (parallel mode only)
        """
        if parallel:
            try:
                from .parallel_extractor import extract_frames_parallel

                frame_count = extract_frames_parallel(
                    video_path=self.video_path,
                    output_dir=self.thumbnail_dir,
                    width=self.WIDTH,
                    height=self.HEIGHT,
                    ips=self.IPS,
                    progress_callback=progress_callback,
                )
                logger.info(f"Parallel extraction complete: {frame_count} frames")
                return
            except ImportError:
                logger.warning(
                    "ffmpeg-python not available, falling back to sequential extraction"
                )

        # Original sequential extraction
        output = os.path.join(self.thumbnail_dir, self.FILENAME_FORMAT)
        cmd = FFMPEG_THUMBNAIL_COMMAND.format(
            input=self.video_path,
            ips=self.IPS,
            width=self.WIDTH,
            height=self.HEIGHT,
            output=output,
        )

        logger.debug(f"ffmpeg generate thumbnails [{cmd}]")
        result = subprocess.run(shlex.split(cmd))
        logger.debug(f"ffmpeg generate thumbnails [{cmd}]\n{result}")

    def generate_sprite(self, sprite_file):
        self.sprite_file = sprite_file
        cmd = MONTAGE_COMMAND.format(
            rows=self.ROWS,
            cols=self.COLS,
            width=self.WIDTH,
            height=self.HEIGHT,
            input=self.thumbnail_dir,
            output=sprite_file,
        )
        subprocess.run(shlex.split(cmd))

        return self

    def ips_seconds_to_timestamp(self, ips):
        return time.strftime(self.WEBVTT_TIME_FORMAT, time.gmtime(ips))

    def webvtt_getx(self, imnumber, w, h):
        # coordinate in sprite image for a given image
        gridsize = self.ROWS * self.COLS
        imnumber = imnumber - ((imnumber // gridsize) * gridsize)
        windex = imnumber % self.COLS
        return windex * w

    def webvtt_gety(self, imnumber, w, h):
        # coordinate in sprite image for a given image
        gridsize = self.ROWS * self.COLS
        imnumber = imnumber - ((imnumber // gridsize) * gridsize)
        hindex = imnumber // self.ROWS
        return hindex * h

    def webvtt_content(self):
        contents = [self.WEBVTT_HEADER]
        file_name = os.path.split(self.sprite_file)[1]
        start, end = 0, self.IPS
        w, h = self.WIDTH, self.HEIGHT
        for i in range(0, self.count_files()):
            contents += [
                self.WEBVTT_TIMELINE_FORMAT.format(
                    start=self.ips_seconds_to_timestamp(start),
                    end=self.ips_seconds_to_timestamp(end),
                ),
                self.WEBVTT_IMAGE_TITLE_FORMAT.format(
                    x=self.webvtt_getx(i, w, h),
                    y=self.webvtt_gety(i, w, h),
                    w=w,
                    h=h,
                    filename=file_name,
                ),
            ]
            start = end
            end += self.IPS
        return contents

    def generate_webvtt(self, webvtt_file):
        with open(webvtt_file, "w") as f:
            f.writelines(self.webvtt_content())

    @classmethod
    def from_media(
        cls,
        video_path,
        thumbnail_dir,
        sprite_file,
        webvtt_file,
        delete_existing_thumbnail_dir=False,
        parallel=False,
        progress_callback=None,
    ):
        """Create sprites from media file.

        Args:
            video_path: Path to input video
            thumbnail_dir: Directory for extracted frames
            sprite_file: Output sprite sheet path
            webvtt_file: Output WebVTT file path
            delete_existing_thumbnail_dir: Whether to clear existing files
            parallel: Use parallel frame extraction (default: False)
            progress_callback: Progress reporting function for parallel mode
        """
        if os.path.isdir(thumbnail_dir):
            if os.listdir(thumbnail_dir):
                raise Exception(f"There are already files in {thumbnail_dir}!")
        else:
            raise Exception(
                f"{thumbnail_dir} doesn't exist, create it before calling MontageSprites.from_media()"
            )

        montage = MontageSprites(
            video_path=video_path,
            thumbnail_dir=thumbnail_dir,
        )
        montage.generate_thumbs(parallel=parallel, progress_callback=progress_callback)
        montage.generate_sprite(sprite_file)
        montage.generate_webvtt(webvtt_file)
        return montage

    def extract_streaming(
        self, frame_processor: Optional[Callable[[str, int], str]] = None
    ):
        """Extract frames with streaming processing for real-time ML pipelines.

        Yields frames as they're extracted, perfect for neural networks,
        style transfer, or other frame-by-frame processing.

        Args:
            frame_processor: Optional function to process each frame

        Yields:
            Tuple[str, int]: (frame_path, frame_number)

        Example:
            >>> def apply_style_transfer(frame_path, frame_num):
            ...     # Your ML model here
            ...     return f"styled_{frame_num:04d}.jpg"

            >>> sprite = MontageSprites("video.mp4", "frames/")
            >>> for frame_path, num in sprite.extract_streaming(apply_style_transfer):
            ...     print(f"Processed frame {num}")
        """
        try:
            from .parallel_extractor import ParallelFrameExtractor

            extractor = ParallelFrameExtractor(
                video_path=self.video_path,
                output_dir=self.thumbnail_dir,
                width=self.WIDTH,
                height=self.HEIGHT,
                ips=self.IPS,
            )

            yield from extractor.extract_streaming(frame_processor)

        except ImportError as e:
            raise ImportError(
                "ffmpeg-python required for streaming extraction. Install with: pip install ffmpeg-python"
            ) from e
