"""Tests for parallel frame extraction functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    import ffmpeg

    from msprites2.parallel_extractor import (
        ParallelFrameExtractor,
        extract_frames_parallel,
    )

    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg-python not available")
class TestParallelFrameExtractor:
    """Test the parallel frame extraction functionality."""

    def test_init_with_defaults(self, temp_dir, sample_video_path):
        """Test initialization with default parameters."""
        extractor = ParallelFrameExtractor(sample_video_path, temp_dir)

        assert extractor.video_path == sample_video_path
        assert extractor.output_dir == temp_dir
        assert extractor.width == 512
        assert extractor.height == 288
        assert extractor.ips == 1
        assert extractor.chunk_duration == 10
        assert extractor.max_workers is not None
        assert extractor.progress_callback is None

    def test_init_with_custom_params(self, temp_dir, sample_video_path):
        """Test initialization with custom parameters."""

        def progress_cb(completed, total):
            pass

        extractor = ParallelFrameExtractor(
            video_path=sample_video_path,
            output_dir=temp_dir,
            width=256,
            height=144,
            ips=2,
            chunk_duration=5,
            max_workers=2,
            progress_callback=progress_cb,
        )

        assert extractor.width == 256
        assert extractor.height == 144
        assert extractor.ips == 2
        assert extractor.chunk_duration == 5
        assert extractor.max_workers == 2
        assert extractor.progress_callback is progress_cb

    @patch("ffmpeg.probe")
    def test_get_video_duration(self, mock_probe, temp_dir, sample_video_path):
        """Test video duration detection."""
        mock_probe.return_value = {"format": {"duration": "120.5"}}

        extractor = ParallelFrameExtractor(sample_video_path, temp_dir)
        duration = extractor.get_video_duration()

        assert duration == 120.5
        mock_probe.assert_called_once_with(sample_video_path)

    @patch("ffmpeg.probe")
    def test_get_video_duration_error(self, mock_probe, temp_dir, sample_video_path):
        """Test video duration detection with error."""
        mock_probe.side_effect = ffmpeg.Error("cmd", "stdout", "stderr")

        extractor = ParallelFrameExtractor(sample_video_path, temp_dir)

        with pytest.raises(ffmpeg.Error):
            extractor.get_video_duration()

    def test_calculate_chunks(self, temp_dir, sample_video_path):
        """Test chunk calculation logic."""
        extractor = ParallelFrameExtractor(
            sample_video_path, temp_dir, ips=1, chunk_duration=10
        )

        # Test video duration that divides evenly
        chunks = extractor.calculate_chunks(30.0)
        assert len(chunks) == 3
        assert chunks[0] == (0.0, 10.0, 10)
        assert chunks[1] == (10.0, 20.0, 10)
        assert chunks[2] == (20.0, 30.0, 10)

    def test_calculate_chunks_partial(self, temp_dir, sample_video_path):
        """Test chunk calculation with partial last chunk."""
        extractor = ParallelFrameExtractor(
            sample_video_path, temp_dir, ips=2, chunk_duration=10
        )

        chunks = extractor.calculate_chunks(25.0)
        assert len(chunks) == 3
        assert chunks[0] == (0.0, 10.0, 5)  # 10s / 2s per frame = 5 frames
        assert chunks[1] == (10.0, 20.0, 5)
        assert chunks[2] == (20.0, 25.0, 2)  # 5s / 2s per frame = 2.5 -> 2 frames

    @patch("ffmpeg.run")
    @patch("os.path.exists")
    @patch("pathlib.Path.glob")
    def test_extract_chunk_success(
        self, mock_glob, mock_exists, mock_run, temp_dir, sample_video_path
    ):
        """Test successful chunk extraction."""
        # Mock successful extraction
        mock_run.return_value = None
        mock_exists.return_value = True

        # Mock found frames
        mock_frames = [Path(f"/tmp/chunk_0_{i:04d}.jpg") for i in range(1, 6)]
        mock_glob.return_value = mock_frames

        extractor = ParallelFrameExtractor(sample_video_path, temp_dir)

        result = extractor.extract_chunk(0.0, 10.0, 0)

        assert len(result) == 5
        assert all(str(frame) in result for frame in mock_frames)
        mock_run.assert_called_once()

    @patch("ffmpeg.run")
    def test_extract_chunk_ffmpeg_error(self, mock_run, temp_dir, sample_video_path):
        """Test chunk extraction with FFmpeg error."""
        mock_run.side_effect = ffmpeg.Error("cmd", "stdout", "stderr")

        extractor = ParallelFrameExtractor(sample_video_path, temp_dir)
        result = extractor.extract_chunk(0.0, 10.0, 0)

        assert result == []

    def test_merge_chunks(self, temp_dir, sample_video_path):
        """Test merging chunk results."""
        extractor = ParallelFrameExtractor(sample_video_path, temp_dir)

        # Create temporary chunk files
        chunk_dir1 = tempfile.mkdtemp(prefix="chunk_0_")
        chunk_dir2 = tempfile.mkdtemp(prefix="chunk_1_")

        frame1 = os.path.join(chunk_dir1, "0001.jpg")
        frame2 = os.path.join(chunk_dir1, "0002.jpg")
        frame3 = os.path.join(chunk_dir2, "0001.jpg")

        # Create mock frame files
        for frame in [frame1, frame2, frame3]:
            Path(frame).touch()

        chunk_results = [
            [frame1, frame2],  # Chunk 0
            [frame3],  # Chunk 1
        ]

        total_frames = extractor.merge_chunks(chunk_results)

        assert total_frames == 3
        assert os.path.exists(os.path.join(temp_dir, "0001.jpg"))
        assert os.path.exists(os.path.join(temp_dir, "0002.jpg"))
        assert os.path.exists(os.path.join(temp_dir, "0003.jpg"))

    @patch("msprites2.parallel_extractor.ParallelFrameExtractor.get_video_duration")
    @patch("msprites2.parallel_extractor.ParallelFrameExtractor.extract_chunk")
    def test_extract_parallel(
        self, mock_extract_chunk, mock_duration, temp_dir, sample_video_path
    ):
        """Test parallel extraction workflow."""
        mock_duration.return_value = 20.0
        mock_extract_chunk.side_effect = [
            ["/tmp/frame1.jpg", "/tmp/frame2.jpg"],  # Chunk 0
            ["/tmp/frame3.jpg", "/tmp/frame4.jpg"],  # Chunk 1
        ]

        extractor = ParallelFrameExtractor(
            sample_video_path, temp_dir, chunk_duration=10
        )

        # Mock the merge_chunks method to avoid file operations
        with patch.object(extractor, "merge_chunks", return_value=4) as mock_merge:
            result = extractor.extract_parallel()

            assert result == 4
            assert mock_extract_chunk.call_count == 2
            mock_merge.assert_called_once()

    def test_progress_callback(self, temp_dir, sample_video_path):
        """Test progress callback functionality."""
        progress_calls = []

        def progress_callback(completed, total):
            progress_calls.append((completed, total))

        extractor = ParallelFrameExtractor(
            sample_video_path, temp_dir, progress_callback=progress_callback
        )

        # Mock the extraction to test callback
        with patch.object(extractor, "get_video_duration", return_value=20.0):
            with patch.object(extractor, "extract_chunk", return_value=[]):
                with patch.object(extractor, "merge_chunks", return_value=0):
                    extractor.extract_parallel()

        # Should have received progress updates
        assert len(progress_calls) > 0
        # Final call should be (total_chunks, total_chunks)
        assert progress_calls[-1][0] == progress_calls[-1][1]

    def test_convenience_function(self, temp_dir, sample_video_path):
        """Test the convenience extract_frames_parallel function."""
        with patch(
            "msprites2.parallel_extractor.ParallelFrameExtractor"
        ) as mock_extractor_class:
            mock_extractor = MagicMock()
            mock_extractor.extract_parallel.return_value = 5
            mock_extractor_class.return_value = mock_extractor

            result = extract_frames_parallel(sample_video_path, temp_dir)

            assert result == 5
            mock_extractor_class.assert_called_once_with(
                video_path=sample_video_path,
                output_dir=temp_dir,
                width=512,
                height=288,
                ips=1,
                chunk_duration=10,
                max_workers=None,
                progress_callback=None,
            )
            mock_extractor.extract_parallel.assert_called_once()


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg-python not available")
class TestParallelIntegration:
    """Integration tests for parallel processing with MontageSprites."""

    def test_montage_sprites_parallel_integration(self, temp_dir, sample_video_path):
        """Test parallel processing integration with MontageSprites."""
        from msprites2 import MontageSprites

        sprite = MontageSprites(sample_video_path, temp_dir)

        # Mock the parallel extractor to avoid actual video processing
        with patch(
            "msprites2.parallel_extractor.extract_frames_parallel"
        ) as mock_extract:
            mock_extract.return_value = 5

            sprite.generate_thumbs(parallel=True)

            mock_extract.assert_called_once_with(
                video_path=sample_video_path,
                output_dir=temp_dir,
                width=512,
                height=288,
                ips=1,
                progress_callback=None,
            )

    def test_from_media_parallel(self, temp_dir, sample_video_path):
        """Test from_media with parallel processing."""
        from msprites2 import MontageSprites

        os.makedirs(temp_dir, exist_ok=True)
        sprite_file = os.path.join(temp_dir, "sprite.jpg")
        webvtt_file = os.path.join(temp_dir, "sprite.webvtt")

        with patch(
            "msprites2.parallel_extractor.extract_frames_parallel"
        ) as mock_extract:
            with patch("subprocess.run"):  # Mock ImageMagick call
                mock_extract.return_value = 5

                result = MontageSprites.from_media(
                    video_path=sample_video_path,
                    thumbnail_dir=temp_dir,
                    sprite_file=sprite_file,
                    webvtt_file=webvtt_file,
                    parallel=True,
                )

                assert isinstance(result, MontageSprites)
                mock_extract.assert_called_once()


class TestMissingDependency:
    """Test behavior when ffmpeg-python is not available."""

    def test_import_error_handling(self, temp_dir, sample_video_path):
        """Test graceful handling of missing ffmpeg-python dependency."""
        from msprites2 import MontageSprites

        sprite = MontageSprites(sample_video_path, temp_dir)

        # Mock sys.modules to simulate missing parallel_extractor module
        import sys
        original_modules = sys.modules.copy()
        
        try:
            # Remove the parallel_extractor module if it exists
            if 'msprites2.parallel_extractor' in sys.modules:
                del sys.modules['msprites2.parallel_extractor']
            
            # Mock the module import to raise ImportError
            def mock_import(name, *args, **kwargs):
                if 'parallel_extractor' in name:
                    raise ImportError("No module named 'ffmpeg'")
                return original_import(name, *args, **kwargs)
            
            original_import = __builtins__['__import__']
            __builtins__['__import__'] = mock_import
            
            # Should fall back to sequential processing without error
            with patch("subprocess.run") as mock_run:
                sprite.generate_thumbs(parallel=True)
                # Should have fallen back to sequential extraction
                mock_run.assert_called_once()
                
        finally:
            # Restore original state
            __builtins__['__import__'] = original_import
            sys.modules.clear()
            sys.modules.update(original_modules)
    
    def test_streaming_import_error(self, temp_dir, sample_video_path):
        """Test streaming extraction with missing ffmpeg-python dependency."""
        from msprites2 import MontageSprites

        sprite = MontageSprites(sample_video_path, temp_dir)

        # Mock sys.modules to simulate missing parallel_extractor module
        import sys
        original_modules = sys.modules.copy()
        
        try:
            # Remove the parallel_extractor module if it exists
            if 'msprites2.parallel_extractor' in sys.modules:
                del sys.modules['msprites2.parallel_extractor']
            
            # Mock the module import to raise ImportError
            def mock_import(name, *args, **kwargs):
                if 'parallel_extractor' in name:
                    raise ImportError("No module named 'ffmpeg'")
                return original_import(name, *args, **kwargs)
            
            original_import = __builtins__['__import__']
            __builtins__['__import__'] = mock_import
            
            # Should raise ImportError with helpful message
            with pytest.raises(ImportError, match="ffmpeg-python required for streaming extraction"):
                list(sprite.extract_streaming())
                
        finally:
            # Restore original state
            __builtins__['__import__'] = original_import
            sys.modules.clear()
            sys.modules.update(original_modules)
