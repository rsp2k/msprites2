# msprites2

> Modern Python library for creating video thumbnail sprites and WebVTT files with parallel processing and ML pipeline integration

[![PyPI Version](https://img.shields.io/pypi/v/msprites2.svg)](https://pypi.org/project/msprites2/)
[![Python Support](https://img.shields.io/pypi/pyversions/msprites2.svg)](https://pypi.org/project/msprites2/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Quality](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests](https://img.shields.io/badge/tests-pytest-blue.svg)](https://pytest.org/)

**msprites2** transforms video files into thumbnail sprite sheets and WebVTT metadata files, enabling smooth video scrubbing experiences in web players. With modern Python packaging, parallel processing capabilities, and streaming integration for ML pipelines.

## ✨ Key Features

- **🚀 High Performance**: Optional parallel frame extraction with intelligent chunk processing
- **🎯 Video Player Ready**: Generate sprite sheets and WebVTT files for seamless video scrubbing
- **🧠 ML Pipeline Integration**: Streaming frame extraction for neural networks and AI processing
- **⚡ Modern Python**: Python 3.9-3.13 support with modern tooling (uv, ruff, pytest)
- **🔧 Flexible Configuration**: Customizable dimensions, frame rates, and grid layouts
- **📊 Performance Analytics**: Built-in benchmarking tools for optimization
- **🎬 Production Ready**: Comprehensive test suite and robust error handling

## 🎯 Perfect For

- **Video Streaming Platforms**: Netflix-style video scrubbing thumbnails
- **ML/AI Researchers**: Frame-by-frame video analysis and processing
- **Content Management**: Automated video preview generation
- **Web Developers**: Enhanced video player experiences

## 📦 Installation

### Quick Install
```bash
pip install msprites2
```

### With Parallel Processing (Recommended)
```bash
pip install msprites2 ffmpeg-python
```

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt install ffmpeg imagemagick

# macOS
brew install ffmpeg imagemagick

# Arch Linux
sudo pacman -S ffmpeg imagemagick
```

## 🚀 Quick Start

### Basic Usage
```python
from msprites2 import MontageSprites
import os

# Create sprite sheet from video
sprite = MontageSprites.from_media(
    video_path="video.mp4",
    thumbnail_dir="thumbnails/",  # Directory for extracted frames
    sprite_file="sprite.jpg",     # Output sprite sheet
    webvtt_file="sprite.webvtt"   # WebVTT metadata file
)

# View generated files
print(f"Sprite sheet: {sprite.sprite_file}")
for filename in os.listdir(sprite.thumbnail_dir):
    print(f"Frame: {filename}")
```

### High-Performance Parallel Processing
```python
# Enable parallel processing for faster extraction
sprite = MontageSprites.from_media(
    video_path="long_video.mp4",
    thumbnail_dir="thumbnails/",
    sprite_file="sprite.jpg",
    webvtt_file="sprite.webvtt",
    parallel=True,  # Enable parallel processing
    progress_callback=lambda completed, total: print(f"Progress: {completed}/{total}")
)
```

## 🧠 ML/AI Integration

Perfect for neural networks, style transfer, and computer vision pipelines:

```python
def apply_style_transfer(frame_path, frame_num):
    """Apply neural style transfer to each frame"""
    # Load your trained model
    styled_frame = model.process(frame_path)
    output_path = f"styled_frames/frame_{frame_num:04d}.jpg"
    styled_frame.save(output_path)
    return output_path

def detect_objects(frame_path, frame_num):
    """Run object detection on each frame"""
    detections = detector.detect(frame_path)
    return {"frame": frame_num, "objects": detections}

# Stream processing for real-time ML pipelines
sprite = MontageSprites("video.mp4", "frames/")

# Style transfer example
for frame_path, frame_num in sprite.extract_streaming(apply_style_transfer):
    print(f"Styled frame {frame_num}: {frame_path}")

# Object detection example  
for frame_path, frame_num in sprite.extract_streaming(detect_objects):
    print(f"Processed frame {frame_num}")
```

## 📊 Advanced Configuration

```python
from msprites2 import MontageSprites

# Custom sprite configuration
class CustomSprites(MontageSprites):
    IPS = 2          # Extract every 2 seconds
    WIDTH = 256      # Thumbnail width
    HEIGHT = 144     # Thumbnail height  
    ROWS = 20        # Sprite grid rows
    COLS = 20        # Sprite grid columns

# High-resolution thumbnails for 4K videos
sprite = CustomSprites("4k_video.mp4", "hd_thumbnails/")
sprite.generate_thumbs(parallel=True)
sprite.generate_sprite("hd_sprite.jpg")
sprite.generate_webvtt("hd_sprite.webvtt")
```

## 📋 Output Examples

### Generated Sprite Sheet
The library creates a grid-based sprite sheet containing all video thumbnails:
```
[Thumbnail 1][Thumbnail 2][Thumbnail 3]...
[Thumbnail N][Thumbnail N+1][Thumbnail N+2]...
...
```

### WebVTT Metadata File
Compatible with HTML5 video players and streaming platforms:
```webvtt
WEBVTT

00:00:00.000 --> 00:00:01.000
sprite.jpg#xywh=0,0,256,144

00:00:01.000 --> 00:00:02.000
sprite.jpg#xywh=256,0,256,144

00:00:02.000 --> 00:00:03.000
sprite.jpg#xywh=512,0,256,144
```

## ⚡ Performance Characteristics

Based on comprehensive benchmarking:

| Scenario | Recommendation | Reason |
|----------|---------------|---------|
| Videos < 5 minutes | Sequential processing | Minimal overhead, optimal for short content |
| Videos > 5 minutes | Parallel processing | Better throughput for long content |
| ML/AI pipelines | Streaming extraction | Memory efficient, real-time processing |
| Network storage | Parallel processing | Overlaps I/O latency with processing |

### Benchmark Your Usage
```bash
# Run performance benchmarks
python benchmark_performance.py your_video.mp4

# Generate test videos and benchmark
python benchmark_performance.py --duration 120
```

## 🛠 Development Setup

### Modern Python Workflow (Recommended)
```bash
# Install uv (fast Python package installer)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/rsp2k/msprites2.git
cd msprites2

# Create virtual environment and install dependencies
uv sync --extra dev

# Run linting and formatting
uv run ruff check .
uv run ruff format .

# Run tests
uv run pytest                    # Unit tests
uv run pytest -m slow          # Integration tests  
uv run pytest --cov=msprites2  # Coverage report
```

### Traditional Setup
```bash
git clone https://github.com/rsp2k/msprites2.git
cd msprites2
pip install -e ".[dev]"
pytest
```

## 🧪 Testing

Comprehensive test suite covering:

```bash
# Unit tests (fast)
pytest tests/ -m "not slow"

# Integration tests (downloads test videos)
pytest tests/ -m slow  

# Performance benchmarks
python benchmark_performance.py

# Realistic workflow testing
python benchmark_realistic.py
```

## 📚 Use Cases & Examples

### Video Streaming Platform
```python
# Netflix-style thumbnail previews
def generate_preview_sprites(video_path, output_dir):
    sprite = MontageSprites.from_media(
        video_path=video_path,
        thumbnail_dir=f"{output_dir}/frames",
        sprite_file=f"{output_dir}/preview.jpg",
        webvtt_file=f"{output_dir}/preview.webvtt",
        parallel=True
    )
    return sprite.sprite_file, sprite.webvtt_file
```

### Content Management System
```python
# Automated video processing pipeline
def process_uploaded_video(video_file):
    base_name = os.path.splitext(video_file)[0]
    
    # Generate multiple resolutions
    resolutions = [
        (320, 180),   # Mobile
        (512, 288),   # Desktop  
        (1024, 576),  # HD
    ]
    
    results = []
    for width, height in resolutions:
        class CustomSprite(MontageSprites):
            WIDTH = width
            HEIGHT = height
            
        sprite = CustomSprite.from_media(
            video_path=video_file,
            thumbnail_dir=f"{base_name}_{width}x{height}_frames",
            sprite_file=f"{base_name}_{width}x{height}.jpg", 
            webvtt_file=f"{base_name}_{width}x{height}.webvtt",
            parallel=True
        )
        results.append((width, height, sprite.sprite_file))
    
    return results
```

### Research & Analytics
```python
# Video analysis pipeline
def analyze_video_content(video_path):
    results = {
        "scene_changes": [],
        "object_counts": [],
        "color_analysis": []
    }
    
    def analyze_frame(frame_path, frame_num):
        # Scene change detection
        if is_scene_change(frame_path):
            results["scene_changes"].append(frame_num)
        
        # Object detection
        objects = count_objects(frame_path) 
        results["object_counts"].append(objects)
        
        # Color analysis
        colors = analyze_colors(frame_path)
        results["color_analysis"].append(colors)
        
        return frame_path
    
    sprite = MontageSprites(video_path, "analysis_frames/")
    for frame_path, frame_num in sprite.extract_streaming(analyze_frame):
        print(f"Analyzed frame {frame_num}")
    
    return results
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository** on GitHub
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Set up development environment**: `uv sync --extra dev` 
4. **Make your changes** with tests
5. **Run the test suite**: `uv run pytest`
6. **Format code**: `uv run ruff format .`
7. **Submit a pull request**

### Development Guidelines

- **Code Quality**: Use ruff for linting and formatting
- **Testing**: Add tests for new features (pytest)
- **Documentation**: Update docstrings and examples
- **Performance**: Run benchmarks for performance-related changes
- **Compatibility**: Support Python 3.9-3.13

### Areas for Contribution

- 🚀 **Performance Optimization**: GPU acceleration, smarter chunking
- 🧠 **ML Integration**: TensorFlow/PyTorch utilities, model examples  
- 🎨 **Output Formats**: Additional sprite layouts, WebP support
- 📱 **Platform Support**: Windows optimizations, ARM support
- 📚 **Documentation**: Tutorials, advanced examples, API docs

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Original Concept**: Built upon [msprites](https://github.com/baloda/msprites) by [@baloda](https://github.com/baloda) - thank you!
- **FFmpeg Integration**: Powered by [ffmpeg-python](https://github.com/kkroening/ffmpeg-python)
- **WebVTT Standard**: Following [W3C WebVTT specification](https://www.w3.org/TR/webvtt1/)

## 🔗 Links

- **PyPI Package**: https://pypi.org/project/msprites2/
- **Source Code**: https://github.com/rsp2k/msprites2
- **Issues**: https://github.com/rsp2k/msprites2/issues
- **Changelog**: https://github.com/rsp2k/msprites2/releases

---

⚡ **Performance Tips**: For videos > 5 minutes, use `parallel=True`. For ML pipelines, use `extract_streaming()` for memory efficiency.

🎯 **Production Ready**: Used in production environments with comprehensive testing and performance optimization.