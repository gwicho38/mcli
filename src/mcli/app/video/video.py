import base64
import json
import os
import queue
import shutil
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
import cv2
import numpy as np
import requests
from PIL import Image
from scipy import ndimage, spatial
from skimage import feature, morphology, restoration

# Add this to your existing CONFIG
CONFIG = {"temp_dir": "./temp", "output_dir": "./output"}


class VideoProcessor:
    """Handles video processing operations including frame extraction and reconstruction."""

    def __init__(self, temp_dir: str = CONFIG["temp_dir"]):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(CONFIG["output_dir"], exist_ok=True)

    def extract_frames(self, video_path: str, fps: int = 8) -> List[str]:
        """
        Extract frames from video at specified FPS.

        Args:
            video_path: Path to input video
            fps: Frames per second to extract

        Returns:
            List of paths to extracted frames
        """
        click.echo(click.style(f"Extracting frames from {video_path} at {fps} FPS...", fg="green"))

        # Clean temp directory
        # for file in os.listdir(self.temp_dir):
        # os.remove(os.path.join(self.temp_dir, file))

        # Extract frames
        video = cv2.VideoCapture(video_path)
        video_fps = video.get(cv2.CAP_PROP_FPS)
        frame_interval = int(video_fps / fps)
        frame_paths = []

        frame_count = 0
        frame_saved = 0

        with click.progressbar(
            length=int(video.get(cv2.CAP_PROP_FRAME_COUNT)), label="Extracting frames"
        ) as bar:
            while True:
                success, frame = video.read()
                if not success:
                    break

                if frame_count % frame_interval == 0:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_path = os.path.join(self.temp_dir, f"frame_{frame_saved:05d}.png")
                    Image.fromarray(frame_rgb).save(frame_path)
                    frame_paths.append(frame_path)
                    frame_saved += 1

                frame_count += 1
                bar.update(1)

        video.release()
        click.echo(f"Extracted {len(frame_paths)} frames.")

        # Save video info for reconstruction
        self.video_info = {
            "original_fps": video_fps,
            "width": int(video.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "total_frames": frame_count,
        }

        return frame_paths

    def extract_motion_vectors(self, video_path: str) -> Dict[str, Any]:
        """
        Extract motion vectors from video for temporal consistency.
        This is a simplified placeholder for actual motion vector extraction.

        Args:
            video_path: Path to input video

        Returns:
            Dictionary with motion vector data
        """
        # Placeholder for motion vector extraction
        # In a complete implementation, this would use optical flow or
        # dedicated motion vector extraction techniques
        click.echo(click.style("Extracting motion vectors...", fg="blue"))

        # Simple optical flow calculation between consecutive frames
        video = cv2.VideoCapture(video_path)
        ret, prev_frame = video.read()
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

        motion_data = {}
        frame_idx = 0

        with click.progressbar(
            length=int(video.get(cv2.CAP_PROP_FRAME_COUNT)) - 1, label="Analyzing motion"
        ) as bar:
            while True:
                ret, frame = video.read()
                if not ret:
                    break

                curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray,
                    curr_gray,
                    None,
                    pyr_scale=0.5,
                    levels=3,
                    winsize=15,
                    iterations=3,
                    poly_n=5,
                    poly_sigma=1.2,
                    flags=0,
                )

                # Store compressed flow data
                motion_data[f"frame_{frame_idx:05d}"] = {
                    "mean_x": float(np.mean(flow[..., 0])),
                    "mean_y": float(np.mean(flow[..., 1])),
                    "std_x": float(np.std(flow[..., 0])),
                    "std_y": float(np.std(flow[..., 1])),
                }

                prev_gray = curr_gray
                frame_idx += 1
                bar.update(1)

        video.release()
        click.echo("Motion analysis complete.")
        return motion_data

    def frames_to_video(self, frame_paths: List[str], output_path: str, fps: float = None) -> str:
        """
        Convert frames back to video.

        Args:
            frame_paths: List of paths to frames
            output_path: Path for output video
            fps: Frames per second (defaults to original video FPS)

        Returns:
            Path to output video
        """
        if not frame_paths:
            raise ValueError("No frames provided")

        if fps is None:
            fps = self.video_info.get("original_fps", 30)

        click.echo(
            click.style(
                f"Converting {len(frame_paths)} frames to video at {fps} FPS...", fg="green"
            )
        )

        # Get dimensions from first frame
        first_frame = cv2.imread(frame_paths[0])
        h, w, _ = first_frame.shape

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

        # Add frames to video
        with click.progressbar(frame_paths, label="Creating video") as bar:
            for frame_path in bar:
                frame = cv2.imread(frame_path)
                video_writer.write(frame)

        video_writer.release()
        click.echo(click.style(f"Video saved to {output_path}", fg="bright_green"))

        return output_path

    def apply_temporal_consistency(
        self, processed_frames: List[str], motion_data: Dict[str, Any]
    ) -> List[str]:
        """
        Apply temporal consistency to processed frames using motion data.
        This is a simplified implementation.

        Args:
            processed_frames: List of paths to processed frames
            motion_data: Motion vector data from extract_motion_vectors

        Returns:
            List of paths to temporally consistent frames
        """
        click.echo(click.style("Applying temporal consistency...", fg="blue"))

        if len(processed_frames) < 2:
            return processed_frames

        # Create temp directory for consistent frames
        consistent_dir = os.path.join(self.temp_dir, "consistent")
        os.makedirs(consistent_dir, exist_ok=True)

        # Simple temporal consistency with weighted blending
        consistent_frame_paths = []
        prev_frame = None

        with click.progressbar(
            enumerate(processed_frames), length=len(processed_frames), label="Reducing flicker"
        ) as bar:
            for i, frame_path in bar:
                frame = np.array(Image.open(frame_path))

                if prev_frame is not None:
                    # Simple blending with motion-aware weight
                    if f"frame_{i-1:05d}" in motion_data:
                        motion_info = motion_data[f"frame_{i-1:05d}"]
                        # Calculate blending weight based on motion magnitude
                        motion_magnitude = np.sqrt(
                            motion_info["mean_x"] ** 2 + motion_info["mean_y"] ** 2
                        )
                        # Less blending when motion is high, more when motion is low
                        blend_weight = max(0.1, min(0.3, 0.4 - motion_magnitude * 0.1))
                    else:
                        blend_weight = 0.2

                    # Blend frames
                    blended_frame = cv2.addWeighted(
                        prev_frame, blend_weight, frame, 1.0 - blend_weight, 0
                    )
                    frame = blended_frame

                # Save consistent frame
                out_path = os.path.join(consistent_dir, f"consistent_{i:05d}.png")
                Image.fromarray(frame.astype(np.uint8)).save(out_path)
                consistent_frame_paths.append(out_path)

                prev_frame = frame

        return consistent_frame_paths


class OverlayRemover:
    """Handles detection and removal of colored overlays from video frames."""

    def __init__(self):
        # Green overlay detection parameters (adjust based on your specific green)
        self.green_lower = np.array([40, 100, 100])  # HSV lower bound
        self.green_upper = np.array([80, 255, 255])  # HSV upper bound

        # Alternative RGB-based detection for bright green
        self.green_rgb_lower = np.array([0, 200, 0])
        self.green_rgb_upper = np.array([100, 255, 100])

    def detect_green_overlay(self, frame: np.ndarray, method: str = "hsv") -> np.ndarray:
        """
        Detect green overlay areas in a frame.

        Args:
            frame: Input frame as numpy array (RGB)
            method: Detection method ("hsv" or "rgb")

        Returns:
            Binary mask where overlay areas are white (255)
        """
        if method == "hsv":
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            mask = cv2.inRange(hsv, self.green_lower, self.green_upper)
        else:
            # RGB-based detection
            mask = cv2.inRange(frame, self.green_rgb_lower, self.green_rgb_upper)

        # Morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Remove small noise
        mask = (
            morphology.remove_small_objects(mask.astype(bool), min_size=50).astype(np.uint8) * 255
        )

        return mask

    def create_inpainting_mask(self, overlay_mask: np.ndarray, dilate_size: int = 3) -> np.ndarray:
        """
        Create an inpainting mask with slight dilation to ensure complete overlay removal.

        Args:
            overlay_mask: Binary mask of overlay areas
            dilate_size: Size of dilation kernel

        Returns:
            Dilated mask for inpainting
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_size, dilate_size))
        inpaint_mask = cv2.dilate(overlay_mask, kernel, iterations=1)
        return inpaint_mask

    def inpaint_frame(
        self, frame: np.ndarray, mask: np.ndarray, method: str = "telea"
    ) -> np.ndarray:
        """
        Inpaint frame areas marked by mask.

        Args:
            frame: Input frame (RGB)
            mask: Binary mask marking areas to inpaint
            method: Inpainting method ("telea" or "navier_stokes")

        Returns:
            Inpainted frame
        """
        # Convert to BGR for OpenCV
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Choose inpainting algorithm
        if method == "telea":
            inpainted_bgr = cv2.inpaint(frame_bgr, mask, 3, cv2.INPAINT_TELEA)
        else:
            inpainted_bgr = cv2.inpaint(frame_bgr, mask, 3, cv2.INPAINT_NS)

        # Convert back to RGB
        inpainted_rgb = cv2.cvtColor(inpainted_bgr, cv2.COLOR_BGR2RGB)
        return inpainted_rgb

    def remove_overlay_from_frame(
        self, frame: np.ndarray, debug: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Complete overlay removal pipeline for a single frame.

        Args:
            frame: Input frame (RGB)
            debug: If True, return debug information

        Returns:
            Tuple of (cleaned_frame, overlay_mask)
        """
        # Try HSV detection first
        mask_hsv = self.detect_green_overlay(frame, "hsv")

        # If HSV doesn't find much, try RGB
        if np.sum(mask_hsv) < 1000:  # Threshold for "not much found"
            mask_rgb = self.detect_green_overlay(frame, "rgb")
            overlay_mask = mask_rgb if np.sum(mask_rgb) > np.sum(mask_hsv) else mask_hsv
        else:
            overlay_mask = mask_hsv

        # Create inpainting mask
        inpaint_mask = self.create_inpainting_mask(overlay_mask)

        # Inpaint the frame
        cleaned_frame = self.inpaint_frame(frame, inpaint_mask, "telea")

        return cleaned_frame, overlay_mask


class EnhancedVideoProcessor(VideoProcessor):
    """Enhanced video processor with overlay removal capabilities."""

    def __init__(self, temp_dir: str = CONFIG["temp_dir"]):
        super().__init__(temp_dir)
        self.overlay_remover = OverlayRemover()

        # Create subdirectories for different processing stages
        self.masks_dir = os.path.join(temp_dir, "masks")
        self.cleaned_dir = os.path.join(temp_dir, "cleaned")
        os.makedirs(self.masks_dir, exist_ok=True)
        os.makedirs(self.cleaned_dir, exist_ok=True)

    def process_frames_remove_overlay(
        self, frame_paths: List[str], save_debug: bool = False
    ) -> List[str]:
        """
        Process all frames to remove green overlays.

        Args:
            frame_paths: List of paths to input frames
            save_debug: Whether to save debug masks

        Returns:
            List of paths to cleaned frames
        """
        click.echo(click.style("Removing green overlays from frames...", fg="cyan"))

        cleaned_frame_paths = []

        with click.progressbar(
            enumerate(frame_paths), length=len(frame_paths), label="Removing overlays"
        ) as bar:
            for i, frame_path in bar:
                # Load frame
                frame = np.array(Image.open(frame_path))

                # Remove overlay
                cleaned_frame, overlay_mask = self.overlay_remover.remove_overlay_from_frame(frame)

                # Save cleaned frame
                cleaned_path = os.path.join(self.cleaned_dir, f"cleaned_{i:05d}.png")
                Image.fromarray(cleaned_frame).save(cleaned_path)
                cleaned_frame_paths.append(cleaned_path)

                # Save debug mask if requested
                if save_debug:
                    mask_path = os.path.join(self.masks_dir, f"mask_{i:05d}.png")
                    Image.fromarray(overlay_mask).save(mask_path)

        click.echo(f"Processed {len(cleaned_frame_paths)} frames.")
        return cleaned_frame_paths

    def analyze_overlay_consistency(self, frame_paths: List[str]) -> Dict[str, Any]:
        """
        Analyze overlay patterns across frames for better temporal consistency.

        Args:
            frame_paths: List of frame paths

        Returns:
            Dictionary with overlay analysis data
        """
        click.echo(click.style("Analyzing overlay patterns...", fg="blue"))

        overlay_stats = {}

        for i, frame_path in enumerate(
            frame_paths[: min(50, len(frame_paths))]
        ):  # Sample first 50 frames
            frame = np.array(Image.open(frame_path))
            mask = self.overlay_remover.detect_green_overlay(frame, "hsv")

            overlay_stats[f"frame_{i:05d}"] = {
                "overlay_area": int(np.sum(mask > 0)),
                "overlay_density": float(np.sum(mask > 0) / (mask.shape[0] * mask.shape[1])),
                "overlay_centroid": self._calculate_centroid(mask),
            }

        return overlay_stats

    def _calculate_centroid(self, mask: np.ndarray) -> Tuple[float, float]:
        """Calculate centroid of overlay mask."""
        if np.sum(mask) == 0:
            return (0.0, 0.0)

        moments = cv2.moments(mask)
        if moments["m00"] == 0:
            return (0.0, 0.0)

        cx = moments["m10"] / moments["m00"]
        cy = moments["m01"] / moments["m00"]
        return (float(cx), float(cy))

    def remove_overlay_from_video(
        self,
        video_path: str,
        output_path: str = None,
        fps: int = 8,
        apply_temporal_smoothing: bool = True,
    ) -> str:
        """
        Complete pipeline to remove overlays from video.

        Args:
            video_path: Input video path
            output_path: Output video path (auto-generated if None)
            fps: Frame extraction rate
            apply_temporal_smoothing: Whether to apply temporal consistency

        Returns:
            Path to output video
        """
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(CONFIG["output_dir"], f"{base_name}_cleaned.mp4")

        try:
            # Step 1: Extract frames
            frame_paths = self.extract_frames(video_path, fps)

            # Step 2: Extract motion vectors for temporal consistency
            motion_data = (
                self.extract_motion_vectors(video_path) if apply_temporal_smoothing else None
            )

            # Step 3: Remove overlays from frames
            cleaned_frame_paths = self.process_frames_remove_overlay(frame_paths, save_debug=True)

            # Step 4: Apply temporal consistency if requested
            if apply_temporal_smoothing and motion_data:
                final_frame_paths = self.apply_temporal_consistency(
                    cleaned_frame_paths, motion_data
                )
            else:
                final_frame_paths = cleaned_frame_paths

            # Step 5: Convert back to video
            output_video = self.frames_to_video(final_frame_paths, output_path)

            click.echo(
                click.style(
                    f"✅ Overlay removal complete! Output: {output_video}", fg="bright_green"
                )
            )
            return output_video

        except Exception as e:
            click.echo(click.style(f"❌ Error during processing: {str(e)}", fg="red"))
            raise


# Add this to your existing CONFIG
CONFIG = {"temp_dir": "./temp", "output_dir": "./output"}


class AdvancedOverlayRemover:
    """Advanced overlay removal with intelligent content reconstruction."""

    def __init__(self):
        # Green overlay detection parameters
        self.green_lower = np.array([40, 100, 100])  # HSV lower bound
        self.green_upper = np.array([80, 255, 255])  # HSV upper bound

        # Alternative RGB-based detection for bright green
        self.green_rgb_lower = np.array([0, 180, 0])
        self.green_rgb_upper = np.array([120, 255, 120])

        # Patch matching parameters
        self.patch_size = 9
        self.search_radius = 50
        self.coherence_threshold = 0.85

    def detect_green_overlay(self, frame: np.ndarray, method: str = "combined") -> np.ndarray:
        """Enhanced green overlay detection with multiple methods."""
        if method == "combined":
            # HSV detection
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            mask_hsv = cv2.inRange(hsv, self.green_lower, self.green_upper)

            # RGB detection
            mask_rgb = cv2.inRange(frame, self.green_rgb_lower, self.green_rgb_upper)

            # Combine masks
            mask = cv2.bitwise_or(mask_hsv, mask_rgb)

            # Advanced saturation-based detection for bright colors
            saturation = hsv[:, :, 1]
            value = hsv[:, :, 2]
            bright_saturated = (saturation > 150) & (value > 150)

            # Green hue detection
            hue = hsv[:, :, 0]
            green_hue = (hue >= 40) & (hue <= 80)

            # Combine all conditions
            advanced_mask = bright_saturated & green_hue
            mask = cv2.bitwise_or(mask, advanced_mask.astype(np.uint8) * 255)
        else:
            # Use single method as before
            if method == "hsv":
                hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
                mask = cv2.inRange(hsv, self.green_lower, self.green_upper)
            else:
                mask = cv2.inRange(frame, self.green_rgb_lower, self.green_rgb_upper)

        # Enhanced morphological operations
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        # Close small gaps
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_medium)
        # Remove noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small)

        # Remove small objects and fill holes
        mask = (
            morphology.remove_small_objects(mask.astype(bool), min_size=30).astype(np.uint8) * 255
        )
        mask = (
            morphology.remove_small_holes(mask.astype(bool), area_threshold=100).astype(np.uint8)
            * 255
        )

        return mask

    def find_similar_patches(
        self, frame: np.ndarray, mask: np.ndarray, target_point: Tuple[int, int]
    ) -> np.ndarray:
        """Find similar patches in the frame for exemplar-based inpainting."""
        y, x = target_point
        h, w = frame.shape[:2]

        # Extract target patch (known pixels around the hole)
        half_patch = self.patch_size // 2
        y_start, y_end = max(0, y - half_patch), min(h, y + half_patch + 1)
        x_start, x_end = max(0, x - half_patch), min(w, x + half_patch + 1)

        target_patch = frame[y_start:y_end, x_start:x_end]
        target_mask = mask[y_start:y_end, x_start:x_end]

        best_patches = []
        best_scores = []

        # Search for similar patches in valid areas
        search_y_start = max(0, y - self.search_radius)
        search_y_end = min(h - self.patch_size, y + self.search_radius)
        search_x_start = max(0, x - self.search_radius)
        search_x_end = min(w - self.patch_size, x + self.search_radius)

        for sy in range(search_y_start, search_y_end, 2):  # Step by 2 for speed
            for sx in range(search_x_start, search_x_end, 2):
                candidate_patch = frame[sy : sy + self.patch_size, sx : sx + self.patch_size]
                candidate_mask = mask[sy : sy + self.patch_size, sx : sx + self.patch_size]

                # Skip if candidate area has overlay
                if np.any(candidate_mask > 0):
                    continue

                # Calculate similarity only on known pixels
                known_pixels = target_mask == 0
                if np.sum(known_pixels) < self.patch_size:  # Need enough known pixels
                    continue

                # Resize patches if needed
                if candidate_patch.shape != target_patch.shape:
                    continue

                # Calculate normalized cross-correlation on known pixels
                target_known = target_patch[known_pixels]
                candidate_known = candidate_patch[known_pixels]

                if len(target_known) > 0:
                    correlation = np.corrcoef(target_known.flatten(), candidate_known.flatten())[
                        0, 1
                    ]
                    if not np.isnan(correlation):
                        best_patches.append(candidate_patch)
                        best_scores.append(correlation)

        # Return best matching patches
        if best_patches:
            best_indices = np.argsort(best_scores)[-3:]  # Top 3 matches
            return [best_patches[i] for i in best_indices]
        else:
            return []

    def exemplar_based_inpainting(self, frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Advanced exemplar-based inpainting for intelligent content reconstruction."""
        result = frame.copy()
        mask_to_fill = mask.copy()

        # Find boundary of the region to fill
        contours, _ = cv2.findContours(mask_to_fill, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)

            # Process region in patches
            for py in range(y, y + h, self.patch_size // 2):
                for px in range(x, x + w, self.patch_size // 2):
                    if mask_to_fill[py, px] > 0:  # Need to fill this pixel
                        # Find similar patches
                        similar_patches = self.find_similar_patches(frame, mask, (py, px))

                        if similar_patches:
                            # Blend the best patches
                            blended_patch = np.mean(similar_patches, axis=0).astype(np.uint8)

                            # Apply to result
                            patch_h, patch_w = blended_patch.shape[:2]
                            y_end = min(result.shape[0], py + patch_h)
                            x_end = min(result.shape[1], px + patch_w)

                            # Only fill masked areas
                            patch_mask = mask_to_fill[py:y_end, px:x_end]
                            mask_indices = patch_mask > 0

                            if np.any(mask_indices):
                                result[py:y_end, px:x_end][mask_indices] = blended_patch[
                                    : y_end - py, : x_end - px
                                ][mask_indices]

        return result

    def temporal_reference_inpainting(
        self,
        current_frame: np.ndarray,
        reference_frames: List[np.ndarray],
        mask: np.ndarray,
        motion_vectors: Optional[Dict] = None,
    ) -> np.ndarray:
        """Use multiple reference frames for better content reconstruction."""
        if not reference_frames:
            return self.exemplar_based_inpainting(current_frame, mask)

        result = current_frame.copy()

        # For high-speed video, we need to be more selective about reference frames
        # Use frames that are more likely to have similar content

        # Simple approach: weighted average of valid pixels from reference frames
        valid_pixels = np.zeros_like(current_frame, dtype=np.float32)
        weight_sum = np.zeros(mask.shape, dtype=np.float32)

        for i, ref_frame in enumerate(reference_frames):
            if ref_frame.shape == current_frame.shape:
                # Calculate weight based on frame distance (closer frames get higher weight)
                weight = 1.0 / (i + 1)

                # Only use pixels that aren't masked in current frame
                ref_mask = self.detect_green_overlay(ref_frame, "combined")
                valid_mask = (ref_mask == 0) & (mask > 0)  # Valid in ref, needs filling in current

                if np.any(valid_mask):
                    valid_pixels[valid_mask] += ref_frame[valid_mask].astype(np.float32) * weight
                    weight_sum[valid_mask] += weight

        # Apply weighted average where we have valid data
        fill_mask = weight_sum > 0
        if np.any(fill_mask):
            # Fix broadcasting issue by expanding weight_sum to match color channels
            weight_sum_expanded = weight_sum[:, :, np.newaxis]  # Add channel dimension
            result[fill_mask] = (valid_pixels[fill_mask] / weight_sum_expanded[fill_mask]).astype(
                np.uint8
            )

        # For remaining unfilled areas, use exemplar-based inpainting
        remaining_mask = mask & (~fill_mask.astype(np.uint8) * 255)
        if np.any(remaining_mask > 0):
            result = self.exemplar_based_inpainting(result, remaining_mask)

        return result

    def content_aware_fill(self, frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Advanced content-aware fill using multiple techniques."""
        # Step 1: Try edge-preserving inpainting for smooth areas
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Use Fast Marching Method for smooth regions
        inpainted_fmm = cv2.inpaint(frame_bgr, mask, 3, cv2.INPAINT_TELEA)

        # Use Navier-Stokes for textured regions
        inpainted_ns = cv2.inpaint(frame_bgr, mask, 3, cv2.INPAINT_NS)

        # Detect textured vs smooth regions
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        # Calculate local variance to detect texture
        kernel = np.ones((9, 9), np.float32) / 81
        local_mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        local_variance = cv2.filter2D((gray.astype(np.float32) - local_mean) ** 2, -1, kernel)

        # Create texture mask
        texture_threshold = np.mean(local_variance) * 1.5
        texture_mask = (local_variance > texture_threshold).astype(np.float32)

        # Smooth the transition
        texture_mask = cv2.GaussianBlur(texture_mask, (15, 15), 5)

        # Blend based on texture
        result_bgr = inpainted_ns.astype(np.float32) * texture_mask[
            :, :, np.newaxis
        ] + inpainted_fmm.astype(np.float32) * (1 - texture_mask[:, :, np.newaxis])

        result_rgb = cv2.cvtColor(result_bgr.astype(np.uint8), cv2.COLOR_BGR2RGB)

        # Step 2: Apply exemplar-based inpainting for better results
        final_result = self.exemplar_based_inpainting(result_rgb, mask)

        return final_result

    def remove_overlay_with_context(
        self, frame: np.ndarray, reference_frames: List[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Remove overlay with intelligent content reconstruction using context.

        Args:
            frame: Current frame
            reference_frames: List of reference frames for temporal consistency

        Returns:
            Tuple of (cleaned_frame, overlay_mask)
        """
        # Detect overlay
        overlay_mask = self.detect_green_overlay(frame, "combined")

        if np.sum(overlay_mask) == 0:
            return frame, overlay_mask

        # Use temporal reference if available and not too many reference frames
        if reference_frames and len(reference_frames) <= 5:
            cleaned_frame = self.temporal_reference_inpainting(
                frame, reference_frames, overlay_mask
            )
        else:
            # Use content-aware fill for single frame processing
            cleaned_frame = self.content_aware_fill(frame, overlay_mask)

        return cleaned_frame, overlay_mask


class IntelligentVideoProcessor(VideoProcessor):
    """Enhanced processor with intelligent overlay removal capabilities."""

    def __init__(self, temp_dir: str = CONFIG["temp_dir"]):
        super().__init__(temp_dir)
        self.overlay_remover = AdvancedOverlayRemover()

        # Create processing directories
        self.masks_dir = os.path.join(temp_dir, "masks")
        self.cleaned_dir = os.path.join(temp_dir, "cleaned")
        self.reference_dir = os.path.join(temp_dir, "references")
        os.makedirs(self.masks_dir, exist_ok=True)
        os.makedirs(self.cleaned_dir, exist_ok=True)
        os.makedirs(self.reference_dir, exist_ok=True)

    def extract_motion_vectors_highspeed(
        self, video_path: str, sample_rate: int = 10
    ) -> Dict[str, Any]:
        """
        Optimized motion vector extraction for high-speed videos.
        Sample every Nth frame to reduce computation while maintaining accuracy.
        """
        click.echo(click.style("Extracting motion vectors (high-speed optimized)...", fg="blue"))

        video = cv2.VideoCapture(video_path)
        ret, prev_frame = video.read()
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

        motion_data = {}
        frame_idx = 0
        sample_count = 0

        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

        with click.progressbar(
            length=total_frames // sample_rate, label="Analyzing motion (sampled)"
        ) as bar:
            while True:
                ret, frame = video.read()
                if not ret:
                    break

                # Sample every Nth frame for high-speed videos
                if frame_idx % sample_rate == 0:
                    curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                    # Use sparse optical flow for better performance
                    corners = cv2.goodFeaturesToTrack(
                        prev_gray, maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7
                    )

                    if corners is not None:
                        # Calculate optical flow
                        next_corners, status, error = cv2.calcOpticalFlowPyrLK(
                            prev_gray, curr_gray, corners, None
                        )

                        # Filter good points
                        good_old = corners[status == 1]
                        good_new = next_corners[status == 1]

                        if len(good_old) > 0:
                            # Calculate motion statistics
                            motion_vectors = good_new - good_old
                            motion_data[f"frame_{frame_idx:05d}"] = {
                                "mean_x": float(np.mean(motion_vectors[:, 0])),
                                "mean_y": float(np.mean(motion_vectors[:, 1])),
                                "std_x": float(np.std(motion_vectors[:, 0])),
                                "std_y": float(np.std(motion_vectors[:, 1])),
                                "magnitude": float(np.mean(np.linalg.norm(motion_vectors, axis=1))),
                                "sample_points": len(good_old),
                            }

                    prev_gray = curr_gray
                    sample_count += 1
                    bar.update(1)

                frame_idx += 1

        video.release()
        click.echo(f"Motion analysis complete. Sampled {sample_count} frames.")
        return motion_data

    def process_with_temporal_context(
        self, frame_paths: List[str], context_window: int = 3
    ) -> List[str]:
        """
        Process frames with temporal context for better reconstruction.

        Args:
            frame_paths: List of frame paths
            context_window: Number of frames to use as reference (on each side)

        Returns:
            List of cleaned frame paths
        """
        click.echo(click.style("Processing with temporal context...", fg="cyan"))

        cleaned_frame_paths = []

        # Pre-load some frames for context
        frame_cache = {}

        with click.progressbar(
            enumerate(frame_paths), length=len(frame_paths), label="Intelligent overlay removal"
        ) as bar:
            for i, frame_path in bar:
                # Load current frame
                current_frame = np.array(Image.open(frame_path))

                # Collect reference frames
                reference_frames = []

                # Look backwards and forwards for reference frames
                for offset in range(-context_window, context_window + 1):
                    ref_idx = i + offset
                    if ref_idx != i and 0 <= ref_idx < len(frame_paths):
                        ref_path = frame_paths[ref_idx]

                        # Use cache to avoid reloading
                        if ref_path not in frame_cache:
                            frame_cache[ref_path] = np.array(Image.open(ref_path))

                        reference_frames.append(frame_cache[ref_path])

                # Remove overlay with context
                cleaned_frame, overlay_mask = self.overlay_remover.remove_overlay_with_context(
                    current_frame, reference_frames
                )

                # Save results
                cleaned_path = os.path.join(self.cleaned_dir, f"cleaned_{i:05d}.png")
                Image.fromarray(cleaned_frame).save(cleaned_path)
                cleaned_frame_paths.append(cleaned_path)

                # Save mask for debugging
                mask_path = os.path.join(self.masks_dir, f"mask_{i:05d}.png")
                Image.fromarray(overlay_mask).save(mask_path)

                # Manage cache size (keep only recent frames)
                if len(frame_cache) > context_window * 4:
                    oldest_key = list(frame_cache.keys())[0]
                    del frame_cache[oldest_key]

        click.echo(f"Processed {len(cleaned_frame_paths)} frames with temporal context.")
        return cleaned_frame_paths

    def remove_overlay_from_video_intelligent(
        self, video_path: str, output_path: str = None, fps: int = 30, context_window: int = 3
    ) -> str:
        """
        Complete pipeline for intelligent overlay removal while maintaining original video speed.

        Args:
            video_path: Input video path
            output_path: Output video path
            fps: Frame extraction rate (higher = better quality, slower processing)
            context_window: Temporal context window size

        Returns:
            Path to output video
        """
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(CONFIG["output_dir"], f"{base_name}_intelligent_cleaned.mp4")

        try:
            click.echo(click.style("🚀 Starting intelligent overlay removal...", fg="bright_cyan"))
            click.echo(
                click.style(
                    f"📊 Extraction FPS: {fps} (higher = better quality, slower processing)",
                    fg="blue",
                )
            )

            # Step 1: Extract frames
            frame_paths = self.extract_frames(video_path, fps)

            # Step 2: Process with temporal context for intelligent reconstruction
            cleaned_frame_paths = self.process_with_temporal_context(frame_paths, context_window)

            # Step 3: Extract motion data (sampled for performance)
            motion_data = self.extract_motion_vectors_highspeed(
                video_path, sample_rate=max(1, fps // 6)
            )

            # Step 4: Apply light temporal smoothing
            if motion_data:
                final_frame_paths = self.apply_temporal_consistency(
                    cleaned_frame_paths, motion_data
                )
            else:
                final_frame_paths = cleaned_frame_paths

            # Step 5: Reconstruct video at extraction FPS to maintain original speed
            output_video = self.frames_to_video(final_frame_paths, output_path)

            click.echo(
                click.style(
                    f"✅ Intelligent overlay removal complete! Output: {output_video}",
                    fg="bright_green",
                )
            )
            click.echo(
                click.style(
                    f"⏱️  Original speed maintained using {self.video_info.get('extraction_fps', fps)} FPS",
                    fg="green",
                )
            )

            return output_video

        except Exception as e:
            click.echo(click.style(f"❌ Error during processing: {str(e)}", fg="red"))
            raise


# Enhanced command line interface
@click.command()
@click.argument("input_video", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output video path")
@click.option(
    "--fps",
    "-f",
    default=30,
    help="Frame extraction rate (default: 30 to maintain quality). Higher values = better quality but slower processing",
)
@click.option(
    "--output-fps",
    type=float,
    help="Output video FPS (defaults to extraction FPS for correct speed)",
)
@click.option("--context", "-c", default=3, help="Temporal context window size (default: 3)")
@click.option(
    "--method",
    type=click.Choice(["intelligent", "basic"]),
    default="intelligent",
    help="Processing method (default: intelligent)",
)
def remove_overlay(input_video, output, fps, output_fps, context, method):
    """Remove overlays from videos with intelligent content reconstruction."""

    if method == "intelligent":
        processor = IntelligentVideoProcessor()

        # Process video
        result = processor.remove_overlay_from_video_intelligent(
            video_path=input_video, output_path=output, fps=fps, context_window=context
        )

        # If user specified different output FPS, recreate video
        if output_fps and output_fps != fps:
            click.echo(
                click.style(f"Recreating video with custom output FPS: {output_fps}", fg="yellow")
            )

            # Get the cleaned frames
            cleaned_frames = [
                os.path.join(processor.cleaned_dir, f)
                for f in sorted(os.listdir(processor.cleaned_dir))
                if f.endswith(".png")
            ]

            # Create new output path
            base_name = os.path.splitext(os.path.basename(input_video))[0]
            custom_output = os.path.join(
                CONFIG["output_dir"], f"{base_name}_custom_fps_{output_fps}.mp4"
            )

            # Recreate with custom FPS
            result = processor.frames_to_video(cleaned_frames, custom_output, output_fps)
    else:
        # Fallback to basic processing
        from your_original_module import EnhancedVideoProcessor

        processor = EnhancedVideoProcessor()
        result = processor.remove_overlay_from_video(
            video_path=input_video, output_path=output, fps=fps
        )

    click.echo(f"Video processed successfully: {result}")
    click.echo(
        click.style("📝 Note: Output video should maintain original playback speed", fg="green")
    )


@click.group()
def main():
    """Advanced video overlay removal tool with intelligent content reconstruction."""
    pass


main.add_command(remove_overlay)

if __name__ == "__main__":
    main()
