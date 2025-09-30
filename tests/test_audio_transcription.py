"""Tests for audio transcription module."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Check if faster-whisper is available
try:
    import faster_whisper

    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


# Test fixtures
@pytest.fixture
def sample_video_path():
    """Return path to sample video (assumes it exists from previous tests)."""
    video_path = Path(__file__).parent / "fixtures" / "SampleVideo_360x240_1mb.mp4"
    if not video_path.exists():
        pytest.skip("Sample video not available")
    return str(video_path)


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestTranscriptionSegment:
    """Tests for TranscriptionSegment class."""

    def test_import_without_faster_whisper(self):
        """Test that TranscriptionSegment can be imported independently."""
        # Import directly from the module (doesn't require faster-whisper)
        from msprites2.audio_transcription import TranscriptionSegment

        segment = TranscriptionSegment(start=0.0, end=5.0, text="Hello world")
        assert segment.start == 0.0
        assert segment.end == 5.0
        assert segment.text == "Hello world"

    def test_timestamp_formatting(self):
        """Test WebVTT timestamp formatting."""
        from msprites2.audio_transcription import TranscriptionSegment

        segment = TranscriptionSegment(start=0.0, end=1.0, text="test")

        # Test various timestamp formats
        assert segment.to_webvtt_timestamp(0.0) == "00:00:00.000"
        assert segment.to_webvtt_timestamp(1.5) == "00:00:01.500"
        assert segment.to_webvtt_timestamp(61.25) == "00:01:01.250"
        assert segment.to_webvtt_timestamp(3661.123) == "01:01:01.123"

    def test_webvtt_cue_format(self):
        """Test WebVTT cue block formatting."""
        from msprites2.audio_transcription import TranscriptionSegment

        segment = TranscriptionSegment(
            start=1.5, end=5.25, text="This is a test caption."
        )
        cue = segment.to_webvtt_cue()

        assert "00:00:01.500 --> 00:00:05.250" in cue
        assert "This is a test caption." in cue
        assert cue.endswith("\n")


class TestAudioTranscriberInit:
    """Tests for AudioTranscriber initialization."""

    def test_import_error_without_faster_whisper(self):
        """Test that AudioTranscriber raises ImportError without faster-whisper."""
        # Mock the import to simulate missing package
        with patch.dict(sys.modules, {"faster_whisper": None}):
            # Clear any cached imports
            if "msprites2.audio_transcription" in sys.modules:
                del sys.modules["msprites2.audio_transcription"]

            from msprites2.audio_transcription import AudioTranscriber

            with pytest.raises(ImportError) as exc_info:
                AudioTranscriber()

            assert "faster-whisper is required" in str(exc_info.value)
            assert "pip install msprites2[transcription]" in str(exc_info.value)

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    def test_initialization_with_defaults(self):
        """Test default initialization parameters."""
        from msprites2.audio_transcription import AudioTranscriber

        transcriber = AudioTranscriber()

        assert transcriber.model_size == "base"
        assert transcriber.device == "auto"
        assert transcriber.compute_type == "int8"
        assert transcriber.language is None
        assert transcriber.model is not None

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        from msprites2.audio_transcription import AudioTranscriber

        transcriber = AudioTranscriber(
            model_size="tiny",
            device="cpu",
            compute_type="int8",
            language="en",
        )

        assert transcriber.model_size == "tiny"
        assert transcriber.device == "cpu"
        assert transcriber.compute_type == "int8"
        assert transcriber.language == "en"


class TestAudioTranscriberMethods:
    """Tests for AudioTranscriber methods."""

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    def test_transcribe_nonexistent_file(self):
        """Test transcription with nonexistent video file."""
        from msprites2.audio_transcription import AudioTranscriber

        transcriber = AudioTranscriber(model_size="tiny")

        with pytest.raises(FileNotFoundError) as exc_info:
            transcriber.transcribe("/nonexistent/video.mp4")

        assert "Video file not found" in str(exc_info.value)

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    @pytest.mark.slow
    def test_transcribe_real_video(self, sample_video_path):
        """Test transcription with a real video file."""
        from msprites2.audio_transcription import AudioTranscriber

        transcriber = AudioTranscriber(model_size="tiny")
        segments = transcriber.transcribe(sample_video_path)

        assert isinstance(segments, list)
        # Video might not have audio, so segments could be empty
        for segment in segments:
            assert hasattr(segment, "start")
            assert hasattr(segment, "end")
            assert hasattr(segment, "text")
            assert segment.start >= 0
            assert segment.end > segment.start

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    def test_save_webvtt(self, temp_output_dir):
        """Test saving WebVTT file."""
        from msprites2.audio_transcription import (
            AudioTranscriber,
            TranscriptionSegment,
        )

        transcriber = AudioTranscriber()
        segments = [
            TranscriptionSegment(0.0, 2.5, "First caption"),
            TranscriptionSegment(2.5, 5.0, "Second caption"),
            TranscriptionSegment(5.0, 8.0, "Third caption"),
        ]

        output_path = os.path.join(temp_output_dir, "test.vtt")
        transcriber.save_webvtt(segments, output_path)

        assert os.path.exists(output_path)

        with open(output_path, encoding="utf-8") as f:
            content = f.read()

        # Check WebVTT header
        assert content.startswith("WEBVTT\n\n")

        # Check cue identifiers
        assert "1\n" in content
        assert "2\n" in content
        assert "3\n" in content

        # Check timestamps
        assert "00:00:00.000 --> 00:00:02.500" in content
        assert "00:00:02.500 --> 00:00:05.000" in content
        assert "00:00:05.000 --> 00:00:08.000" in content

        # Check captions
        assert "First caption" in content
        assert "Second caption" in content
        assert "Third caption" in content

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    @pytest.mark.slow
    def test_transcribe_to_webvtt(self, sample_video_path, temp_output_dir):
        """Test complete transcription to WebVTT workflow."""
        from msprites2.audio_transcription import AudioTranscriber

        transcriber = AudioTranscriber(model_size="tiny")
        output_path = os.path.join(temp_output_dir, "captions.vtt")

        segments = transcriber.transcribe_to_webvtt(sample_video_path, output_path)

        assert isinstance(segments, list)
        assert os.path.exists(output_path)

        with open(output_path, encoding="utf-8") as f:
            content = f.read()

        assert content.startswith("WEBVTT\n\n")

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    def test_progress_callback(self, sample_video_path):
        """Test progress callback functionality."""
        from msprites2.audio_transcription import AudioTranscriber

        transcriber = AudioTranscriber(model_size="tiny")
        progress_values = []

        def callback(progress):
            progress_values.append(progress)

        segments = transcriber.transcribe(sample_video_path, progress_callback=callback)

        # If there are segments, we should have progress updates
        if segments:
            assert len(progress_values) == len(segments)
            # Progress should be monotonically increasing
            for i in range(1, len(progress_values)):
                assert progress_values[i] >= progress_values[i - 1]


class TestConvenienceFunction:
    """Tests for convenience function."""

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    @pytest.mark.slow
    def test_transcribe_video_function(self, sample_video_path, temp_output_dir):
        """Test the convenience transcribe_video function."""
        from msprites2.audio_transcription import transcribe_video

        output_path = os.path.join(temp_output_dir, "captions.vtt")

        segments = transcribe_video(
            sample_video_path,
            output_path,
            model_size="tiny",
            device="cpu",
        )

        assert isinstance(segments, list)
        assert os.path.exists(output_path)

        with open(output_path, encoding="utf-8") as f:
            content = f.read()

        assert content.startswith("WEBVTT\n\n")


class TestIntegration:
    """Integration tests for audio transcription."""

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    @pytest.mark.slow
    @pytest.mark.integration
    def test_full_workflow(self, sample_video_path, temp_output_dir):
        """Test complete transcription workflow from video to WebVTT."""
        from msprites2.audio_transcription import AudioTranscriber

        transcriber = AudioTranscriber(model_size="tiny", device="cpu")

        # Transcribe
        segments = transcriber.transcribe(
            sample_video_path, vad_filter=True, beam_size=3
        )

        # Save to WebVTT
        output_path = os.path.join(temp_output_dir, "full_test.vtt")
        transcriber.save_webvtt(segments, output_path)

        # Verify file exists and is valid
        assert os.path.exists(output_path)

        with open(output_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Basic validation
        assert lines[0].strip() == "WEBVTT"

        # Check structure
        if len(segments) > 0:
            # Should have cue identifiers, timestamps, and text
            content = "".join(lines)
            assert "-->" in content  # Timestamp separator

    @pytest.mark.skipif(
        not FASTER_WHISPER_AVAILABLE, reason="faster-whisper not installed"
    )
    def test_language_override(self, sample_video_path):
        """Test language parameter override."""
        from msprites2.audio_transcription import AudioTranscriber

        # Initialize with default language
        transcriber = AudioTranscriber(model_size="tiny", language="en")

        # Override with different language
        # Note: This won't actually test transcription quality,
        # just that the parameter is accepted
        with patch.object(transcriber.model, "transcribe") as mock_transcribe:
            mock_transcribe.return_value = ([], Mock(language="es"))

            transcriber.transcribe(sample_video_path, language="es")

            # Verify language was passed to the model
            assert mock_transcribe.called
            call_kwargs = mock_transcribe.call_args[1]
            assert call_kwargs.get("language") == "es"