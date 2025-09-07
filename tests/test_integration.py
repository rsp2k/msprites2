import os
import shutil
from pathlib import Path
from urllib.request import urlretrieve

import pytest

from msprites2 import MontageSprites


@pytest.fixture(scope="session")
def test_video_path(tmp_path_factory):
    """Download a small test video for integration testing."""
    test_video_url = (
        "https://sample-videos.com/zip/10/mp4/480/big_buck_bunny_480p_5s.mp4"
    )
    video_filename = "big_buck_bunny_480p_5s.mp4"

    # Use session temp directory to avoid re-downloading
    session_temp = tmp_path_factory.mktemp("test_videos")
    video_path = session_temp / video_filename

    if not video_path.exists():
        try:
            print(f"Downloading test video: {video_filename}")
            urlretrieve(test_video_url, video_path)
            print(f"Downloaded to: {video_path}")
        except Exception as e:
            pytest.skip(f"Could not download test video: {e}")

    return str(video_path)


@pytest.fixture
def integration_temp_dir(tmp_path):
    """Create a temp directory for integration tests."""
    return str(tmp_path)


class TestIntegration:
    """Integration tests that test the full workflow with real video files."""

    @pytest.mark.slow
    def test_full_workflow_with_real_video(self, test_video_path, integration_temp_dir):
        """Test the complete workflow with a real video file."""
        # Skip if no ffmpeg or magick
        if not (
            shutil.which("ffmpeg")
            and (shutil.which("magick") or shutil.which("montage"))
        ):
            pytest.skip("ffmpeg and ImageMagick are required for integration tests")

        thumbnail_dir = os.path.join(integration_temp_dir, "thumbnails")
        os.makedirs(thumbnail_dir)

        sprite_file = os.path.join(integration_temp_dir, "sprite.jpg")
        webvtt_file = os.path.join(integration_temp_dir, "sprite.webvtt")

        # Execute the full workflow
        MontageSprites.from_media(
            video_path=test_video_path,
            thumbnail_dir=thumbnail_dir,
            sprite_file=sprite_file,
            webvtt_file=webvtt_file,
        )

        # Verify thumbnail files were created
        thumb_files = os.listdir(thumbnail_dir)
        assert len(thumb_files) > 0, "No thumbnail files were created"

        # Verify all thumbnail files are images
        for thumb_file in thumb_files:
            assert thumb_file.endswith(".jpg"), f"Unexpected file type: {thumb_file}"

        # Verify sprite file was created
        assert os.path.exists(sprite_file), "Sprite file was not created"
        assert os.path.getsize(sprite_file) > 0, "Sprite file is empty"

        # Verify WebVTT file was created
        assert os.path.exists(webvtt_file), "WebVTT file was not created"
        assert os.path.getsize(webvtt_file) > 0, "WebVTT file is empty"

        # Verify WebVTT content structure
        with open(webvtt_file) as f:
            content = f.read()
            assert content.startswith("WEBVTT\n"), (
                "WebVTT file doesn't start with header"
            )
            assert "-->" in content, "WebVTT file doesn't contain timeline entries"
            assert "#xywh=" in content, (
                "WebVTT file doesn't contain coordinate information"
            )

            # Count timeline entries
            timeline_entries = content.count("-->")
            assert timeline_entries > 0, "No timeline entries found"
            assert timeline_entries == len(thumb_files), (
                "Timeline entries don't match thumbnail count"
            )

    @pytest.mark.slow
    def test_custom_settings_workflow(self, test_video_path, integration_temp_dir):
        """Test workflow with custom sprite settings."""
        if not (
            shutil.which("ffmpeg")
            and (shutil.which("magick") or shutil.which("montage"))
        ):
            pytest.skip("ffmpeg and ImageMagick are required for integration tests")

        thumbnail_dir = os.path.join(integration_temp_dir, "custom_thumbnails")
        os.makedirs(thumbnail_dir)

        sprite_file = os.path.join(integration_temp_dir, "custom_sprite.jpg")
        webvtt_file = os.path.join(integration_temp_dir, "custom_sprite.webvtt")

        # Create a sprite object with custom settings
        sprite = MontageSprites(test_video_path, thumbnail_dir)

        # Modify settings for smaller output
        sprite.WIDTH = 256
        sprite.HEIGHT = 144
        sprite.IPS = 2  # Extract frames every 2 seconds

        # Execute workflow steps manually
        sprite.generate_thumbs()
        sprite.generate_sprite(sprite_file)
        sprite.generate_webvtt(webvtt_file)

        # Verify results
        assert os.path.exists(sprite_file)
        assert os.path.exists(webvtt_file)

        # Verify WebVTT timing reflects custom IPS
        with open(webvtt_file) as f:
            content = f.read()
            # Should have 2-second intervals
            assert "00:00:02.000" in content, (
                "Custom IPS setting not reflected in WebVTT"
            )

    def test_empty_directory_validation(self, test_video_path, integration_temp_dir):
        """Test that the validation for empty directories works correctly."""
        thumbnail_dir = os.path.join(integration_temp_dir, "non_empty_thumbnails")
        os.makedirs(thumbnail_dir)

        # Add a file to make directory non-empty
        dummy_file = os.path.join(thumbnail_dir, "dummy.txt")
        Path(dummy_file).touch()

        sprite_file = os.path.join(integration_temp_dir, "sprite.jpg")
        webvtt_file = os.path.join(integration_temp_dir, "sprite.webvtt")

        # Should raise exception for non-empty directory
        with pytest.raises(Exception, match="There are already files"):
            MontageSprites.from_media(
                video_path=test_video_path,
                thumbnail_dir=thumbnail_dir,
                sprite_file=sprite_file,
                webvtt_file=webvtt_file,
            )

    def test_nonexistent_directory_validation(
        self, test_video_path, integration_temp_dir
    ):
        """Test validation for non-existent directories."""
        thumbnail_dir = os.path.join(integration_temp_dir, "nonexistent")
        sprite_file = os.path.join(integration_temp_dir, "sprite.jpg")
        webvtt_file = os.path.join(integration_temp_dir, "sprite.webvtt")

        # Should raise exception for non-existent directory
        with pytest.raises(Exception, match="doesn't exist"):
            MontageSprites.from_media(
                video_path=test_video_path,
                thumbnail_dir=thumbnail_dir,
                sprite_file=sprite_file,
                webvtt_file=webvtt_file,
            )

    @pytest.mark.slow
    def test_coordinate_calculation_accuracy(
        self, test_video_path, integration_temp_dir
    ):
        """Test that WebVTT coordinates are calculated correctly."""
        if not (
            shutil.which("ffmpeg")
            and (shutil.which("magick") or shutil.which("montage"))
        ):
            pytest.skip("ffmpeg and ImageMagick are required for integration tests")

        thumbnail_dir = os.path.join(integration_temp_dir, "coord_test_thumbnails")
        os.makedirs(thumbnail_dir)

        sprite_file = os.path.join(integration_temp_dir, "coord_sprite.jpg")
        webvtt_file = os.path.join(integration_temp_dir, "coord_sprite.webvtt")

        # Create sprite with known dimensions
        sprite = MontageSprites(test_video_path, thumbnail_dir)
        sprite.WIDTH = 100
        sprite.HEIGHT = 50
        sprite.ROWS = 5
        sprite.COLS = 5

        sprite.generate_thumbs()
        sprite.generate_sprite(sprite_file)
        sprite.generate_webvtt(webvtt_file)

        # Parse WebVTT and verify coordinates
        with open(webvtt_file) as f:
            content = f.read()

            lines = content.split("\n")
            coord_lines = [line for line in lines if "#xywh=" in line]

            if coord_lines:
                # First thumbnail should be at 0,0
                first_coord = coord_lines[0]
                assert "xywh=0,0,100,50" in first_coord, (
                    f"First coordinate incorrect: {first_coord}"
                )

                # If we have a second thumbnail, it should be at 100,0
                if len(coord_lines) > 1:
                    second_coord = coord_lines[1]
                    assert "xywh=100,0,100,50" in second_coord, (
                        f"Second coordinate incorrect: {second_coord}"
                    )
