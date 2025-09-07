#!/usr/bin/env python3
"""
Realistic performance benchmark with higher resolution and complex video content.

This creates more demanding test scenarios that better demonstrate the benefits
of parallel processing for typical video sprite generation workflows.
"""

import os
import shutil
import tempfile
import time

try:
    import ffmpeg

    from msprites2 import MontageSprites
    from msprites2.parallel_extractor import extract_frames_parallel

    DEPS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Dependencies not available: {e}")
    DEPS_AVAILABLE = False


def create_complex_test_video(
    output_path: str, duration: int = 60, resolution: str = "1920x1080"
) -> str:
    """Create a complex test video that's more demanding to process."""
    print(f"Creating complex {duration}s test video at {resolution}: {output_path}")

    # Create a more complex test pattern with movement and detail
    (
        ffmpeg.input(f"mandelbrot=size={resolution}:rate=30", f="lavfi", t=duration)
        .output(
            output_path,
            vcodec="libx264",
            pix_fmt="yuv420p",
            **{"b:v": "5M"},  # Higher bitrate for more complex encoding
        )
        .overwrite_output()
        .run(quiet=True)
    )

    print(f"✅ Complex test video created: {output_path}")
    return output_path


def benchmark_extraction_methods(video_path: str, output_base: str) -> dict:
    """Compare sequential vs parallel extraction with detailed timing."""
    results = {}

    # Test parameters that are more demanding
    test_configs = [
        {"name": "Low Res", "width": 256, "height": 144, "ips": 1},
        {"name": "Standard", "width": 512, "height": 288, "ips": 1},
        {"name": "High Res", "width": 1024, "height": 576, "ips": 1},
        {
            "name": "High Freq",
            "width": 512,
            "height": 288,
            "ips": 0.5,
        },  # Every 0.5 seconds
    ]

    for config in test_configs:
        config_name = config["name"]
        print(f"\n🧪 Testing {config_name} configuration...")
        print(
            f"   Resolution: {config['width']}x{config['height']}, IPS: {config['ips']}"
        )

        config_results = {}

        # Sequential test
        seq_dir = os.path.join(
            output_base, f"seq_{config_name.lower().replace(' ', '_')}"
        )
        os.makedirs(seq_dir, exist_ok=True)

        start_time = time.time()
        sprite = MontageSprites(video_path, seq_dir)
        sprite.WIDTH = config["width"]
        sprite.HEIGHT = config["height"]
        sprite.IPS = config["ips"]
        sprite.generate_thumbs(parallel=False)
        sequential_time = time.time() - start_time
        sequential_frames = sprite.count_files()

        config_results["sequential"] = {
            "time": sequential_time,
            "frames": sequential_frames,
            "fps": sequential_frames / sequential_time if sequential_time > 0 else 0,
        }

        print(f"   📊 Sequential: {sequential_frames} frames in {sequential_time:.2f}s")

        # Parallel test
        par_dir = os.path.join(
            output_base, f"par_{config_name.lower().replace(' ', '_')}"
        )
        os.makedirs(par_dir, exist_ok=True)

        start_time = time.time()
        parallel_frames = extract_frames_parallel(
            video_path=video_path,
            output_dir=par_dir,
            width=config["width"],
            height=config["height"],
            ips=config["ips"],
        )
        parallel_time = time.time() - start_time

        config_results["parallel"] = {
            "time": parallel_time,
            "frames": parallel_frames,
            "fps": parallel_frames / parallel_time if parallel_time > 0 else 0,
        }

        # Calculate improvement
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0
        improvement = (
            ((sequential_time - parallel_time) / sequential_time * 100)
            if sequential_time > 0
            else 0
        )

        config_results["comparison"] = {
            "speedup": speedup,
            "improvement_percent": improvement,
            "time_saved": sequential_time - parallel_time,
        }

        print(f"   ⚡ Parallel: {parallel_frames} frames in {parallel_time:.2f}s")
        print(f"   🚀 Speedup: {speedup:.2f}x ({improvement:+.1f}%)")

        results[config_name] = config_results

        # Cleanup
        shutil.rmtree(seq_dir, ignore_errors=True)
        shutil.rmtree(par_dir, ignore_errors=True)

    return results


def print_comprehensive_results(results: dict):
    """Print detailed benchmark results."""
    print("\n" + "=" * 70)
    print("🏆 COMPREHENSIVE PERFORMANCE BENCHMARK RESULTS")
    print("=" * 70)

    best_speedup = 0
    best_config = None

    for config_name, config_results in results.items():
        sequential = config_results["sequential"]
        parallel = config_results["parallel"]
        comparison = config_results["comparison"]

        print(f"\n📋 {config_name} Configuration:")
        print(
            f"   Sequential: {sequential['time']:.2f}s, {sequential['frames']} frames, {sequential['fps']:.1f} fps"
        )
        print(
            f"   Parallel:   {parallel['time']:.2f}s, {parallel['frames']} frames, {parallel['fps']:.1f} fps"
        )
        print(
            f"   Speedup:    {comparison['speedup']:.2f}x ({comparison['improvement_percent']:+.1f}%)"
        )

        if comparison["speedup"] > best_speedup:
            best_speedup = comparison["speedup"]
            best_config = config_name

    print(f"\n🥇 Best Performance: {best_config} with {best_speedup:.2f}x speedup")

    # Overall recommendations
    print("\n💡 Performance Analysis:")
    if best_speedup >= 2:
        print("   ✅ Parallel processing shows significant benefits (≥2x speedup)")
        print("   📈 Recommend using parallel=True for production workloads")
    elif best_speedup >= 1.5:
        print("   👍 Parallel processing shows moderate benefits (1.5-2x speedup)")
        print("   📊 Consider parallel=True for larger videos or batch processing")
    elif best_speedup >= 1.2:
        print("   🔍 Parallel processing shows minor benefits (1.2-1.5x speedup)")
        print("   ⚖️  Evaluate based on video size and processing frequency")
    else:
        print("   ⚠️  Limited or no benefits from parallel processing")
        print("   🤔 System may be I/O bound or videos too small to benefit")
        print("   📝 Consider sequential processing for optimal resource usage")


def main():
    if not DEPS_AVAILABLE:
        print("❌ Required dependencies not available")
        return 1

    # Create test video
    test_video = "benchmark_complex_test.mp4"

    if not os.path.exists(test_video):
        create_complex_test_video(test_video, duration=90, resolution="1920x1080")
    else:
        print(f"Using existing test video: {test_video}")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            print("🎬 Running comprehensive benchmarks...")

            results = benchmark_extraction_methods(test_video, temp_dir)
            print_comprehensive_results(results)

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        return 1

    finally:
        # Cleanup test video
        if os.path.exists(test_video):
            response = input(f"\n🗑️  Delete test video {test_video}? [y/N]: ")
            if response.lower().startswith("y"):
                os.remove(test_video)
                print(f"Deleted {test_video}")

    return 0


if __name__ == "__main__":
    exit(main())
