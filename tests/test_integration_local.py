import os
import shutil

import pytest

from msprites2 import MontageSprites


class TestIntegrationLocal:
    """Fast integration tests using locally generated video."""

    @pytest.mark.slow
    def test_full_workflow_with_generated_video(self, test_video_file, temp_dir):
        """Test the complete workflow with a locally generated video."""
        # Skip if no ffmpeg or magick
        if not (
            shutil.which("ffmpeg")
            and (shutil.which("magick") or shutil.which("montage"))
        ):
            pytest.skip("ffmpeg and ImageMagick are required for integration tests")

        thumbnail_dir = os.path.join(temp_dir, "thumbnails")
        os.makedirs(thumbnail_dir)

        sprite_file = os.path.join(temp_dir, "sprite.jpg")
        webvtt_file = os.path.join(temp_dir, "sprite.webvtt")

        # Execute the full workflow
        MontageSprites.from_media(
            video_path=test_video_file,
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
