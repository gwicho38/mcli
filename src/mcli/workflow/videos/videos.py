import os
import sys
from pathlib import Path

import click

# Add the app/video directory to the path so we can import the video processor
app_video_path = Path(__file__).parent.parent.parent / "app" / "video"
sys.path.insert(0, str(app_video_path))

# Lazy import variables
_video_module = None
_import_error = None


def _get_video_module():
    """Lazy import of video processing module."""
    global _video_module, _import_error

    if _video_module is not None:
        return _video_module

    if _import_error is not None:
        raise _import_error

    try:
        from mcli.app.video.video import (
            CONFIG,
            EnhancedVideoProcessor,
            IntelligentVideoProcessor,
            VideoProcessor,
        )

        _video_module = {
            "VideoProcessor": VideoProcessor,
            "EnhancedVideoProcessor": EnhancedVideoProcessor,
            "IntelligentVideoProcessor": IntelligentVideoProcessor,
            "CONFIG": CONFIG,
        }
    except ImportError:
        try:
            # Fallback import
            import importlib.util

            spec = importlib.util.spec_from_file_location("video", app_video_path / "video.py")
            video_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(video_module)

            _video_module = {
                "VideoProcessor": video_module.VideoProcessor,
                "EnhancedVideoProcessor": video_module.EnhancedVideoProcessor,
                "IntelligentVideoProcessor": video_module.IntelligentVideoProcessor,
                "CONFIG": video_module.CONFIG,
            }
        except Exception as e:
            _import_error = ImportError(f"Could not import video processing modules: {e}")
            # Return basic fallback
            _video_module = {
                "VideoProcessor": None,
                "EnhancedVideoProcessor": None,
                "IntelligentVideoProcessor": None,
                "CONFIG": {"temp_dir": "./temp", "output_dir": "./output"},
            }

    return _video_module


@click.group()
def videos():
    """Video processing and overlay removal tools."""
    pass


@videos.command()
@click.argument("input_video", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output video path")
@click.option("--fps", "-f", default=30, help="Frame extraction rate (default: 30)")
@click.option("--context", "-c", default=3, help="Temporal context window size (default: 3)")
@click.option(
    "--method",
    type=click.Choice(["intelligent", "basic"]),
    default="intelligent",
    help="Processing method (default: intelligent)",
)
@click.option("--dry-run", is_flag=True, help="Only extract frames and analyze video")
def remove_overlay(input_video, output, fps, context, method, dry_run):
    """Remove overlays from videos with intelligent content reconstruction."""

    try:
        video_module = _get_video_module()
    except ImportError as e:
        click.echo(click.style(f"❌ Video processing modules not available: {e}", fg="red"))
        return

    VideoProcessor = video_module["VideoProcessor"]
    EnhancedVideoProcessor = video_module["EnhancedVideoProcessor"]
    IntelligentVideoProcessor = video_module["IntelligentVideoProcessor"]

    if VideoProcessor is None:
        click.echo(
            click.style(
                "❌ Video processing modules not available. Please install required dependencies.",
                fg="red",
            )
        )
        return

    if method == "intelligent":
        if IntelligentVideoProcessor is None:
            click.echo(
                click.style(
                    "❌ Intelligent video processor not available. Using basic processor.",
                    fg="yellow",
                )
            )
            processor = EnhancedVideoProcessor() if EnhancedVideoProcessor else VideoProcessor()
        else:
            processor = IntelligentVideoProcessor()

        if dry_run:
            click.echo(
                click.style(
                    "🔍 Dry run mode - extracting frames and analyzing video only", fg="cyan"
                )
            )
            frame_paths = processor.extract_frames(input_video, fps)
            click.echo(
                click.style(
                    f"✅ Dry run complete. Extracted {len(frame_paths)} frames to {processor.temp_dir}",
                    fg="green",
                )
            )
            click.echo(click.style(f"📁 Temp directory: {processor.temp_dir}", fg="blue"))
            if hasattr(processor, "video_info"):
                click.echo(click.style(f"🎬 Video info: {processor.video_info}", fg="blue"))
            return

        if hasattr(processor, "remove_overlay_from_video_intelligent"):
            result = processor.remove_overlay_from_video_intelligent(
                video_path=input_video, output_path=output, fps=fps, context_window=context
            )
        else:
            result = processor.remove_overlay_from_video(
                video_path=input_video, output_path=output, fps=fps
            )
    else:
        processor = EnhancedVideoProcessor() if EnhancedVideoProcessor else VideoProcessor()
        if hasattr(processor, "remove_overlay_from_video"):
            result = processor.remove_overlay_from_video(
                video_path=input_video, output_path=output, fps=fps
            )
        else:
            click.echo(
                click.style("❌ Overlay removal not available with current processor.", fg="red")
            )
            return

    click.echo(f"Video processed successfully: {result}")


@videos.command()
@click.argument("input_video", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output directory path")
@click.option("--fps", "-f", default=8, help="Frame extraction rate (default: 8)")
def extract_frames(input_video, output, fps):
    """Extract frames from video to timestamped directory."""

    try:
        video_module = _get_video_module()
    except ImportError as e:
        click.echo(click.style(f"❌ Video processing modules not available: {e}", fg="red"))
        return

    VideoProcessor = video_module["VideoProcessor"]

    if VideoProcessor is None:
        click.echo(
            click.style(
                "❌ Video processing modules not available. Please install required dependencies.",
                fg="red",
            )
        )
        return

    processor = VideoProcessor()

    result_dir = processor.extract_frames_to_directory(
        video_path=input_video, output_dir=output, fps=fps
    )

    click.echo(click.style(f"✅ Frame extraction complete!", fg="bright_green"))
    click.echo(click.style(f"📁 Output directory: {result_dir}", fg="green"))


@videos.command()
@click.argument("frame_directory", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output video path")
@click.option("--fps", "-f", default=30.0, help="Output video FPS (default: 30)")
def frames_to_video(frame_directory, output, fps):
    """Convert frames back to video."""

    try:
        video_module = _get_video_module()
    except ImportError as e:
        click.echo(click.style(f"❌ Video processing modules not available: {e}", fg="red"))
        return

    VideoProcessor = video_module["VideoProcessor"]

    if VideoProcessor is None:
        click.echo(
            click.style(
                "❌ Video processing modules not available. Please install required dependencies.",
                fg="red",
            )
        )
        return

    processor = VideoProcessor()

    # Get all frame files from directory
    frame_dir = Path(frame_directory)
    frame_files = sorted([f for f in frame_dir.glob("*.png")])

    if not frame_files:
        click.echo(click.style("❌ No PNG frames found in directory", fg="red"))
        return

    if output is None:
        output = str(frame_dir.parent / f"{frame_dir.name}_reconstructed.mp4")

    frame_paths = [str(f) for f in frame_files]

    # Set video info manually for frames_to_video
    processor.video_info = {"original_fps": fps}

    result = processor.frames_to_video(frame_paths, output, fps)
    click.echo(f"Video created successfully: {result}")


if __name__ == "__main__":
    videos()
