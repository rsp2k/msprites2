#!/usr/bin/env python3
"""
Performance benchmark script for msprites2 parallel processing.

This script compares sequential vs parallel frame extraction performance
and provides detailed metrics on the speed improvements achieved.

Usage:
    python benchmark_performance.py [test_video_path] [--duration seconds]

Example:
    python benchmark_performance.py sample.mp4 --duration 30
"""

import argparse
import os
import shutil
import tempfile
import time
from typing import Any

try:
    from msprites2 import MontageSprites
    from msprites2.parallel_extractor import extract_frames_parallel

    MSPRITES_AVAILABLE = True
except ImportError:
    MSPRITES_AVAILABLE = False

try:
    import ffmpeg

    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False


class PerformanceBenchmark:
    """Benchmark parallel vs sequential frame extraction performance."""

    def __init__(self, video_path: str, test_duration: int = 30):
        self.video_path = video_path
        self.test_duration = test_duration
        self.results = {}

        # Standard test parameters matching msprites2 defaults
        self.width = 512
        self.height = 288
        self.ips = 1

    def get_video_info(self) -> dict[str, Any]:
        """Get video metadata for the benchmark."""
        if not FFMPEG_AVAILABLE:
            return {"duration": "Unknown", "size": "Unknown"}

        try:
            probe = ffmpeg.probe(self.video_path)
            duration = float(probe["format"]["duration"])
            size_mb = float(probe["format"]["size"]) / (1024 * 1024)

            return {
                "duration": f"{duration:.2f}s",
                "size": f"{size_mb:.1f}MB",
                "format": probe["format"].get("format_name", "Unknown"),
                "video_codec": probe["streams"][0].get("codec_name", "Unknown"),
            }
        except Exception as e:
            print(f"Warning: Could not probe video: {e}")
            return {"duration": "Unknown", "size": "Unknown"}

    def benchmark_sequential(self, output_dir: str) -> dict[str, Any]:
        """Benchmark sequential frame extraction."""
        print("🔄 Running sequential extraction benchmark...")

        start_time = time.time()

        # Use traditional MontageSprites extraction (parallel=False)
        sprite = MontageSprites(self.video_path, output_dir)
        sprite.generate_thumbs(parallel=False)

        end_time = time.time()

        # Count extracted frames
        frame_count = sprite.count_files()
        duration = end_time - start_time

        result = {
            "method": "Sequential",
            "duration": duration,
            "frames": frame_count,
            "fps": frame_count / duration if duration > 0 else 0,
            "frames_per_second_extraction": frame_count / duration
            if duration > 0
            else 0,
        }

        print(
            f"   ✅ Sequential: {frame_count} frames in {duration:.2f}s ({result['fps']:.1f} frames/s)"
        )
        return result

    def benchmark_parallel(
        self, output_dir: str, workers: int = None
    ) -> dict[str, Any]:
        """Benchmark parallel frame extraction."""
        worker_desc = f" ({workers} workers)" if workers else ""
        print(f"⚡ Running parallel extraction benchmark{worker_desc}...")

        start_time = time.time()

        # Use parallel extraction
        frame_count = extract_frames_parallel(
            video_path=self.video_path,
            output_dir=output_dir,
            width=self.width,
            height=self.height,
            ips=self.ips,
            max_workers=workers,
        )

        end_time = time.time()

        duration = end_time - start_time

        result = {
            "method": f"Parallel{worker_desc}",
            "duration": duration,
            "frames": frame_count,
            "fps": frame_count / duration if duration > 0 else 0,
            "frames_per_second_extraction": frame_count / duration
            if duration > 0
            else 0,
            "workers": workers,
        }

        print(
            f"   ✅ Parallel{worker_desc}: {frame_count} frames in {duration:.2f}s ({result['fps']:.1f} frames/s)"
        )
        return result

    def benchmark_different_worker_counts(self, base_output_dir: str) -> list:
        """Test different worker counts to find optimal performance."""
        import os

        cpu_count = os.cpu_count() or 1
        worker_counts = [1, 2, 4, min(8, cpu_count), cpu_count, cpu_count + 4]
        worker_counts = sorted(set(worker_counts))  # Remove duplicates and sort

        results = []

        for workers in worker_counts:
            output_dir = os.path.join(base_output_dir, f"parallel_{workers}_workers")
            os.makedirs(output_dir, exist_ok=True)

            try:
                result = self.benchmark_parallel(output_dir, workers)
                results.append(result)

                # Clean up frames after each test
                shutil.rmtree(output_dir)

            except Exception as e:
                print(f"   ❌ Failed with {workers} workers: {e}")

        return results

    def run_comprehensive_benchmark(self) -> dict[str, Any]:
        """Run comprehensive performance benchmarks."""
        if not MSPRITES_AVAILABLE:
            print("❌ msprites2 not available for benchmarking")
            return {}

        if not FFMPEG_AVAILABLE:
            print("❌ ffmpeg-python not available for parallel benchmarking")
            return {}

        print("🎬 Benchmarking msprites2 performance")
        print(f"📹 Video: {self.video_path}")

        # Show video info
        video_info = self.get_video_info()
        for key, value in video_info.items():
            print(f"   {key}: {value}")
        print()

        with tempfile.TemporaryDirectory() as temp_base_dir:
            results = {
                "video_info": video_info,
                "test_parameters": {
                    "width": self.width,
                    "height": self.height,
                    "ips": self.ips,
                    "video_path": self.video_path,
                },
                "benchmarks": [],
            }

            # Sequential benchmark
            sequential_dir = os.path.join(temp_base_dir, "sequential")
            os.makedirs(sequential_dir, exist_ok=True)

            sequential_result = self.benchmark_sequential(sequential_dir)
            results["benchmarks"].append(sequential_result)

            # Clean up sequential frames
            shutil.rmtree(sequential_dir)

            # Parallel benchmarks with different worker counts
            parallel_dir = os.path.join(temp_base_dir, "parallel_tests")
            os.makedirs(parallel_dir, exist_ok=True)

            parallel_results = self.benchmark_different_worker_counts(parallel_dir)
            results["benchmarks"].extend(parallel_results)

            # Find best parallel result
            if parallel_results:
                best_parallel = min(parallel_results, key=lambda x: x["duration"])

                # Calculate improvements
                sequential_time = sequential_result["duration"]
                best_parallel_time = best_parallel["duration"]

                speedup = (
                    sequential_time / best_parallel_time
                    if best_parallel_time > 0
                    else 0
                )
                time_saved = sequential_time - best_parallel_time
                percent_improvement = (
                    ((sequential_time - best_parallel_time) / sequential_time * 100)
                    if sequential_time > 0
                    else 0
                )

                results["summary"] = {
                    "sequential_time": sequential_time,
                    "best_parallel_time": best_parallel_time,
                    "best_parallel_workers": best_parallel.get("workers"),
                    "speedup": speedup,
                    "time_saved": time_saved,
                    "percent_improvement": percent_improvement,
                }

        return results

    def print_benchmark_summary(self, results: dict[str, Any]):
        """Print a formatted summary of benchmark results."""
        print("\n" + "=" * 60)
        print("🏆 PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)

        if "summary" in results:
            summary = results["summary"]
            print(f"📊 Sequential Time: {summary['sequential_time']:.2f}s")
            print(
                f"⚡ Best Parallel Time: {summary['best_parallel_time']:.2f}s ({summary['best_parallel_workers']} workers)"
            )
            print(f"🚀 Speedup: {summary['speedup']:.1f}x faster")
            print(f"⏱️  Time Saved: {summary['time_saved']:.2f}s")
            print(f"📈 Performance Improvement: {summary['percent_improvement']:.1f}%")
            print()

            # Performance interpretation
            if summary["speedup"] >= 3:
                print("🎉 EXCELLENT: >3x speedup achieved!")
            elif summary["speedup"] >= 2:
                print("✅ GREAT: 2-3x speedup achieved!")
            elif summary["speedup"] >= 1.5:
                print("👍 GOOD: 1.5-2x speedup achieved!")
            elif summary["speedup"] >= 1.2:
                print("🔍 MODERATE: Some improvement achieved")
            else:
                print("⚠️  LIMITED: Minimal performance gain")

        print("\n📋 Detailed Results:")
        for benchmark in results.get("benchmarks", []):
            method = benchmark["method"]
            duration = benchmark["duration"]
            frames = benchmark["frames"]
            fps = benchmark["fps"]
            print(f"   {method}: {duration:.2f}s, {frames} frames, {fps:.1f} frames/s")

        print("\n💡 Recommendations:")
        if "summary" in results:
            if summary["speedup"] >= 2:
                print(
                    "   • Parallel processing provides significant benefits for this video"
                )
                print(f"   • Optimal worker count: {summary['best_parallel_workers']}")
                print("   • Recommend using parallel=True for production")
            else:
                print("   • Limited benefit from parallel processing")
                print("   • Video may be too short or system may be I/O bound")
                print("   • Consider using sequential processing for small videos")


def create_test_video(duration_seconds: int = 30) -> str:
    """Create a test video for benchmarking if needed."""
    if not FFMPEG_AVAILABLE:
        raise ImportError("ffmpeg-python required to create test video")

    output_path = f"test_video_{duration_seconds}s.mp4"

    if os.path.exists(output_path):
        print(f"Using existing test video: {output_path}")
        return output_path

    print(f"Creating {duration_seconds}s test video: {output_path}")

    # Create a test pattern video using ffmpeg
    (
        ffmpeg.input(
            f"testsrc=duration={duration_seconds}:size=1280x720:rate=30", f="lavfi"
        )
        .output(output_path, vcodec="libx264", pix_fmt="yuv420p")
        .overwrite_output()
        .run(quiet=True)
    )

    print(f"✅ Test video created: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark msprites2 parallel processing performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python benchmark_performance.py                    # Use generated 30s test video
    python benchmark_performance.py sample.mp4         # Use existing video
    python benchmark_performance.py --duration 60      # Generate 60s test video
        """,
    )

    parser.add_argument(
        "video_path",
        nargs="?",
        help="Path to video file (will create test video if not provided)",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in seconds for generated test video (default: 30)",
    )

    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep generated test video after benchmarking",
    )

    args = parser.parse_args()

    # Check dependencies
    if not MSPRITES_AVAILABLE:
        print("❌ Error: msprites2 package not available")
        print("   Install with: pip install -e .")
        return 1

    if not FFMPEG_AVAILABLE:
        print("❌ Error: ffmpeg-python not available")
        print("   Install with: pip install ffmpeg-python")
        return 1

    # Get or create test video
    if args.video_path:
        if not os.path.exists(args.video_path):
            print(f"❌ Error: Video file not found: {args.video_path}")
            return 1
        video_path = args.video_path
        cleanup_video = False
    else:
        video_path = create_test_video(args.duration)
        cleanup_video = not args.no_cleanup

    try:
        # Run benchmark
        benchmark = PerformanceBenchmark(video_path, args.duration)
        results = benchmark.run_comprehensive_benchmark()

        if results:
            benchmark.print_benchmark_summary(results)
        else:
            print("❌ Benchmark failed - check dependencies and video file")
            return 1

    finally:
        # Cleanup generated test video if needed
        if cleanup_video and os.path.exists(video_path):
            os.remove(video_path)
            print(f"🗑️  Cleaned up test video: {video_path}")

    return 0


if __name__ == "__main__":
    exit(main())
