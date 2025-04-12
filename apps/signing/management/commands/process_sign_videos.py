"""
Django management command to process sign language videos and extract landmarks.
"""

import logging
import os

from django.core.management.base import BaseCommand

from apps.signing.models import SignReference
from apps.signing.services.sign_comparer import SignComparer
from apps.signing.services.sign_visualizer import SignVisualizer
from apps.signing.services.utils import (
    create_thumbnail_for_sign,
    process_video_to_landmarks,
    save_landmarks_to_model,
)
from apps.signing.services.video_manager import VideoManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process sign language videos and extract landmarks"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force processing even if landmarks exist",
        )
        parser.add_argument(
            "--download",
            action="store_true",
            help="Download videos from S3 if not available locally",
        )
        parser.add_argument(
            "--sign",
            type=str,
            help="Process only the specified sign",
        )

    def handle(self, *args, **options):
        force = options["force"]
        download = options["download"]
        specific_sign = options.get("sign")

        self.stdout.write(
            self.style.NOTICE("Starting sign language video processing...")
        )

        # Initialize services
        sign_comparer = SignComparer()
        sign_visualizer = SignVisualizer()
        video_manager = VideoManager()

        # Get available videos
        video_map = video_manager.list_available_videos()
        if not video_map:
            self.stdout.write(self.style.ERROR("No videos found locally or in S3."))
            return

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(video_map)} videos to process.")
        )

        # Filter for specific sign if requested
        if specific_sign:
            if specific_sign in video_map:
                video_map = {specific_sign: video_map[specific_sign]}
                self.stdout.write(
                    self.style.SUCCESS(f"Processing only sign: {specific_sign}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Sign '{specific_sign}' not found in available videos."
                    )
                )
                return

        # Process videos and get counts
        results = self._process_videos(
            video_map, force, download, sign_comparer, sign_visualizer, video_manager
        )

        # Display summary of processing
        self._display_summary(results)

    def _process_videos(
        self, video_map, force, download, sign_comparer, sign_visualizer, video_manager
    ):
        """Process each video and extract landmarks."""
        results = {
            "processed": 0,
            "skipped": 0,
            "missing": 0,
            "errors": 0,
        }

        for sign_name, video_path in video_map.items():
            try:
                # Get or create sign reference
                sign, created = self._get_or_create_sign(sign_name)

                # Skip if already processed and not forced
                if self._should_skip_processing(sign, force):
                    results["skipped"] += 1
                    continue

                # Ensure video is available locally
                video_path = self._ensure_video_available(
                    sign_name, video_path, download, video_manager
                )
                if not video_path:
                    results["missing"] += 1
                    continue

                # Process and save landmarks
                success, frames = self._process_and_save_landmarks(
                    sign_name, video_path, sign, sign_comparer
                )
                if not success:
                    results["errors"] += 1
                    continue

                # Create thumbnail if needed
                self._create_thumbnail_if_needed(sign, frames, sign_visualizer)

                results["processed"] += 1

            except Exception as e:
                self._log_processing_error(sign_name, e)
                results["errors"] += 1

        return results

    def _get_or_create_sign(self, sign_name):
        """Get or create a sign reference."""
        sign, created = SignReference.objects.get_or_create(
            name=sign_name,
            defaults={
                "meaning": sign_name,  # Default meaning is the same as name
                "difficulty": SignReference.DifficultyLevel.BEGINNER,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created new sign: {sign_name}"))
        else:
            self.stdout.write(f"Found existing sign: {sign_name}")

        return sign, created

    def _should_skip_processing(self, sign, force):
        """Determine if processing should be skipped."""
        if sign.landmarks and not force:
            self.stdout.write(
                self.style.WARNING(f"Skipping {sign.name} - landmarks already exist")
            )
            return True
        return False

    def _ensure_video_available(self, sign_name, video_path, download, video_manager):
        """Ensure the video is available locally."""
        if not os.path.exists(video_path) and os.path.isabs(video_path):
            if download:
                self.stdout.write(f"Downloading video for {sign_name}...")
                video_path = video_manager.get_video_path(sign_name)
                if not video_path:
                    self.stdout.write(
                        self.style.ERROR(f"Could not download video for {sign_name}")
                    )
                    return None
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Video file not found for {sign_name}. Use --download to get it from S3."
                    )
                )
                return None
        return video_path

    def _process_and_save_landmarks(self, sign_name, video_path, sign, sign_comparer):
        """Process video and save extracted landmarks."""
        self.stdout.write(f"Processing video: {video_path}")
        landmarks, frames = process_video_to_landmarks(video_path, sign_comparer)

        if not landmarks or not frames:
            self.stdout.write(
                self.style.ERROR(f"No landmarks or frames found for {sign_name}")
            )
            return False, None

        if save_landmarks_to_model(sign, landmarks):
            self.stdout.write(self.style.SUCCESS(f"Saved landmarks for {sign_name}"))
            return True, frames
        else:
            self.stdout.write(
                self.style.ERROR(f"Failed to save landmarks for {sign_name}")
            )
            return False, None

    def _create_thumbnail_if_needed(self, sign, frames, sign_visualizer):
        """Create a thumbnail for the sign if one doesn't exist."""
        if not sign.thumbnail and frames:
            if create_thumbnail_for_sign(sign, frames[0], sign_visualizer):
                self.stdout.write(
                    self.style.SUCCESS(f"Created thumbnail for {sign.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Failed to create thumbnail for {sign.name}")
                )

    def _log_processing_error(self, sign_name, error):
        """Log an error that occurred during processing."""
        self.stdout.write(self.style.ERROR(f"Error processing {sign_name}: {error}"))
        logger.exception(f"Error processing sign {sign_name}")

    def _display_summary(self, results):
        """Display a summary of processing results."""
        self.stdout.write("\nProcessing completed:")
        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed: {results['processed']}")
        )
        if results["skipped"] > 0:
            self.stdout.write(
                self.style.WARNING(f"Skipped (already processed): {results['skipped']}")
            )
        if results["missing"] > 0:
            self.stdout.write(
                self.style.WARNING(f"Missing videos: {results['missing']}")
            )
        if results["errors"] > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {results['errors']}"))
