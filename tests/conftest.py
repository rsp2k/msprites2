import os
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def empty_thumbnail_dir(temp_dir):
    """Create an empty thumbnail directory for testing."""
    thumb_dir = os.path.join(temp_dir, "thumbnails")
    os.makedirs(thumb_dir)
    return thumb_dir


@pytest.fixture
def thumbnail_dir_with_files(temp_dir):
    """Create a thumbnail directory with some test files."""
    thumb_dir = os.path.join(temp_dir, "thumbnails_with_files")
    os.makedirs(thumb_dir)

    # Create some dummy thumbnail files
    for i in range(5):
        filename = f"{i:04d}.jpg"
        filepath = os.path.join(thumb_dir, filename)
        Path(filepath).touch()

    return thumb_dir


@pytest.fixture
def sample_video_path():
    """Return a sample video path (doesn't need to exist for unit tests)."""
    return "/tmp/sample_video.mp4"


@pytest.fixture
def sample_sprite_file(temp_dir):
    """Return path for sample sprite file."""
    return os.path.join(temp_dir, "sprite.jpg")


@pytest.fixture
def sample_webvtt_file(temp_dir):
    """Return path for sample WebVTT file."""
    return os.path.join(temp_dir, "sprite.webvtt")


@pytest.fixture
def test_video_file(temp_dir):
    """Create a small test video using ffmpeg."""
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available for creating test video")

    video_path = os.path.join(temp_dir, "test_video.mp4")

    # Create a simple 5-second test video
    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=duration=5:size=320x240:rate=1",
        "-pix_fmt",
        "yuv420p",
        "-y",
        video_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return video_path
    except subprocess.CalledProcessError:
        pytest.skip("Failed to create test video with ffmpeg")
