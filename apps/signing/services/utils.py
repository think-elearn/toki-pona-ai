"""
Utility functions for the signing app.
"""

import base64
import json
import logging
import os
import tempfile
from io import BytesIO

import cv2
import imageio
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image

logger = logging.getLogger(__name__)


def process_video_to_landmarks(video_path, sign_comparer):
    """
    Process a video file to extract hand landmarks.

    Args:
        video_path: Path to the video file
        sign_comparer: An instance of SignComparer

    Returns:
        A tuple of (landmarks, frames)
    """
    try:
        # Extract landmarks from the video
        landmarks = sign_comparer.extract_landmarks_from_video(video_path)

        # Get frames from the video for visualization
        video = cv2.VideoCapture(video_path)
        frames = []

        if not video.isOpened():
            logger.error(f"Error opening video file: {video_path}")
            return [], []

        while True:
            success, frame = video.read()
            if not success:
                break

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)

        video.release()

        return landmarks, frames

    except Exception as e:
        logger.exception(f"Error processing video {video_path}: {e}")
        return [], []


def save_landmarks_to_model(sign_reference, landmarks):
    """
    Save landmarks to a SignReference model.

    Args:
        sign_reference: SignReference model instance
        landmarks: List of landmarks

    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert landmarks to JSON
        sign_reference.landmarks = json.dumps(landmarks)
        sign_reference.save(update_fields=["landmarks"])
        return True
    except Exception as e:
        logger.exception(f"Error saving landmarks: {e}")
        return False


def load_landmarks_from_model(sign_reference):
    """
    Load landmarks from a SignReference model.

    Args:
        sign_reference: SignReference model instance

    Returns:
        List of landmarks or None if not found
    """
    try:
        if sign_reference.landmarks:
            return json.loads(sign_reference.landmarks)
        return None
    except Exception as e:
        logger.exception(f"Error loading landmarks: {e}")
        return None


def create_thumbnail_for_sign(sign_reference, frame, sign_visualizer):
    """
    Create a thumbnail for a sign and save it to the model.

    Args:
        sign_reference: SignReference model instance
        frame: RGB frame to use for the thumbnail
        sign_visualizer: An instance of SignVisualizer

    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate thumbnail
        thumbnail_buffer = sign_visualizer.generate_thumbnail(frame)

        # Generate filename
        filename = f"{slugify(sign_reference.name)}_thumbnail.png"

        # Save to model
        sign_reference.thumbnail.save(
            filename, ContentFile(thumbnail_buffer.getvalue()), save=True
        )
        return True
    except Exception as e:
        logger.exception(f"Error creating thumbnail: {e}")
        return False


def create_gif_from_frames(frames, output_path=None):
    """
    Create a GIF from a list of frames.

    Args:
        frames: List of RGB frames
        output_path: Optional path to save the GIF

    Returns:
        Path to the created GIF file
    """
    try:
        if not output_path:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
                output_path = tmp.name

        # Save frames as GIF
        imageio.mimsave(output_path, frames, duration=0.1)
        return output_path
    except Exception as e:
        logger.exception(f"Error creating GIF: {e}")
        return None


def convert_base64_to_image(base64_str):
    """
    Convert a base64 string to a PIL Image.

    Args:
        base64_str: Base64 encoded image string

    Returns:
        PIL Image object or None if failed
    """
    try:
        # Remove data URL prefix if present
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        # Decode base64
        image_data = base64.b64decode(base64_str)
        image = Image.open(BytesIO(image_data))
        return image
    except Exception as e:
        logger.exception(f"Error converting base64 to image: {e}")
        return None


def convert_frames_to_base64(frames):
    """
    Convert a list of frames to base64 encoded strings.

    Args:
        frames: List of RGB frames

    Returns:
        List of base64 encoded strings
    """
    base64_frames = []

    for frame in frames:
        try:
            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Encode frame as JPEG
            _, buffer = cv2.imencode(".jpg", frame_bgr)

            # Convert to base64
            base64_str = base64.b64encode(buffer).decode("utf-8")
            base64_frames.append(f"data:image/jpeg;base64,{base64_str}")
        except Exception as e:
            logger.exception(f"Error converting frame to base64: {e}")

    return base64_frames


def scan_video_directory():
    """
    Scan the static videos directory for Toki Pona sign videos.

    Returns:
        Dictionary mapping sign names to video paths
    """
    video_dir = os.path.join(settings.STATICFILES_DIRS[0], "videos", "lukapona", "mp4")
    videos = {}

    try:
        if os.path.exists(video_dir):
            for filename in os.listdir(video_dir):
                if filename.endswith(".mp4"):
                    # Extract sign name from filename (remove extension)
                    sign_name = os.path.splitext(filename)[0]
                    videos[sign_name] = os.path.join(video_dir, filename)
        else:
            logger.warning(f"Video directory not found: {video_dir}")
    except Exception as e:
        logger.exception(f"Error scanning video directory: {e}")

    return videos
