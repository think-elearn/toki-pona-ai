import logging
import re

import googleapiclient.discovery
from django.conf import settings
from django.core.cache import cache
from youtube_transcript_api import YouTubeTranscriptApi

from ..models import Transcript, VideoResource

logger = logging.getLogger(__name__)


class YouTubeService:
    """Service for interacting with YouTube API."""

    def __init__(self):
        """Initialize the YouTube service with API credentials."""
        self.api_service_name = "youtube"
        self.api_version = "v3"
        self.youtube_api_key = settings.YOUTUBE_API_KEY
        self.youtube = None
        self._setup_youtube_api()

    def _setup_youtube_api(self):
        """Initialize the YouTube API client."""
        if not self.youtube_api_key:
            logger.error(
                "YouTube API key not found. Please set the YOUTUBE_API_KEY environment variable."
            )
            return

        self.youtube = googleapiclient.discovery.build(
            self.api_service_name, self.api_version, developerKey=self.youtube_api_key
        )

    def search_videos(self, query, limit=5):
        """
        Search YouTube for Toki Pona related videos matching the query.

        Args:
            query (str): Search query related to Toki Pona
            limit (int): Maximum number of results to return

        Returns:
            list: List of video information dictionaries
        """
        # Check for cached results first
        cache_key = f"youtube_search_{query}_{limit}"
        cached_results = cache.get(cache_key)
        if cached_results:
            logger.info(f"Using cached search results for '{query}'")
            return cached_results

        if not self.youtube:
            logger.error("YouTube API client not initialized.")
            return []

        # Add "toki pona" to the query if not already present to focus results
        if "toki pona" not in query.lower():
            query = f"toki pona {query}"

        try:
            # Call the search.list method to retrieve results
            search_response = (
                self.youtube.search()
                .list(
                    q=query,
                    part="snippet",
                    maxResults=limit,
                    type="video",
                    relevanceLanguage="en",  # Prefer English results but will include others
                )
                .execute()
            )

            # Format results
            results = []
            for item in search_response.get("items", []):
                video_id = item["id"]["videoId"]

                # Get additional video details like duration
                video_details = (
                    self.youtube.videos()
                    .list(part="contentDetails,statistics", id=video_id)
                    .execute()
                )

                if video_details["items"]:
                    details = video_details["items"][0]
                    duration_iso = details["contentDetails"][
                        "duration"
                    ]  # ISO 8601 format
                    # Convert ISO 8601 duration to simple minutes:seconds format
                    # For simplicity, only handling typical lesson video durations (< 1 hour)
                    duration = duration_iso.replace("PT", "")
                    minutes = 0
                    seconds = 0
                    if "M" in duration:
                        minutes_part = duration.split("M")[0]
                        minutes = int(minutes_part)
                        duration = duration.split("M")[1]
                    if "S" in duration:
                        seconds_part = duration.split("S")[0]
                        seconds = int(seconds_part)

                    formatted_duration = f"{minutes}:{seconds:02d}"
                    view_count = details["statistics"].get("viewCount", "0")
                else:
                    formatted_duration = "Unknown"
                    view_count = "Unknown"

                # Build the full YouTube URL
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                # Format the result
                results.append(
                    {
                        "id": video_id,
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"]["channelTitle"],
                        "duration": formatted_duration,
                        "description": item["snippet"]["description"],
                        "published_at": item["snippet"]["publishedAt"],
                        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                        "view_count": view_count,
                        "url": video_url,
                    }
                )

            # Cache the results for 1 hour
            cache.set(cache_key, results, 3600)
            return results

        except Exception as e:
            logger.error(f"Error searching YouTube videos: {str(e)}")
            return []

    def get_video_content(self, video_id):
        """
        Get comprehensive details about a video including its transcript.

        Args:
            video_id (str): YouTube video ID

        Returns:
            dict: Video metadata and transcript
        """
        # Check for cached results first
        cache_key = f"youtube_video_{video_id}"
        cached_results = cache.get(cache_key)
        if cached_results:
            logger.info(f"Using cached video content for '{video_id}'")
            return cached_results

        # Check if already in database
        try:
            video_resource = VideoResource.objects.get(youtube_id=video_id)
            # Only return if transcript also exists
            if hasattr(video_resource, "transcript"):
                video_content = {
                    "title": video_resource.title,
                    "channel": video_resource.channel,
                    "description": video_resource.description,
                    "published_at": video_resource.published_at,
                    "view_count": video_resource.view_count,
                    "duration": video_resource.duration,
                    "thumbnail_url": video_resource.thumbnail_url,
                    "has_subtitles": True,
                    "transcript": video_resource.transcript.content,
                    "transcript_language": video_resource.transcript.language,
                    "is_generated_transcript": video_resource.transcript.is_generated,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "video_id": video_id,
                }
                return video_content
        except VideoResource.DoesNotExist:
            # If not in database, fetch from API
            pass

        if not self.youtube:
            logger.error("YouTube API client not initialized.")
            return {"error": "YouTube API client not initialized."}

        try:
            # Get video details
            video_response = (
                self.youtube.videos()
                .list(part="snippet,contentDetails,statistics", id=video_id)
                .execute()
            )

            if not video_response["items"]:
                return {"error": f"Video with ID {video_id} not found"}

            video_data = video_response["items"][0]
            snippet = video_data["snippet"]

            # Build the full YouTube URL
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # Get transcript data
            transcript_data = self.get_video_transcript(video_id)

            # Format the response
            video_content = {
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "description": snippet["description"],
                "published_at": snippet["publishedAt"],
                "view_count": video_data["statistics"].get("viewCount", "0"),
                "like_count": video_data["statistics"].get("likeCount", "0"),
                "comment_count": video_data["statistics"].get("commentCount", "0"),
                "has_subtitles": transcript_data["has_subtitles"],
                "transcript_language": transcript_data["language"],
                "transcript": transcript_data["transcript"],
                "is_generated_transcript": transcript_data["is_generated"],
                "url": video_url,
                "video_id": video_id,
            }

            # Cache the result for 24 hours
            cache.set(cache_key, video_content, 86400)

            # Store in database for future access and processing
            self._store_video_in_database(video_content)

            return video_content

        except Exception as e:
            logger.error(f"Error getting video content: {str(e)}")
            return {"error": f"Error retrieving video content: {str(e)}"}

    def get_video_transcript(self, video_id):
        """
        Get transcript for a specific video.

        Args:
            video_id (str): YouTube video ID

        Returns:
            dict: Transcript data including text and metadata
        """
        try:
            # Attempt to get transcript in any available language
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # First try to find English or Toki Pona transcripts
            preferred_transcript = None
            for transcript in transcript_list:
                if transcript.language_code in [
                    "en",
                    "tok",
                ]:  # 'tok' is language code for Toki Pona
                    preferred_transcript = transcript
                    break

            # If no preferred language found, use the first available transcript
            if not preferred_transcript and transcript_list:
                preferred_transcript = transcript_list[0]

            if preferred_transcript:
                transcript_data = preferred_transcript.fetch()

                # Format the transcript as text
                formatted_transcript = ""
                for entry in transcript_data:
                    formatted_transcript += f"{entry['text']} "

                return {
                    "transcript": formatted_transcript.strip(),
                    "language": preferred_transcript.language_code,
                    "is_generated": preferred_transcript.is_generated,
                    "has_subtitles": True,
                    "source": "youtube_api",
                }
            else:
                # No transcript available - return empty result
                return {
                    "transcript": "",
                    "language": "unknown",
                    "is_generated": False,
                    "has_subtitles": False,
                    "source": "none",
                }

        except Exception as e:
            logger.error(f"Error getting transcript: {str(e)}")
            return {
                "transcript": "",
                "language": "unknown",
                "is_generated": False,
                "has_subtitles": False,
                "source": "error",
                "error": str(e),
            }

    def _store_video_in_database(self, video_content):
        """
        Store video and transcript data in the database.

        Args:
            video_content (dict): Video data from YouTube API
        """
        try:
            # Create or update the video record
            video, created = VideoResource.objects.update_or_create(
                youtube_id=video_content["video_id"],
                defaults={
                    "title": video_content["title"],
                    "channel": video_content["channel"],
                    "description": video_content["description"],
                    "duration": video_content.get("duration", "0:00"),
                    "thumbnail_url": video_content.get("thumbnail", ""),
                    "published_at": video_content["published_at"],
                    "view_count": int(video_content["view_count"])
                    if video_content["view_count"].isdigit()
                    else 0,
                    # Default to beginner difficulty until we analyze content
                    "difficulty": "beginner",
                    "topics": [],  # Empty topics list until we analyze content
                },
            )

            # Only create transcript if it has content
            if video_content.get("transcript"):
                Transcript.objects.update_or_create(
                    video=video,
                    defaults={
                        "content": video_content["transcript"],
                        "language": video_content["transcript_language"],
                        "is_generated": video_content["is_generated_transcript"],
                        "has_embeddings": False,  # Will be processed separately
                        "segments": [],  # Empty until processed
                        "vocabulary": [],  # Empty until processed
                    },
                )

            logger.info(
                f"{'Created' if created else 'Updated'} video record: {video.title}"
            )
        except Exception as e:
            logger.error(f"Error storing video in database: {str(e)}")

    @staticmethod
    def extract_video_id(url):
        """
        Extract YouTube video ID from URL.

        Args:
            url (str): YouTube URL

        Returns:
            str: Video ID or None if not found
        """
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url)
        return match.group(1) if match else None
