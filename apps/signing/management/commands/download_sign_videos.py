"""
Django management command to download sign language videos from S3.
This is useful for development environments to get videos without committing them to Git.
"""

import logging
import os

from django.core.management.base import BaseCommand

from apps.signing.services.video_manager import VideoManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Download sign language videos from S3 for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force download even if videos exist locally",
        )
        parser.add_argument(
            "--sign",
            type=str,
            help="Download only the specified sign",
        )
        parser.add_argument(
            "--source",
            type=str,
            default="s3",
            choices=["s3", "url"],
            help="Source to download from (s3 or url)",
        )
        parser.add_argument(
            "--url",
            type=str,
            help="Base URL for downloading videos (used with --source=url)",
        )

    def handle(self, *args, **options):
        force = options["force"]
        specific_sign = options.get("sign")
        source = options["source"]
        base_url = options.get("url")

        self.stdout.write(self.style.NOTICE("Starting sign language video download..."))

        # Initialize video manager
        video_manager = VideoManager()

        # Validate source configuration
        if not self._validate_source_config(video_manager, source, base_url):
            return

        # Process downloads based on source
        if source == "s3":
            downloaded, skipped, errors = self._process_s3_downloads(
                video_manager, specific_sign, force
            )
        else:  # url source
            downloaded, skipped, errors = self._process_url_downloads(
                video_manager, specific_sign, base_url, force
            )

        # Display summary
        self._display_summary(downloaded, skipped, errors)

    def _validate_source_config(self, video_manager, source, base_url):
        """Validate the selected source configuration."""
        # Check if S3 is configured
        if source == "s3" and not video_manager.use_s3:
            self.stdout.write(
                self.style.ERROR(
                    "S3 storage not configured. Set USE_S3_STORAGE=True and configure AWS credentials."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "Alternatively, use --source=url and provide a --url parameter to download from a URL."
                )
            )
            return False

        # For URL source, ensure base URL is provided
        if source == "url" and not base_url:
            self.stdout.write(
                self.style.ERROR(
                    "URL source selected but no base URL provided. Use --url parameter."
                )
            )
            return False

        return True

    def _process_s3_downloads(self, video_manager, specific_sign, force):
        """Process downloads from S3 source."""
        # List available videos in S3
        video_map = video_manager.list_available_videos()
        if not video_map:
            self.stdout.write(self.style.ERROR("No videos found in S3."))
            return 0, 0, 0

        self.stdout.write(self.style.SUCCESS(f"Found {len(video_map)} videos in S3."))

        # Filter for specific sign if requested
        if specific_sign:
            if specific_sign in video_map:
                video_map = {specific_sign: video_map[specific_sign]}
                self.stdout.write(
                    self.style.SUCCESS(f"Downloading only sign: {specific_sign}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"Sign '{specific_sign}' not found in S3.")
                )
                return 0, 0, 0

        # Download each video
        return self._download_from_s3(video_manager, video_map, force)

    def _download_from_s3(self, video_manager, video_map, force):
        """Download videos from S3 and track progress."""
        downloaded_count = 0
        skipped_count = 0
        error_count = 0

        for sign_name, _video_path in video_map.items():
            try:
                # Check if already exists
                if self._should_skip_existing(video_manager, sign_name, force):
                    skipped_count += 1
                    continue

                # Download from S3
                self.stdout.write(f"Downloading {sign_name} from S3...")
                result = video_manager.download_from_s3(sign_name, force=force)

                if result:
                    self.stdout.write(
                        self.style.SUCCESS(f"Downloaded {sign_name} to {result}")
                    )
                    downloaded_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to download {sign_name}")
                    )
                    error_count += 1

            except Exception as e:
                self._handle_download_error(sign_name, e)
                error_count += 1

        return downloaded_count, skipped_count, error_count

    def _process_url_downloads(self, video_manager, specific_sign, base_url, force):
        """Process downloads from URL source."""
        # If specific sign is provided, download just that one
        if specific_sign:
            sign_list = [specific_sign]
        else:
            # Otherwise, use a default list
            sign_list = ["toki", "pona", "mi", "sina", "olin", "moku", "tenpo"]
            self.stdout.write(
                self.style.WARNING(
                    f"No specific sign provided. Downloading {len(sign_list)} default signs."
                )
            )

        # Download each sign
        return self._download_from_url(video_manager, sign_list, base_url, force)

    def _download_from_url(self, video_manager, sign_list, base_url, force):
        """Download videos from URL and track progress."""
        downloaded_count = 0
        skipped_count = 0
        error_count = 0

        for sign_name in sign_list:
            try:
                # Check if already exists
                if self._should_skip_existing(video_manager, sign_name, force):
                    skipped_count += 1
                    continue

                # Construct URL
                url = f"{base_url.rstrip('/')}/{sign_name}.mp4"

                # Download from URL
                self.stdout.write(f"Downloading {sign_name} from URL: {url}")
                result = video_manager.download_from_url(sign_name, url)

                if result:
                    self.stdout.write(
                        self.style.SUCCESS(f"Downloaded {sign_name} to {result}")
                    )
                    downloaded_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to download {sign_name}")
                    )
                    error_count += 1

            except Exception as e:
                self._handle_download_error(sign_name, e)
                error_count += 1

        return downloaded_count, skipped_count, error_count

    def _should_skip_existing(self, video_manager, sign_name, force):
        """Check if file exists and should be skipped."""
        local_path = video_manager.get_local_video_path(sign_name)
        if os.path.exists(local_path) and not force:
            self.stdout.write(
                self.style.WARNING(f"Skipping {sign_name} - already exists locally")
            )
            return True
        return False

    def _handle_download_error(self, sign_name, error):
        """Handle and log download errors."""
        self.stdout.write(self.style.ERROR(f"Error downloading {sign_name}: {error}"))
        logger.exception(f"Error downloading sign {sign_name}")

    def _display_summary(self, downloaded_count, skipped_count, error_count):
        """Display a summary of the download operation."""
        self.stdout.write("\nDownload completed:")
        self.stdout.write(
            self.style.SUCCESS(f"Successfully downloaded: {downloaded_count}")
        )
        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Skipped (already exists): {skipped_count}")
            )
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))
