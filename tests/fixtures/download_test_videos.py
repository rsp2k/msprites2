#!/usr/bin/env python3
"""
Download small test videos for integration testing.
"""

import urllib.request
from pathlib import Path

# Small open source test videos
TEST_VIDEOS = {
    "big_buck_bunny_480p_5s.mp4": {
        "url": "https://sample-videos.com/zip/10/mp4/480/big_buck_bunny_480p_5s.mp4",
        "description": "Big Buck Bunny 480p 5 seconds",
    },
    "sample_960x400_ocean_with_audio.mp4": {
        "url": "https://sample-videos.com/zip/10/mp4/480/sample_960x400_ocean_with_audio.mp4",
        "description": "Ocean sample with audio",
    },
}


def download_test_videos(fixtures_dir=None):
    """Download test videos to fixtures directory."""
    if fixtures_dir is None:
        fixtures_dir = Path(__file__).parent

    fixtures_dir = Path(fixtures_dir)
    fixtures_dir.mkdir(exist_ok=True)

    for filename, info in TEST_VIDEOS.items():
        filepath = fixtures_dir / filename

        if filepath.exists():
            print(f"✓ {filename} already exists")
            continue

        print(f"Downloading {filename}...")
        try:
            urllib.request.urlretrieve(info["url"], filepath)
            print(f"✓ Downloaded {filename} ({info['description']})")
        except Exception as e:
            print(f"✗ Failed to download {filename}: {e}")

    print(f"\nTest videos in: {fixtures_dir}")


if __name__ == "__main__":
    download_test_videos()
