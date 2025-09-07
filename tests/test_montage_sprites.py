import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from msprites2.montage_sprites import (
    MontageSprites,
)


class TestMontageSprites:
    """Test the MontageSprites class."""

    def test_init_creates_directory_if_not_exists(self, temp_dir, sample_video_path):
        """Test that __init__ creates thumbnail directory if it doesn't exist."""
        thumb_dir = os.path.join(temp_dir, "new_thumbnails")

        sprite = MontageSprites(sample_video_path, thumb_dir)

        assert sprite.video_path == sample_video_path
        assert sprite.thumbnail_dir == thumb_dir
        assert os.path.isdir(thumb_dir)

    def test_init_with_existing_directory(self, sample_video_path, empty_thumbnail_dir):
        """Test that __init__ works with existing directory."""
        sprite = MontageSprites(sample_video_path, empty_thumbnail_dir)

        assert sprite.video_path == sample_video_path
        assert sprite.thumbnail_dir == empty_thumbnail_dir
        assert os.path.isdir(empty_thumbnail_dir)

    def test_frame_filename_returns_sprite_file(
        self, sample_video_path, empty_thumbnail_dir
    ):
        """Test that frame_filename returns the sprite_file."""
        sprite = MontageSprites(sample_video_path, empty_thumbnail_dir)
        sprite.sprite_file = "test_sprite.jpg"

        assert sprite.frame_filename(1) == "test_sprite.jpg"
        assert sprite.frame_filename(999) == "test_sprite.jpg"

    def test_count_files_empty_directory(self, sample_video_path, empty_thumbnail_dir):
        """Test file counting in empty directory."""
        sprite = MontageSprites(sample_video_path, empty_thumbnail_dir)

        assert sprite.count_files() == 0

    def test_count_files_with_files(self, sample_video_path, thumbnail_dir_with_files):
        """Test file counting with files present."""
        sprite = MontageSprites(sample_video_path, thumbnail_dir_with_files)

        assert sprite.count_files() == 5

    def test_count_files_ignores_directories(self, sample_video_path, temp_dir):
        """Test that count_files ignores subdirectories."""
        thumb_dir = os.path.join(temp_dir, "thumbnails")
        os.makedirs(thumb_dir)

        # Create files and directories
        Path(os.path.join(thumb_dir, "file1.jpg")).touch()
        Path(os.path.join(thumb_dir, "file2.jpg")).touch()
        os.makedirs(os.path.join(thumb_dir, "subdir"))

        sprite = MontageSprites(sample_video_path, thumb_dir)

        assert sprite.count_files() == 2

    @patch("subprocess.run")
    def test_generate_thumbs(self, mock_run, sample_video_path, empty_thumbnail_dir):
        """Test thumbnail generation command construction."""
        sprite = MontageSprites(sample_video_path, empty_thumbnail_dir)

        sprite.generate_thumbs()

        mock_run.assert_called_once()
        # Verify the command structure
        called_command = mock_run.call_args[0][0]
        assert "ffmpeg" in called_command
        assert "-loglevel" in called_command
        assert "error" in called_command
        assert sample_video_path in called_command

    @patch("subprocess.run")
    def test_generate_sprite(
        self, mock_run, sample_video_path, empty_thumbnail_dir, sample_sprite_file
    ):
        """Test sprite generation command construction."""
        sprite = MontageSprites(sample_video_path, empty_thumbnail_dir)

        result = sprite.generate_sprite(sample_sprite_file)

        mock_run.assert_called_once()
        # Verify the command structure
        called_command = mock_run.call_args[0][0]
        assert any("montage" in cmd for cmd in called_command)
        assert sample_sprite_file in called_command
        assert sprite.sprite_file == sample_sprite_file
        assert result is sprite  # Should return self

    def test_ips_seconds_to_timestamp(self, sample_video_path, empty_thumbnail_dir):
        """Test timestamp conversion."""
        sprite = MontageSprites(sample_video_path, empty_thumbnail_dir)

        assert sprite.ips_seconds_to_timestamp(0) == "00:00:00"
        assert sprite.ips_seconds_to_timestamp(60) == "00:01:00"
        assert sprite.ips_seconds_to_timestamp(3661) == "01:01:01"

    def test_webvtt_getx_coordinates(self, sample_video_path, empty_thumbnail_dir):
        """Test WebVTT X coordinate calculation."""
        sprite = MontageSprites(sample_video_path, empty_thumbnail_dir)
        w, h = 100, 50

        # Test first few positions in grid
        assert sprite.webvtt_getx(0, w, h) == 0  # First column
        assert sprite.webvtt_getx(1, w, h) == 100  # Second column
        assert sprite.webvtt_getx(29, w, h) == 2900  # Last column of first row
        assert sprite.webvtt_getx(30, w, h) == 0  # First column of second row

    def test_webvtt_gety_coordinates(self, sample_video_path, empty_thumbnail_dir):
        """Test WebVTT Y coordinate calculation."""
        sprite = MontageSprites(sample_video_path, empty_thumbnail_dir)
        w, h = 100, 50

        # Test first few positions in grid
        assert sprite.webvtt_gety(0, w, h) == 0  # First row
        assert sprite.webvtt_gety(1, w, h) == 0  # Still first row
        assert sprite.webvtt_gety(29, w, h) == 0  # Still first row
        assert sprite.webvtt_gety(30, w, h) == 50  # Second row
        assert sprite.webvtt_gety(60, w, h) == 100  # Third row

    def test_webvtt_content_structure(
        self, sample_video_path, thumbnail_dir_with_files, sample_sprite_file
    ):
        """Test WebVTT content generation structure."""
        sprite = MontageSprites(sample_video_path, thumbnail_dir_with_files)
        sprite.sprite_file = sample_sprite_file

        content = sprite.webvtt_content()

        assert content[0] == "WEBVTT\n"
        # Should have timeline and image entries for each file
        assert len(content) > 1
        # Check that it includes timeline format
        timeline_entries = [line for line in content if "-->" in line]
        assert len(timeline_entries) == 5  # One for each file

    def test_webvtt_content_timing(
        self, sample_video_path, thumbnail_dir_with_files, sample_sprite_file
    ):
        """Test WebVTT content timing progression."""
        sprite = MontageSprites(sample_video_path, thumbnail_dir_with_files)
        sprite.sprite_file = sample_sprite_file

        content = sprite.webvtt_content()

        # Find timeline entries
        timeline_entries = [line for line in content if "-->" in line]

        # First entry should start at 00:00:00
        assert "00:00:00 --> 00:00:01" in timeline_entries[0]
        # Second entry should be sequential
        assert "00:00:01 --> 00:00:02" in timeline_entries[1]

    def test_generate_webvtt_file_creation(
        self,
        sample_video_path,
        thumbnail_dir_with_files,
        sample_webvtt_file,
        sample_sprite_file,
    ):
        """Test WebVTT file generation."""
        sprite = MontageSprites(sample_video_path, thumbnail_dir_with_files)
        sprite.sprite_file = sample_sprite_file

        sprite.generate_webvtt(sample_webvtt_file)

        assert os.path.exists(sample_webvtt_file)
        with open(sample_webvtt_file) as f:
            content = f.read()
            assert content.startswith("WEBVTT\n")
            assert "-->" in content
            assert "#xywh=" in content

    def test_from_media_validates_thumbnail_dir_existence(
        self, sample_video_path, sample_sprite_file, sample_webvtt_file
    ):
        """Test that from_media validates thumbnail directory existence."""
        with pytest.raises(Exception, match="doesn't exist"):
            MontageSprites.from_media(
                sample_video_path,
                "/nonexistent/directory",
                sample_sprite_file,
                sample_webvtt_file,
            )

    def test_from_media_validates_empty_thumbnail_dir(
        self,
        sample_video_path,
        thumbnail_dir_with_files,
        sample_sprite_file,
        sample_webvtt_file,
    ):
        """Test that from_media validates thumbnail directory is empty."""
        with pytest.raises(Exception, match="There are already files"):
            MontageSprites.from_media(
                sample_video_path,
                thumbnail_dir_with_files,
                sample_sprite_file,
                sample_webvtt_file,
            )

    @patch("msprites2.montage_sprites.MontageSprites.generate_thumbs")
    @patch("msprites2.montage_sprites.MontageSprites.generate_sprite")
    @patch("msprites2.montage_sprites.MontageSprites.generate_webvtt")
    def test_from_media_workflow(
        self,
        mock_webvtt,
        mock_sprite,
        mock_thumbs,
        sample_video_path,
        empty_thumbnail_dir,
        sample_sprite_file,
        sample_webvtt_file,
    ):
        """Test that from_media executes the full workflow."""
        mock_sprite.return_value = MagicMock()

        result = MontageSprites.from_media(
            sample_video_path,
            empty_thumbnail_dir,
            sample_sprite_file,
            sample_webvtt_file,
        )

        mock_thumbs.assert_called_once()
        mock_sprite.assert_called_once_with(sample_sprite_file)
        mock_webvtt.assert_called_once_with(sample_webvtt_file)
        assert isinstance(result, MontageSprites)

    def test_class_constants(self):
        """Test that class constants are set correctly."""
        assert MontageSprites.IPS == 1
        assert MontageSprites.WIDTH == 512
        assert MontageSprites.HEIGHT == 288
        assert MontageSprites.ROWS == 30
        assert MontageSprites.COLS == 30
        assert MontageSprites.FILENAME_FORMAT == "%04d.jpg"
        assert MontageSprites.WEBVTT_HEADER == "WEBVTT\n"
        assert MontageSprites.WEBVTT_TIME_FORMAT == "%H:%M:%S"

    def test_webvtt_formats(self):
        """Test WebVTT format strings."""
        assert "{start} --> {end}\n" == MontageSprites.WEBVTT_TIMELINE_FORMAT
        assert (
            "{filename}#xywh={x},{y},{w},{h}\n\n"
            == MontageSprites.WEBVTT_IMAGE_TITLE_FORMAT
        )
