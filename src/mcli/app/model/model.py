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

# Configuration paths based on the provided directory structure
CONFIG = {
    "hunyuan_video_model": "",
    "hunyuan_vae": "",
    "clip_vision_model": "",
    "text_encoder": "",
    "controlnet_model": "",
    "lora_model": "",  # Example LoRA
    "temp_dir": "./temp_frames",
    "output_dir": "./output",
    "comfyui_api": "",
}


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
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))

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


class ComfyUIClient:
    """Client for interacting with ComfyUI API for video generation."""

    def __init__(self, api_url: str = CONFIG["comfyui_api"]):
        self.api_url = api_url
        self.client_id = str(uuid.uuid4())
        self.session = requests.Session()

    def queue_prompt(self, prompt: Dict[str, Any]) -> str:
        """
        Queue a prompt in ComfyUI.

        Args:
            prompt: ComfyUI workflow prompt

        Returns:
            Prompt ID
        """
        p = {"prompt": prompt, "client_id": self.client_id}
        response = self.session.post(f"{self.api_url}/prompt", json=p)
        return response.json()["prompt_id"]

    def get_image(self, filename: str, subfolder: str, folder_type: str) -> Image.Image:
        """
        Get an image from ComfyUI.

        Args:
            filename: Image filename
            subfolder: Image subfolder
            folder_type: Folder type (input or output)

        Returns:
            PIL Image
        """
        data = {"filename": filename, "subfolder": subfolder, "folder_type": folder_type}
        response = self.session.get(f"{self.api_url}/view", params=data)
        return Image.open(response.raw)

    def upload_image(self, image_path: str) -> Tuple[str, str]:
        """
        Upload an image to ComfyUI.

        Args:
            image_path: Path to image

        Returns:
            Tuple of (filename, subfolder)
        """
        # Read the image and convert to base64
        with open(image_path, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode("utf-8")

        # Upload the image
        filename = os.path.basename(image_path)
        data = {
            "image": encoded_image,
            "filename": filename,
            "subfolder": "v2v_input",  # Custom subfolder for our workflow
            "type": "input",
        }
        response = self.session.post(f"{self.api_url}/upload/image", json=data)
        return filename, "v2v_input"

    def wait_for_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """
        Wait for prompt to complete.

        Args:
            prompt_id: Prompt ID

        Returns:
            Prompt result
        """
        # Create a spinner to indicate processing
        with click.progressbar(
            length=100, label=f"Processing frame with ComfyUI (ID: {prompt_id})"
        ) as bar:
            progress = 0
            while progress < 100:
                response = self.session.get(f"{self.api_url}/history/{prompt_id}")
                if response.status_code == 200:
                    data = response.json()
                    if prompt_id in data:
                        if "outputs" in data[prompt_id]:
                            # Complete
                            bar.update(100 - progress)
                            return data[prompt_id]
                        # Update progress based on execution state
                        if "executed" in data[prompt_id]:
                            executed_nodes = len(data[prompt_id]["executed"])
                            total_nodes = len(data[prompt_id].get("prompt", {}))
                            if total_nodes > 0:
                                new_progress = min(99, int((executed_nodes / total_nodes) * 100))
                                bar.update(new_progress - progress)
                                progress = new_progress

                time.sleep(0.5)

            # If we get here, assume it's done and try to get the final result
            response = self.session.get(f"{self.api_url}/history/{prompt_id}")
            if response.status_code == 200:
                data = response.json()
                if prompt_id in data:
                    return data[prompt_id]

            raise ValueError(f"Processing failed for prompt {prompt_id}")

    def process_frame(
        self,
        frame_path: str,
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.75,
        guidance_scale: float = 7.5,
        use_controlnet: bool = True,
        use_lora: bool = True,
    ) -> str:
        """
        Process a frame using ComfyUI.

        Args:
            frame_path: Path to input frame
            prompt: Text prompt for generation
            negative_prompt: Negative text prompt
            strength: Denoising strength (0-1)
            guidance_scale: Classifier-free guidance scale
            use_controlnet: Whether to use ControlNet
            use_lora: Whether to use LoRA

        Returns:
            Path to processed frame
        """
        # Upload the frame
        filename, subfolder = self.upload_image(frame_path)

        # Build workflow for frame processing
        workflow = self.build_frame_processing_workflow(
            filename=filename,
            subfolder=subfolder,
            prompt=prompt,
            negative_prompt=negative_prompt,
            strength=strength,
            guidance_scale=guidance_scale,
            use_controlnet=use_controlnet,
            use_lora=use_lora,
        )

        # Queue the prompt
        prompt_id = self.queue_prompt(workflow)

        # Wait for completion
        result = self.wait_for_prompt(prompt_id)

        # Get the output image
        output_node = None
        for node_id, node_output in result["outputs"].items():
            if "images" in node_output:
                output_node = node_output
                break

        if output_node is None:
            raise ValueError("No output image found in result")

        # Save the output image
        output_filename = output_node["images"][0]["filename"]
        output_subfolder = output_node["images"][0]["subfolder"]

        output_path = os.path.join(CONFIG["temp_dir"], f"processed_{os.path.basename(frame_path)}")

        # Download and save
        img = self.get_image(output_filename, output_subfolder, "output")
        img.save(output_path)

        return output_path

    def build_frame_processing_workflow(
        self,
        filename: str,
        subfolder: str,
        prompt: str,
        negative_prompt: str,
        strength: float,
        guidance_scale: float,
        use_controlnet: bool,
        use_lora: bool,
    ) -> Dict[str, Any]:
        """
        Build a ComfyUI workflow for frame processing.

        Args:
            filename: Input frame filename
            subfolder: Input frame subfolder
            prompt: Text prompt
            negative_prompt: Negative text prompt
            strength: Denoising strength
            guidance_scale: CFG scale
            use_controlnet: Whether to use ControlNet
            use_lora: Whether to use LoRA

        Returns:
            ComfyUI workflow dictionary
        """
        # This is a simplified workflow that would need to be adjusted based on
        # your exact ComfyUI nodes and workflow requirements

        workflow = {
            "1": {"inputs": {"image": f"{subfolder}/{filename}"}, "class_type": "LoadImage"},
            "2": {"inputs": {"text": prompt, "clip": ["5", 0]}, "class_type": "CLIPTextEncode"},
            "3": {
                "inputs": {"text": negative_prompt, "clip": ["5", 0]},
                "class_type": "CLIPTextEncode",
            },
            "4": {
                "inputs": {
                    "seed": 42,
                    "steps": 20,
                    "cfg": guidance_scale,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": strength,
                    "model": ["5", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["10", 0],
                },
                "class_type": "KSampler",
            },
            "5": {
                "inputs": {"model_name": os.path.basename(CONFIG["hunyuan_video_model"])},
                "class_type": "HunyuanVideoModelLoader",
            },
            "6": {
                "inputs": {"vae_name": os.path.basename(CONFIG["hunyuan_vae"])},
                "class_type": "HunyuanVideoVAELoader",
            },
            "7": {"inputs": {"samples": ["4", 0], "vae": ["6", 0]}, "class_type": "VAEDecode"},
            "8": {
                "inputs": {"filename_prefix": "v2v_output", "images": ["7", 0]},
                "class_type": "SaveImage",
            },
            "9": {
                "inputs": {"image": ["1", 0], "text_encoder": ["5", 1], "vae": ["6", 0]},
                "class_type": "HunyuanImagePreprocessor",
            },
            "10": {"inputs": {"pixels": ["9", 0], "vae": ["6", 0]}, "class_type": "VAEEncode"},
        }

        # Add LoRA if requested
        if use_lora:
            workflow["11"] = {
                "inputs": {
                    "model": ["5", 0],
                    "clip": ["5", 0],
                    "lora_name": os.path.basename(CONFIG["lora_model"]),
                    "strength_model": 0.8,
                    "strength_clip": 0.8,
                },
                "class_type": "LoraLoader",
            }
            # Update model and clip reference
            workflow["4"]["inputs"]["model"] = ["11", 0]
            workflow["2"]["inputs"]["clip"] = ["11", 1]
            workflow["3"]["inputs"]["clip"] = ["11", 1]

        # Add ControlNet if requested
        if use_controlnet:
            workflow["12"] = {
                "inputs": {"control_net_name": os.path.basename(CONFIG["controlnet_model"])},
                "class_type": "ControlNetLoader",
            }
            workflow["13"] = {
                "inputs": {"image": ["1", 0], "control_net": ["12", 0], "strength": 0.6},
                "class_type": "ControlNetApply",
            }
            # Update model with ControlNet
            if use_lora:
                workflow["13"]["inputs"]["model"] = ["11", 0]
                workflow["4"]["inputs"]["model"] = ["13", 0]
            else:
                workflow["13"]["inputs"]["model"] = ["5", 0]
                workflow["4"]["inputs"]["model"] = ["13", 0]

        return workflow


class VideoToVideoGenerator:
    """Main class for video-to-video generation workflow."""

    def __init__(self):
        self.video_processor = VideoProcessor()
        self.comfyui_client = ComfyUIClient()

    def generate(
        self,
        input_video: str,
        output_video: str,
        prompt: str,
        negative_prompt: str = "",
        fps: int = 8,
        strength: float = 0.75,
        guidance_scale: float = 7.5,
        use_controlnet: bool = True,
        use_lora: bool = True,
        use_temporal_consistency: bool = True,
        batch_size: int = 1,
    ) -> str:
        """
        Generate a video using the video-to-video workflow.

        Args:
            input_video: Path to input video
            output_video: Path to output video
            prompt: Text prompt for generation
            negative_prompt: Negative text prompt
            fps: Frames per second to process
            strength: Denoising strength (0-1)
            guidance_scale: Classifier-free guidance scale
            use_controlnet: Whether to use ControlNet
            use_lora: Whether to use LoRA
            use_temporal_consistency: Whether to apply temporal consistency
            batch_size: Number of frames to process in parallel

        Returns:
            Path to output video
        """
        click.echo(click.style("=" * 80, fg="bright_blue"))
        click.echo(
            click.style(
                f"Video-to-Video Generation: {input_video} → {output_video}", fg="bright_blue"
            )
        )
        click.echo(click.style("=" * 80, fg="bright_blue"))
        click.echo(f"Settings:\n- Prompt: {prompt}")
        if negative_prompt:
            click.echo(f"- Negative prompt: {negative_prompt}")
        click.echo(f"- Processing at {fps} FPS")
        click.echo(f"- Denoising strength: {strength}")
        click.echo(f"- Guidance scale: {guidance_scale}")
        click.echo(f"- Using ControlNet: {use_controlnet}")
        click.echo(f"- Using LoRA: {use_lora}")
        click.echo(f"- Temporal consistency: {use_temporal_consistency}")
        click.echo(f"- Batch size: {batch_size}")
        click.echo(click.style("=" * 80, fg="bright_blue"))

        # Extract frames from input video
        frame_paths = self.video_processor.extract_frames(input_video, fps=fps)

        # Extract motion data for temporal consistency if needed
        motion_data = {}
        if use_temporal_consistency:
            motion_data = self.video_processor.extract_motion_vectors(input_video)

        # Process frames
        processed_frame_paths = self.process_frames(
            frame_paths=frame_paths,
            prompt=prompt,
            negative_prompt=negative_prompt,
            strength=strength,
            guidance_scale=guidance_scale,
            use_controlnet=use_controlnet,
            use_lora=use_lora,
            batch_size=batch_size,
        )

        # Apply temporal consistency if requested
        if use_temporal_consistency:
            processed_frame_paths = self.video_processor.apply_temporal_consistency(
                processed_frame_paths, motion_data
            )

        # Convert frames to video
        output_path = self.video_processor.frames_to_video(
            frame_paths=processed_frame_paths, output_path=output_video, fps=fps
        )

        click.echo(click.style("=" * 80, fg="bright_green"))
        click.echo(click.style(f"Video generation complete: {output_path}", fg="bright_green"))
        click.echo(click.style("=" * 80, fg="bright_green"))
        return output_path

    def process_frames(
        self,
        frame_paths: List[str],
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.75,
        guidance_scale: float = 7.5,
        use_controlnet: bool = True,
        use_lora: bool = True,
        batch_size: int = 1,
    ) -> List[str]:
        """
        Process frames using ComfyUI.

        Args:
            frame_paths: List of paths to frames
            prompt: Text prompt for generation
            negative_prompt: Negative text prompt
            strength: Denoising strength (0-1)
            guidance_scale: Classifier-free guidance scale
            use_controlnet: Whether to use ControlNet
            use_lora: Whether to use LoRA
            batch_size: Number of frames to process in parallel

        Returns:
            List of paths to processed frames
        """
        click.echo(click.style(f"Processing {len(frame_paths)} frames...", fg="green"))
        processed_frame_paths = []

        if batch_size <= 1:
            # Process frames sequentially
            with click.progressbar(
                enumerate(frame_paths), length=len(frame_paths), label="Processing frames"
            ) as bar:
                for i, frame_path in bar:
                    processed_frame_path = self.comfyui_client.process_frame(
                        frame_path=frame_path,
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        strength=strength,
                        guidance_scale=guidance_scale,
                        use_controlnet=use_controlnet,
                        use_lora=use_lora,
                    )
                    processed_frame_paths.append(processed_frame_path)
        else:
            # Process frames in parallel batches
            for i in range(0, len(frame_paths), batch_size):
                batch = frame_paths[i : i + batch_size]
                click.echo(
                    f"Processing batch {i//batch_size+1}/{(len(frame_paths)-1)//batch_size+1} ({len(batch)} frames)"
                )

                # Use threading to process batch in parallel
                threads = []
                results_queue = queue.Queue()

                for j, frame_path in enumerate(batch):
                    thread = threading.Thread(
                        target=self._process_frame_thread,
                        args=(
                            frame_path,
                            prompt,
                            negative_prompt,
                            strength,
                            guidance_scale,
                            use_controlnet,
                            use_lora,
                            i + j,
                            results_queue,
                        ),
                    )
                    threads.append(thread)
                    thread.start()

                # Wait for all threads to complete
                with click.progressbar(
                    length=len(batch), label=f"Batch {i//batch_size+1} progress"
                ) as bar:
                    completed = 0
                    while completed < len(batch):
                        # Check how many items are in the queue
                        new_completed = results_queue.qsize() - completed
                        if new_completed > 0:
                            bar.update(new_completed)
                            completed += new_completed
                        time.sleep(0.5)

                # Join all threads
                for thread in threads:
                    thread.join()

                # Get results in correct order
                batch_results = []
                while not results_queue.empty():
                    batch_results.append(results_queue.get())

                # Sort by index
                batch_results.sort(key=lambda x: x[0])

                # Add to processed frames
                processed_frame_paths.extend([result[1] for result in batch_results])

        return processed_frame_paths

    def _process_frame_thread(
        self,
        frame_path: str,
        prompt: str,
        negative_prompt: str,
        strength: float,
        guidance_scale: float,
        use_controlnet: bool,
        use_lora: bool,
        index: int,
        results_queue: queue.Queue,
    ):
        """
        Thread function for processing a frame.

        Args:
            frame_path: Path to input frame
            prompt: Text prompt for generation
            negative_prompt: Negative text prompt
            strength: Denoising strength (0-1)
            guidance_scale: Classifier-free guidance scale
            use_controlnet: Whether to use ControlNet
            use_lora: Whether to use LoRA
            index: Frame index
            results_queue: Queue to store results
        """
        try:
            processed_frame_path = self.comfyui_client.process_frame(
                frame_path=frame_path,
                prompt=prompt,
                negative_prompt=negative_prompt,
                strength=strength,
                guidance_scale=guidance_scale,
                use_controlnet=use_controlnet,
                use_lora=use_lora,
            )
            results_queue.put((index, processed_frame_path))
        except Exception as e:
            click.echo(click.style(f"Error processing frame {index}: {e}", fg="red"))
            # Put original frame in queue to maintain sequence
            results_queue.put((index, frame_path))


@click.group(name="model")
def model():
    """Video-to-video generation workflow using ComfyUI and Hunyuan video models."""
    pass


@model.command()
@click.option("--input", "-i", required=True, help="Path to input video file")
@click.option("--output", "-o", required=True, help="Path for output video file")
@click.option("--prompt", "-p", required=True, help="Text prompt for generation")
@click.option("--negative", "-n", default="", help="Negative text prompt")
@click.option("--fps", default=8, help="Frames per second to process", type=int)
@click.option("--strength", "-s", default=0.75, help="Denoising strength (0-1)", type=float)
@click.option("--guidance", "-g", default=7.5, help="Guidance scale", type=float)
@click.option("--batch", "-b", default=1, help="Batch size for parallel processing", type=int)
@click.option("--no-controlnet", is_flag=True, help="Disable ControlNet")
@click.option("--no-lora", is_flag=True, help="Disable LoRA")
@click.option("--no-temporal", is_flag=True, help="Disable temporal consistency")
@click.option("--model", help="Override Hunyuan video model path", type=str)
@click.option("--lora-model", help="Override LoRA model path", type=str)
@click.option("--controlnet-model", help="Override ControlNet model path", type=str)
def generate(
    input,
    output,
    prompt,
    negative,
    fps,
    strength,
    guidance,
    batch,
    no_controlnet,
    no_lora,
    no_temporal,
    model,
    lora_model,
    controlnet_model,
):
    """Generate a video using video-to-video translation with AI models."""
    # Override model paths if specified
    if model:
        CONFIG["hunyuan_video_model"] = model
    if lora_model:
        CONFIG["lora_model"] = lora_model
    if controlnet_model:
        CONFIG["controlnet_model"] = controlnet_model

    # Create generator and process the video
    generator = VideoToVideoGenerator()

    # Display a nice header with a summary of what will be done
    click.echo("\n" + "=" * 80)
    click.echo(click.style("Video-to-Video Generation Workflow", fg="bright_blue", bold=True))
    click.echo("=" * 80)

    # Run the generation process
    output_path = generator.generate(
        input_video=input,
        output_video=output,
        prompt=prompt,
        negative_prompt=negative,
        fps=fps,
        strength=strength,
        guidance_scale=guidance,
        use_controlnet=not no_controlnet,
        use_lora=not no_lora,
        use_temporal_consistency=not no_temporal,
        batch_size=batch,
    )

    # Display completion message
    click.echo("\n" + "=" * 80)
    click.echo(click.style("✓ Generation Complete!", fg="bright_green", bold=True))
    click.echo(f"Output saved to: {click.style(output_path, fg='bright_green', bold=True)}")
    click.echo("=" * 80 + "\n")

    return {"output_path": output_path, "status": "completed"}


@model.command()
@click.option("--config-file", "-c", default="v2v_config.json", help="Path to config file")
@click.option("--output", "-o", default="v2v_config.json", help="Output path for generated config")
def config(config_file, output):
    """Generate or modify a configuration file for the workflow."""
    if os.path.exists(config_file):
        # Load and modify existing config
        click.echo(f"Loading existing config from {config_file}...")
        with open(config_file, "r") as f:
            existing_config = json.load(f)

        # Update the existing config with current CONFIG values
        merged_config = {**CONFIG, **existing_config}

        # Let user modify values interactively
        for key, value in merged_config.items():
            new_value = click.prompt(f"{key}", default=value)
            merged_config[key] = new_value

        # Save updated config
        with open(output, "w") as f:
            json.dump(merged_config, f, indent=2)

        click.echo(click.style(f"Updated config saved to {output}", fg="green"))
    else:
        # Create new config from current settings
        click.echo("Creating new configuration file...")

        # Let user set values interactively
        updated_config = {}
        for key, value in CONFIG.items():
            new_value = click.prompt(f"{key}", default=value)
            updated_config[key] = new_value

        # Save new config
        with open(output, "w") as f:
            json.dump(updated_config, f, indent=2)

        click.echo(click.style(f"Configuration file created at {output}", fg="green"))

    return {"config_file": output, "status": "saved"}


@model.command()
@click.option("--path", "-p", default="./models", help="Path to search for models")
def list_models(path):
    """List available models that can be used with the workflow."""
    models = {"Video Models": [], "VAE Models": [], "LoRA Models": [], "ControlNet Models": []}

    # Function to check if file is potentially a model
    def is_model(file):
        return file.endswith((".safetensors", ".ckpt", ".pt", ".bin"))

    # Walk through directories and collect models
    for root, dirs, files in os.walk(path):
        for file in files:
            if is_model(file):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, ".")

                # Categorize models based on path or name
                if "diffusion_models" in root or "hunyuan_video" in file:
                    models["Video Models"].append(rel_path)
                elif "vae" in root.lower() or "vae" in file.lower():
                    models["VAE Models"].append(rel_path)
                elif "lora" in root.lower() or "lora" in file.lower():
                    models["LoRA Models"].append(rel_path)
                elif "controlnet" in root.lower() or "control" in file.lower():
                    models["ControlNet Models"].append(rel_path)
                # Add to video models by default if we can't categorize
                elif "video" in file.lower():
                    models["Video Models"].append(rel_path)

    # Display results
    click.echo("\n" + "=" * 80)
    click.echo(click.style("Available Models", fg="bright_blue", bold=True))
    click.echo("=" * 80)

    for category, model_list in models.items():
        if model_list:
            click.echo(click.style(f"\n{category}:", fg="green", bold=True))
            for i, model in enumerate(model_list, 1):
                click.echo(f"{i}. {model}")
        else:
            click.echo(click.style(f"\n{category}: None found", fg="yellow"))

    click.echo("\n" + "=" * 80)
    click.echo(
        "Usage: Specify any of these models with the respective options in the generate command"
    )
    click.echo("=" * 80 + "\n")

    return {"models": models, "search_path": path}


@model.command()
def check_comfyui():
    """Check if ComfyUI is running and if required nodes are available."""
    click.echo("Checking ComfyUI connection...")

    try:
        # Try to connect to ComfyUI API
        response = requests.get(f"{CONFIG['comfyui_api']}/object_info")

        if response.status_code == 200:
            click.echo(click.style("✓ ComfyUI is running!", fg="green"))

            # Check for required node types
            node_info = response.json()
            required_nodes = [
                "HunyuanVideoModelLoader",
                "HunyuanVideoVAELoader",
                "HunyuanImagePreprocessor",
                "ControlNetLoader",
                "LoraLoader",
            ]

            missing_nodes = []
            for node in required_nodes:
                if node not in node_info:
                    missing_nodes.append(node)

            if missing_nodes:
                click.echo(click.style("⚠ Warning: Some required nodes are missing:", fg="yellow"))
                for node in missing_nodes:
                    click.echo(f"  - {node}")
                click.echo("\nYou may need to install additional custom nodes for ComfyUI:")
                click.echo("  1. ComfyUI-HunyuanVideoWrapper - For Hunyuan video processing")
                click.echo("  2. ComfyUI-ControlNet - For structure preservation")
            else:
                click.echo(click.style("✓ All required nodes are available!", fg="green"))

            # Check model availability
            click.echo("\nChecking for required models...")
            api_url = f"{CONFIG['comfyui_api']}/model_list"
            response = requests.get(api_url)

            if response.status_code == 200:
                models_info = response.json()

                # Check for hunyuan models
                hunyuan_found = False
                for model_type, models in models_info.items():
                    for model in models:
                        if "hunyuan" in model.lower():
                            hunyuan_found = True
                            click.echo(click.style(f"✓ Found Hunyuan model: {model}", fg="green"))

                if not hunyuan_found:
                    click.echo(
                        click.style("⚠ Warning: No Hunyuan models found in ComfyUI", fg="yellow")
                    )
                    click.echo(
                        "  Make sure you have the Hunyuan video models installed in your ComfyUI setup"
                    )
            else:
                click.echo(click.style("⚠ Could not check model availability", fg="yellow"))

        else:
            click.echo(click.style("✗ Failed to connect to ComfyUI API", fg="red"))
            click.echo(f"  Received status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        click.echo(click.style("✗ Could not connect to ComfyUI", fg="red"))
        click.echo(f"  Error: {e}")
        click.echo("\nPlease ensure that ComfyUI is running at {CONFIG['comfyui_api']}")
        click.echo("You can start ComfyUI with: python main.py --listen 0.0.0.0 --port 8188")

    return {"status": "checked", "comfyui_url": CONFIG["comfyui_api"]}


if __name__ == "__main__":
    model()
# This script is designed to be run as a command line tool
# and should be executed in the context of a larger application.
# It is not intended to be run as a standalone script.
# The script uses the Click library for command line interface
# and the ComfyUI API for video generation.
# The script is structured to allow for easy modification and
# extension, making it suitable for use in a variety of video
# generation workflows.
# The script is designed to be modular, with separate classes
# for handling different aspects of the video generation process.
# The main class, VideoToVideoGenerator, orchestrates the
# entire workflow, from extracting frames to generating the
# final video. The ComfyUIClient class handles communication
# with the ComfyUI API, while the VideoProcessor class
# manages video processing tasks such as frame extraction
# and video encoding.
