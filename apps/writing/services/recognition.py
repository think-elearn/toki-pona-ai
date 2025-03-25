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
from apps.writing.services.templates import template_service

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
        self.all_scores = {}

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
        """
        try:
            # Get all templates from the template service
            template_list = template_service.get_template_list()

            if not template_list:
                logger.warning(
                    "No templates found. Character recognition will not work properly."
                )
                return

            logger.info(f"Loading {len(template_list)} templates")

            # Process each template
            for template_name in template_list:
                # Get template image
                original_image = template_service.get_template_image(template_name)

                if original_image is None:
                    logger.warning(f"Template image for '{template_name}' not found")
                    continue

                # Convert PIL Image to numpy array if needed
                if isinstance(original_image, Image.Image):
                    original_image = np.array(original_image)

                # Preprocess the image
                processed, _ = self.preprocess_image(original_image)

                # Store images for display
                self.templates[template_name] = {
                    "original": original_image,
                    "processed": (processed * 255).astype(np.uint8),
                }

                # Convert to uint8 for MediaPipe (it doesn't like float input)
                mp_input = (processed * 255).astype(np.uint8)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=mp_input)

                # Get and store embedding values
                embedding_result = self.embedder.embed(mp_image)
                self.embeddings[template_name] = embedding_result.embeddings[
                    0
                ].embedding

            logger.info(
                f"Successfully loaded {len(self.embeddings)} template embeddings"
            )

        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}")

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

        # Find bounding box of non-white pixels to crop the drawing tightly
        # This helps with alignment and improves recognition
        if image.shape[2] == 3:  # RGB image
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Threshold to find ink pixels
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        debug_steps["thresholded"] = thresh.copy()

        # Find contours
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # If no contours are found, use the entire image
        if not contours:
            x, y, w, h = 0, 0, image.shape[1], image.shape[0]
        else:
            # Combine all contours to get the bounding box of the drawing
            all_points = np.concatenate(list(contours))
            x, y, w, h = cv2.boundingRect(all_points)

            # Add some padding around the bounding box
            padding = int(min(w, h) * 0.1)  # 10% padding
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(image.shape[1] - x, w + padding * 2)
            h = min(image.shape[0] - y, h + padding * 2)

        # Crop the image to the bounding box
        cropped = image[y : y + h, x : x + w]
        debug_steps["cropped"] = cropped.copy()

        # Resize while maintaining aspect ratio
        target_size = (224, 224)  # MobileNet default size

        # Slightly adjust the aspect ratio to better match typical glyph proportions
        # This helps when user drawings have different proportions from templates
        cropped_h, cropped_w = cropped.shape[:2]
        aspect = cropped_w / cropped_h

        # Ensure the aspect ratio is not too extreme
        aspect = min(max(aspect, 0.7), 1.3)

        if aspect > 1:
            new_w = target_size[0]
            new_h = int(new_w / aspect)
        else:
            new_h = target_size[1]
            new_w = int(new_h * aspect)

        # Use INTER_AREA for downscaling or INTER_CUBIC for upscaling
        if cropped_w > new_w or cropped_h > new_h:
            interpolation = cv2.INTER_AREA
        else:
            interpolation = cv2.INTER_CUBIC

        resized = cv2.resize(cropped, (new_w, new_h), interpolation=interpolation)
        debug_steps["aspect_preserved"] = resized.copy()

        # Create white canvas of target size
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
