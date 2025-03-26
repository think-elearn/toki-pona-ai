import io
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from apps.writing.models import Glyph
from apps.writing.services import svg_service


class Command(BaseCommand):
    help = "Load Sitelen Pona glyphs from static SVG files"

    def handle(self, *args, **kwargs):
        """Handle the command execution."""
        self.stdout.write(
            self.style.NOTICE("Loading Sitelen Pona glyphs from static files...")
        )

        self._cleanup_legacy_directories()
        self._ensure_media_directories()

        # Source SVG directory in static files
        svg_source_dir = self._get_svg_source_dir()
        if not svg_source_dir:
            return

        # Find all SVG files
        svg_files = self._find_svg_files(svg_source_dir)
        if not svg_files:
            return

        # Process the SVG files
        self._process_svg_files(svg_files)

    def _cleanup_legacy_directories(self):
        """Clean up old incorrect model directory if it exists."""
        root_ml_models = Path(settings.BASE_DIR) / "ml_models"
        if root_ml_models.exists() and root_ml_models.is_dir():
            import shutil

            self.stdout.write(
                self.style.WARNING(
                    "Removing legacy ml_models directory at project root..."
                )
            )
            try:
                shutil.rmtree(root_ml_models)
                self.stdout.write(
                    self.style.SUCCESS(f"Removed legacy directory: {root_ml_models}")
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error removing directory: {e}"))

    def _ensure_media_directories(self):
        """Ensure necessary media directories exist."""
        # Check media directories
        media_dir = Path(settings.MEDIA_ROOT)
        if not media_dir.exists():
            media_dir.mkdir(parents=True)

        glyphs_dir = media_dir / "glyphs"
        if not glyphs_dir.exists():
            glyphs_dir.mkdir(parents=True)

        reference_dir = glyphs_dir / "reference"
        if not reference_dir.exists():
            reference_dir.mkdir(parents=True)

    def _get_svg_source_dir(self):
        """Get the source directory for SVG files."""
        svg_source_dir = Path(
            settings.ML_MODELS_STORAGE.get(
                "STATIC_GLYPHS_DIR",
                Path(settings.BASE_DIR) / "static" / "images" / "glyphs",
            )
        )

        # Check if source directory exists
        if not svg_source_dir.exists():
            self.stderr.write(
                self.style.ERROR(
                    f"Source SVG directory '{svg_source_dir}' does not exist"
                )
            )
            return None

        return svg_source_dir

    def _find_svg_files(self, svg_source_dir):
        """Find all SVG files in the source directory."""
        svg_files = list(svg_source_dir.glob("*.svg"))
        if not svg_files:
            self.stderr.write(
                self.style.WARNING(f"No SVG files found in '{svg_source_dir}'")
            )
            return None

        self.stdout.write(self.style.NOTICE(f"Found {len(svg_files)} SVG files"))
        return svg_files

    def _get_glyph_metadata(self):
        """Define metadata for glyphs."""
        # Define glyph metadata - expand as needed
        glyph_metadata = {
            "toki": {
                "meaning": "language, communicate, talk, speech",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "toki pona li pona",
                "description": "The glyph for 'toki' resembles a mouth talking.",
            },
            "pona": {
                "meaning": "good, simple, positive",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "sina pona",
                "description": "The glyph for 'pona' has a simple design representing goodness.",
            },
            "mi": {
                "meaning": "I, me, we, us",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi moku",
                "description": "The glyph for 'mi' points to oneself.",
            },
            "sina": {
                "meaning": "you",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "sina suli",
                "description": "The glyph for 'sina' points outward to someone else.",
            },
            "jan": {
                "meaning": "person, human, somebody",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "jan li pona",
                "description": "The glyph for 'jan' resembles a simple figure of a person.",
            },
            # Add more metadata for other glyphs as needed
        }

        # Default metadata for unknown glyphs
        default_metadata = {
            "meaning": "Toki Pona word",
            "difficulty": "intermediate",
            "category": "basic",
            "example_sentence": "",
            "description": "Sitelen Pona glyph",
        }

        return glyph_metadata, default_metadata

    def _process_svg_files(self, svg_files):
        """Process each SVG file."""
        glyph_metadata, default_metadata = self._get_glyph_metadata()

        # Import and process each SVG file
        processed_count = 0
        for svg_file in svg_files:
            glyph_name = svg_file.stem  # Get filename without extension

            # Check if glyph already exists
            existing_glyph = Glyph.objects.filter(name=glyph_name).first()
            if existing_glyph:
                self.stdout.write(
                    self.style.WARNING(
                        f"Glyph '{glyph_name}' already exists, updating..."
                    )
                )

            try:
                processed = self._process_single_svg(
                    svg_file,
                    glyph_name,
                    glyph_metadata,
                    default_metadata,
                    existing_glyph,
                )
                if processed:
                    processed_count += 1

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Error processing {glyph_name}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {processed_count} out of {len(svg_files)} glyphs"
            )
        )

    def _process_single_svg(
        self,
        svg_file,
        glyph_name,
        glyph_metadata,
        default_metadata,
        existing_glyph=None,
    ):
        """Process a single SVG file."""
        # Read the SVG content
        with open(svg_file, "r", encoding="utf-8") as f:
            svg_content = f.read()

        # Upload SVG to service (makes it available via API/templates)
        svg_service.upload_svg(glyph_name, svg_content)

        # Convert SVG to PNG for ML model
        png_data = cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            output_width=100,
            output_height=100,
            background_color="white",
        )

        # Convert to numpy array for processing
        image = Image.open(io.BytesIO(png_data))
        image_array = np.array(image)

        # Convert to grayscale if needed
        if len(image_array.shape) == 3:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)

        # Threshold to create binary image
        _, binary = cv2.threshold(image_array, 127, 255, cv2.THRESH_BINARY)

        # Save processed image to bytes
        processed_img = cv2.imencode(".png", binary)[1].tobytes()

        # Also create a template image for character recognition
        from apps.writing.services.templates import template_service

        template_service.upload_template(glyph_name, processed_img)

        # Get glyph metadata (or use defaults)
        metadata = glyph_metadata.get(glyph_name, default_metadata)

        # Update or create the glyph record
        glyph = existing_glyph or Glyph(name=glyph_name)
        glyph.meaning = metadata["meaning"]
        glyph.difficulty = metadata["difficulty"]
        glyph.category = metadata["category"]
        glyph.example_sentence = metadata["example_sentence"]
        glyph.description = metadata["description"]

        # Save to create or update the model instance
        glyph.save()

        # Add both the processed PNG and original SVG to the model
        # For ML recognition
        glyph.image.save(f"{glyph_name}.png", ContentFile(processed_img), save=False)

        # For reference display
        glyph.reference_image.save(
            f"{glyph_name}.svg",
            ContentFile(svg_content.encode("utf-8")),
            save=True,
        )

        self.stdout.write(self.style.SUCCESS(f"Processed glyph: {glyph_name}"))
        return True
