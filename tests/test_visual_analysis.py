"""Tests for visual analysis module."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Check if ollama is available
try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


# Test fixtures
@pytest.fixture
def temp_frames_dir():
    """Create a temporary directory with mock frame files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        frames_dir = Path(tmpdir) / "frames"
        frames_dir.mkdir()

        # Create some dummy frame files
        for i in range(1, 6):
            frame_file = frames_dir / f"frame_{i:04d}.jpg"
            frame_file.write_text(f"dummy frame {i}")

        yield str(frames_dir)


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestFrameDescription:
    """Tests for FrameDescription class."""

    def test_import_without_ollama(self):
        """Test that FrameDescription can be imported independently."""
        from msprites2.visual_analysis import FrameDescription

        desc = FrameDescription(
            frame_number=1,
            timestamp=0.0,
            description="A person walking",
            frame_path="frame_001.jpg",
        )
        assert desc.frame_number == 1
        assert desc.timestamp == 0.0
        assert desc.description == "A person walking"
        assert desc.frame_path == "frame_001.jpg"

    def test_timestamp_formatting(self):
        """Test WebVTT timestamp formatting."""
        from msprites2.visual_analysis import FrameDescription

        desc = FrameDescription(
            frame_number=1, timestamp=0.0, description="test", frame_path="test.jpg"
        )

        # Test various timestamp formats
        assert desc.to_webvtt_timestamp(0.0) == "00:00:00.000"
        assert desc.to_webvtt_timestamp(1.5) == "00:00:01.500"
        assert desc.to_webvtt_timestamp(61.25) == "00:01:01.250"
        assert desc.to_webvtt_timestamp(3661.123) == "01:01:01.123"

    def test_webvtt_cue_format(self):
        """Test WebVTT cue block formatting."""
        from msprites2.visual_analysis import FrameDescription

        desc = FrameDescription(
            frame_number=1,
            timestamp=1.5,
            description="A scenic mountain view.",
            frame_path="frame_001.jpg",
        )
        cue = desc.to_webvtt_cue(duration=2.0)

        assert "00:00:01.500 --> 00:00:03.500" in cue
        assert "A scenic mountain view." in cue
        assert cue.endswith("\n")


class TestVisualAnalyzerInit:
    """Tests for VisualAnalyzer initialization."""

    def test_import_error_without_ollama(self):
        """Test that VisualAnalyzer raises ImportError without ollama."""
        # Mock the import to simulate missing package
        with patch.dict(sys.modules, {"ollama": None}):
            # Clear any cached imports
            if "msprites2.visual_analysis" in sys.modules:
                del sys.modules["msprites2.visual_analysis"]

            from msprites2.visual_analysis import VisualAnalyzer

            with pytest.raises(ImportError) as exc_info:
                VisualAnalyzer()

            assert "ollama is required" in str(exc_info.value)
            assert "pip install msprites2[ai]" in str(exc_info.value)

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_initialization_with_defaults(self):
        """Test default initialization parameters."""
        from msprites2.visual_analysis import VisualAnalyzer

        with patch("ollama.Client"):
            analyzer = VisualAnalyzer()

            assert analyzer.model == "llava:7b"
            assert analyzer.ollama_host == "https://ollama.l.supported.systems"
            assert analyzer.fps == 1.0
            assert analyzer.prompt == VisualAnalyzer.DEFAULT_PROMPT

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        from msprites2.visual_analysis import VisualAnalyzer

        with patch("ollama.Client"):
            analyzer = VisualAnalyzer(
                model="moondream",
                ollama_host="http://localhost:11434",
                fps=2.0,
                prompt="What's in this image?",
            )

            assert analyzer.model == "moondream"
            assert analyzer.ollama_host == "http://localhost:11434"
            assert analyzer.fps == 2.0
            assert analyzer.prompt == "What's in this image?"


class TestVisualAnalyzerMethods:
    """Tests for VisualAnalyzer methods."""

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_analyze_frame_nonexistent_file(self):
        """Test analysis with nonexistent frame file."""
        from msprites2.visual_analysis import VisualAnalyzer

        with patch("ollama.Client"):
            analyzer = VisualAnalyzer()

            with pytest.raises(FileNotFoundError) as exc_info:
                analyzer.analyze_frame("/nonexistent/frame.jpg", 1)

            assert "Frame not found" in str(exc_info.value)

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_analyze_frame_with_mock(self, temp_frames_dir):
        """Test frame analysis with mocked Ollama response."""
        from msprites2.visual_analysis import VisualAnalyzer

        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "A beautiful landscape with mountains."}
        }

        with patch("ollama.Client", return_value=mock_client):
            analyzer = VisualAnalyzer(fps=1.0)

            frame_path = Path(temp_frames_dir) / "frame_0001.jpg"
            desc = analyzer.analyze_frame(str(frame_path), 1)

            assert desc.frame_number == 1
            assert desc.timestamp == 1.0  # frame 1 at 1 fps = 1 second
            assert "mountains" in desc.description.lower()
            assert desc.frame_path == str(frame_path)

            # Verify Ollama was called correctly
            mock_client.chat.assert_called_once()
            call_args = mock_client.chat.call_args[1]
            assert call_args["model"] == "llava:7b"
            assert len(call_args["messages"]) == 1
            assert str(frame_path) in call_args["messages"][0]["images"]

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_analyze_frames_directory(self, temp_frames_dir):
        """Test analyzing all frames in a directory."""
        from msprites2.visual_analysis import VisualAnalyzer

        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "Test description."}
        }

        with patch("ollama.Client", return_value=mock_client):
            analyzer = VisualAnalyzer()

            descriptions = analyzer.analyze_frames(temp_frames_dir)

            assert len(descriptions) == 5  # 5 frames created in fixture
            assert all(isinstance(d.description, str) for d in descriptions)
            assert descriptions[0].frame_number == 1
            assert descriptions[4].frame_number == 5

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_analyze_frames_with_max_limit(self, temp_frames_dir):
        """Test analyzing with max_frames limit."""
        from msprites2.visual_analysis import VisualAnalyzer

        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "Test."}}

        with patch("ollama.Client", return_value=mock_client):
            analyzer = VisualAnalyzer()

            descriptions = analyzer.analyze_frames(temp_frames_dir, max_frames=3)

            assert len(descriptions) == 3  # Only first 3 frames

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_progress_callback(self, temp_frames_dir):
        """Test progress callback functionality."""
        from msprites2.visual_analysis import VisualAnalyzer

        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "Test."}}

        progress_updates = []

        def callback(current, total):
            progress_updates.append((current, total))

        with patch("ollama.Client", return_value=mock_client):
            analyzer = VisualAnalyzer()

            analyzer.analyze_frames(temp_frames_dir, progress_callback=callback)

            assert len(progress_updates) == 5  # 5 frames
            assert progress_updates[0] == (1, 5)
            assert progress_updates[4] == (5, 5)

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_save_webvtt(self, temp_output_dir):
        """Test saving WebVTT file."""
        from msprites2.visual_analysis import VisualAnalyzer, FrameDescription

        with patch("ollama.Client"):
            analyzer = VisualAnalyzer()

            descriptions = [
                FrameDescription(1, 0.0, "First frame description", "frame_001.jpg"),
                FrameDescription(2, 1.0, "Second frame description", "frame_002.jpg"),
                FrameDescription(3, 2.0, "Third frame description", "frame_003.jpg"),
            ]

            output_path = os.path.join(temp_output_dir, "descriptions.vtt")
            analyzer.save_webvtt(descriptions, output_path)

            assert os.path.exists(output_path)

            with open(output_path, encoding="utf-8") as f:
                content = f.read()

            # Check WebVTT header
            assert content.startswith("WEBVTT\nKIND: descriptions\n\n")

            # Check cue identifiers
            assert "1\n" in content
            assert "2\n" in content
            assert "3\n" in content

            # Check timestamps
            assert "00:00:00.000 --> 00:00:01.000" in content
            assert "00:00:01.000 --> 00:00:02.000" in content
            assert "00:00:02.000 --> 00:00:03.000" in content

            # Check descriptions
            assert "First frame description" in content
            assert "Second frame description" in content
            assert "Third frame description" in content

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_analyze_frames_to_webvtt(self, temp_frames_dir, temp_output_dir):
        """Test complete workflow from frames to WebVTT."""
        from msprites2.visual_analysis import VisualAnalyzer

        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "Test description."}}

        with patch("ollama.Client", return_value=mock_client):
            analyzer = VisualAnalyzer()

            output_path = os.path.join(temp_output_dir, "descriptions.vtt")
            descriptions = analyzer.analyze_frames_to_webvtt(
                temp_frames_dir, output_path
            )

            assert len(descriptions) == 5
            assert os.path.exists(output_path)

            with open(output_path, encoding="utf-8") as f:
                content = f.read()

            assert content.startswith("WEBVTT\nKIND: descriptions\n\n")

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_batch_analyze(self, temp_frames_dir):
        """Test batch analysis functionality."""
        from msprites2.visual_analysis import VisualAnalyzer

        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "Batch test."}}

        frame_paths = [
            str(Path(temp_frames_dir) / f"frame_{i:04d}.jpg") for i in range(1, 4)
        ]

        with patch("ollama.Client", return_value=mock_client):
            analyzer = VisualAnalyzer()

            descriptions = analyzer.batch_analyze(frame_paths, batch_size=2)

            assert len(descriptions) == 3
            assert all(d.description == "Batch test." for d in descriptions)


class TestConvenienceFunction:
    """Tests for convenience function."""

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_analyze_video_frames_function(self, temp_frames_dir, temp_output_dir):
        """Test the convenience analyze_video_frames function."""
        from msprites2.visual_analysis import analyze_video_frames

        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "Convenience test."}}

        with patch("ollama.Client", return_value=mock_client):
            output_path = os.path.join(temp_output_dir, "descriptions.vtt")

            descriptions = analyze_video_frames(temp_frames_dir, output_path)

            assert len(descriptions) == 5
            assert os.path.exists(output_path)

            with open(output_path, encoding="utf-8") as f:
                content = f.read()

            assert content.startswith("WEBVTT\nKIND: descriptions\n\n")


class TestIntegration:
    """Integration tests for visual analysis."""

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_custom_prompt(self, temp_frames_dir):
        """Test using custom prompts."""
        from msprites2.visual_analysis import VisualAnalyzer

        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "Custom response."}
        }

        custom_prompt = "Describe this image in 5 words."

        with patch("ollama.Client", return_value=mock_client):
            analyzer = VisualAnalyzer(prompt=custom_prompt)

            frame_path = Path(temp_frames_dir) / "frame_0001.jpg"
            desc = analyzer.analyze_frame(str(frame_path), 1)

            # Verify custom prompt was used
            call_args = mock_client.chat.call_args[1]
            assert call_args["messages"][0]["content"] == custom_prompt

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="ollama not installed")
    def test_error_handling(self, temp_frames_dir):
        """Test error handling when Ollama fails."""
        from msprites2.visual_analysis import VisualAnalyzer

        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("Ollama connection failed")

        with patch("ollama.Client", return_value=mock_client):
            analyzer = VisualAnalyzer()

            frame_path = Path(temp_frames_dir) / "frame_0001.jpg"

            with pytest.raises(RuntimeError) as exc_info:
                analyzer.analyze_frame(str(frame_path), 1)

            assert "Failed to analyze frame" in str(exc_info.value)
            assert "Ollama connection failed" in str(exc_info.value)