# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
msprites2 is a Python package that creates video thumbnail spritesheet images and WebVTT files from video files. It extracts frames from videos using FFmpeg, assembles them into grid-based sprite sheets using ImageMagick, and generates WebVTT subtitle files with spatial metadata for video players.

## Key Dependencies
- **FFmpeg**: Required for video frame extraction
- **ImageMagick**: Required for sprite sheet generation (uses `magick` command in v7.0+, falls back to `montage`)
- Python 3.6+ (standard library only, no external Python dependencies)

## Development Commands

### Installation and Setup
```bash
# Install for development
pip install -e .

# Install package from PyPI
pip install msprites2

# Check system dependencies
which ffmpeg  # Should be available
which magick  # Should be available (or 'montage' for older ImageMagick)
```

### Testing
```bash
# Run tests (pytest is available in environment)
python -m pytest

# Manual testing can be done by creating test.py (gitignored)
python test.py
```

### Package Building and Distribution
```bash
# Build package
python setup.py sdist bdist_wheel

# Clean build artifacts
rm -rf build/ dist/ *.egg-info/
```

## Code Architecture

### Main Components
- **MontageSprites** (`msprites2/montage_sprites.py:23`): Core class handling the entire workflow
- **Settings** (`msprites2/settings.py:1`): Configuration class for customizing output parameters

### Key Processes
1. **Frame Extraction**: Uses FFmpeg to extract frames at specified intervals (IPS - Images Per Second)
2. **Sprite Generation**: Uses ImageMagick montage to combine frames into grid layouts
3. **WebVTT Creation**: Generates subtitle files with spatial coordinates for video player integration

### Default Configuration
- Frame size: 512x288 pixels
- Grid layout: 30x30 frames per sprite sheet
- Extraction rate: 1 frame per second (IPS=1)
- Output format: JPEG

### Usage Pattern
The main entry point is the classmethod `MontageSprites.from_media()` which handles the complete workflow:
- Video path validation
- Thumbnail directory setup
- Frame extraction, sprite creation, and WebVTT generation

## Development Notes

### External Command Execution
The package uses `subprocess.run(shlex.split(cmd))` for executing FFmpeg and ImageMagick commands. Commands are constructed using string formatting and properly shell-escaped.

### File Management
- Thumbnail directories must exist and be empty before processing
- Generated files: individual frame images, sprite sheet image, WebVTT subtitle file
- Uses `os.scandir()` for efficient file counting

### Error Handling
Limited error handling - mainly validates thumbnail directory state. External command failures may not be gracefully handled.