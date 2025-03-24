"""
Service for recognizing Sitelen Pona characters.
"""

import base64
import logging
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

# For when we have MediaPipe installed
try:
    import mediapipe as mp
    from mediapipe.tasks import python  # noqa: F401
    from mediapipe.tasks.python import vision  # noqa: F401

    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None

from apps.writing.services.ml_storage import model_storage

logger = logging.getLogger(__name__)


class CharacterRecognitionService:
    """
    Service for recognizing Sitelen Pona characters using MediaPipe and MobileNet.
    """

    def __init__(self):
        """Initialize the character recognition service."""
        self.embedder = None
        self.templates = {}
        self.embeddings = {}
        self.initialized = False

    def initialize(self):
        """Initialize the character recognition service with the MobileNet model."""
        if self.initialized:
            return

        if not MEDIAPIPE_AVAILABLE:
            logger.error(
                "MediaPipe is not available. Character recognition will not work."
            )
            return

        try:
            # Get the model path from storage service
            model_path = model_storage.get_mobilenet_model_path()

            # Initialize MediaPipe Image Embedder with proper options
            base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
            options = mp.tasks.vision.ImageEmbedderOptions(
                base_options=base_options,
                l2_normalize=True,  # Enable L2 normalization for better similarity comparison
            )
            self.embedder = mp.tasks.vision.ImageEmbedder.create_from_options(options)

            # Load templates
            self.load_templates()

            self.initialized = True
            logger.info("Character recognition service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing character recognition service: {str(e)}")
            raise

    def load_templates(self):
        """
        Load and process template images.

        In production, templates will be stored in S3.
        In development, they will be stored locally.
        """
        # TODO: Implement template loading from S3 or local storage
        # For now, we'll use a dummy implementation
        self.templates = {
            "a": {"original": None, "processed": None},
        }
        self.embeddings = {
            "a": np.ones(1024),  # Dummy embedding vector
        }
        logger.info(f"Loaded {len(self.templates)} template images")

    def preprocess_image(self, image) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Preprocess image for MediaPipe."""
        debug_steps = {}
        debug_steps["original"] = image.copy()

        # Convert to RGB if needed
        if len(image.shape) == 3:
            if image.shape[2] == 4:  # RGBA
                # For canvas input, properly handle alpha channel
                mask = image[:, :, 3] > 0  # Get mask of non-transparent pixels
                rgb = image[:, :, :3]
                # Set transparent pixels to white (background color)
                white_bg = np.ones_like(rgb) * 255
                rgb = np.where(mask[:, :, None], rgb, white_bg)
                image = rgb
                debug_steps["alpha_handled"] = image.copy()
            elif image.shape[2] == 3:  # BGR
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                debug_steps["rgb_converted"] = image.copy()
        elif len(image.shape) == 2:  # Grayscale
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            debug_steps["rgb_converted"] = image.copy()

        # Resize while maintaining aspect ratio
        target_size = (224, 224)  # MobileNet default size
        h, w = image.shape[:2]
        aspect = w / h

        if aspect > 1:
            new_w = target_size[0]
            new_h = int(new_w / aspect)
        else:
            new_h = target_size[1]
            new_w = int(new_h * aspect)

        resized = cv2.resize(image, (new_w, new_h))
        debug_steps["aspect_preserved"] = resized.copy()

        # Create white canvas of target size (since we're dealing with black text)
        canvas = np.ones((target_size[1], target_size[0], 3), dtype=np.uint8) * 255

        # Center the image on the canvas
        y_offset = (target_size[1] - new_h) // 2
        x_offset = (target_size[0] - new_w) // 2
        canvas[y_offset : y_offset + new_h, x_offset : x_offset + new_w] = resized
        debug_steps["centered"] = canvas.copy()

        # Normalize pixel values to [0, 1]
        processed = canvas.astype(np.float32) / 255.0

        return processed, debug_steps

    def get_embedding(self, image) -> Tuple[List[float], Dict[str, np.ndarray]]:
        """Get embedding from preprocessed image using MediaPipe."""
        try:
            # Ensure we're initialized
            if not self.initialized:
                self.initialize()

            # Preprocess and create MediaPipe image
            processed, debug_steps = self.preprocess_image(image)

            # Convert to uint8 for MediaPipe (it doesn't like float input)
            mp_input = (processed * 255).astype(np.uint8)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=mp_input)

            # Get embedding
            embedding_result = self.embedder.embed(mp_image)

            # Return the embedding values (already a numpy array) and debug image
            return embedding_result.embeddings[0].embedding, debug_steps
        except Exception as e:
            logger.error(f"Failed to get embedding: {str(e)}")
            raise

    def cosine_similarity(self, a, b) -> float:
        """Compute cosine similarity between two embeddings."""
        # Embeddings should already be L2 normalized due to embedder options
        # Just compute dot product for cosine similarity
        similarity = float(np.dot(a, b))

        # Return raw similarity score
        return similarity

    def recognize(self, drawn_image, threshold=0.7) -> Tuple[Optional[str], float]:
        """Recognize drawn character by comparing embeddings."""
        # Get embedding for drawn image
        input_embedding, debug_steps = self.get_embedding(drawn_image)

        if input_embedding is None:
            return None, 0

        # Compare with all templates
        best_match = None
        best_score = 0
        all_scores = {}

        for char_name, template_embedding in self.embeddings.items():
            # Calculate similarity score
            score = self.cosine_similarity(input_embedding, template_embedding)
            all_scores[char_name] = float(score)

            if score > best_score:
                best_score = score
                best_match = char_name

        # Store scores for debug display
        self.all_scores = all_scores

        if best_score >= threshold:
            return best_match, best_score
        return None, best_score

    def recognize_base64(
        self, base64_image: str, threshold=0.7
    ) -> Tuple[Optional[str], float, Dict[str, Any]]:
        """
        Recognize a character from a base64-encoded image.

        Args:
            base64_image: Base64-encoded image string
            threshold: Recognition threshold

        Returns:
            tuple: (character_name, confidence_score, debug_info)
        """
        try:
            # Decode base64 image
            if "," in base64_image:
                base64_image = base64_image.split(",")[1]

            image_data = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_data))

            # Convert to numpy array
            image_np = np.array(image)

            # Recognize
            character, score = self.recognize(image_np, threshold)

            debug_info = {
                "scores": getattr(self, "all_scores", {}),
                "threshold": threshold,
                "input_shape": image_np.shape,
            }

            return character, score, debug_info

        except Exception as e:
            logger.error(f"Error recognizing base64 image: {str(e)}")
            return None, 0, {"error": str(e)}


# Create a singleton instance
character_recognition = CharacterRecognitionService()
