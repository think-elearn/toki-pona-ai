"""
Service for comparing sign language gestures using MediaPipe Hands.
Adapted from the standalone implementation in signing-app/main.py.
"""

import base64
import logging
import tempfile

import cv2
import imageio
import mediapipe as mp
import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

logger = logging.getLogger(__name__)


class SignComparer:
    """
    Service for comparing sign language gestures using MediaPipe Hands.
    """

    def __init__(self):
        """Initialize MediaPipe Hands and other components."""
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def extract_landmarks_from_frames(self, frames):
        """Extract hand landmarks from a sequence of frames."""
        all_frame_landmarks = []

        for frame in frames:
            # Process with MediaPipe
            results = self.hands.process(frame)

            # Extract landmarks (if hands detected)
            frame_landmarks = []
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Get all landmarks as (x, y, z) coordinates
                    hand_points = []
                    for landmark in hand_landmarks.landmark:
                        hand_points.append([landmark.x, landmark.y, landmark.z])
                    frame_landmarks.append(hand_points)

            all_frame_landmarks.append(frame_landmarks)

        return all_frame_landmarks

    def extract_landmarks_from_video(self, video_path):
        """Extract hand landmarks from a video file."""
        # Open the video file
        video = cv2.VideoCapture(video_path)

        if not video.isOpened():
            logger.error(f"Error opening video file: {video_path}")
            return []

        frames = []
        # Read frames
        while True:
            success, frame = video.read()
            if not success:
                break

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)

        video.release()

        # Extract landmarks from frames
        return self.extract_landmarks_from_frames(frames)

    def extract_landmarks_from_gif(self, gif_path):
        """Extract hand landmarks from each frame of a GIF."""
        try:
            # Read GIF
            gif = imageio.mimread(gif_path)

            # Process each frame
            frames = []
            for frame in gif:
                # Convert RGBA to RGB if needed
                if frame.shape[2] == 4:
                    frame = frame[:, :, :3]
                frames.append(frame)

            # Extract landmarks from frames
            return self.extract_landmarks_from_frames(frames)
        except Exception as e:
            logger.error(f"Error processing GIF: {e}")
            return []

    def extract_landmarks_from_base64_frames(self, base64_frames):
        """Extract hand landmarks from base64 encoded frames."""
        frames = []

        for base64_str in base64_frames:
            try:
                # Decode base64 string to image
                image_data = base64.b64decode(
                    base64_str.split(",")[1] if "," in base64_str else base64_str
                )
                image = np.frombuffer(image_data, dtype=np.uint8)
                frame = cv2.imdecode(image, cv2.IMREAD_COLOR)

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
            except Exception as e:
                logger.error(f"Error decoding base64 frame: {e}")

        # Extract landmarks from frames
        return self.extract_landmarks_from_frames(frames)

    def normalize_landmarks(self, landmarks):
        """Normalize landmarks to make them invariant to hand size and position."""
        if not landmarks:
            return []

        normalized = []
        for frame_landmarks in landmarks:
            if not frame_landmarks:
                normalized.append([])
                continue

            frame_normalized = []
            for hand in frame_landmarks:
                # Use wrist as origin
                wrist = np.array(hand[0])

                # Find the scale factor (distance from wrist to middle finger MCP)
                scale = np.linalg.norm(np.array(hand[9]) - wrist)
                if scale == 0:  # Avoid division by zero
                    scale = 1

                # Normalize each point
                normalized_hand = [(np.array(point) - wrist) / scale for point in hand]
                frame_normalized.append(normalized_hand)

            normalized.append(frame_normalized)

        return normalized

    def create_sequence_for_comparison(self, normalized_landmarks):
        """Create a sequence for DTW comparison from normalized landmarks."""
        sequence = []

        for frame in normalized_landmarks:
            if frame:  # If hands detected
                # Just use first hand for simplicity
                sequence.append(np.array(frame[0]).flatten())
            else:
                # If no hands detected, use zeros
                sequence.append(np.zeros(21 * 3))  # 21 landmarks, 3 coordinates each

        return sequence

    def compare_signs(self, template_landmarks, learner_landmarks):
        """Compare template sign landmarks with learner's attempt."""
        # Normalize landmarks
        template_norm = self.normalize_landmarks(template_landmarks)
        learner_norm = self.normalize_landmarks(learner_landmarks)

        # Create sequences for comparison
        template_seq = self.create_sequence_for_comparison(template_norm)
        learner_seq = self.create_sequence_for_comparison(learner_norm)

        # Check if we have valid sequences
        if not template_seq or not learner_seq:
            return {"similarity_score": 0, "frame_scores": [], "dtw_path": []}

        # Calculate similarity using Dynamic Time Warping
        distance, path = fastdtw(template_seq, learner_seq, dist=euclidean)

        # Calculate overall similarity score (0-100)
        # Note: 21 landmarks with 3 coordinates each would be the maximum possible distance
        # if all landmarks are completely off, but we use a simpler scaling approach here
        similarity_score = max(0, 100 - (distance / len(path) * 10))

        # Identify problematic frames
        frame_scores = []
        for template_idx, learner_idx in path:
            if template_idx < len(template_seq) and learner_idx < len(learner_seq):
                frame_dist = euclidean(
                    template_seq[template_idx], learner_seq[learner_idx]
                )
                frame_scores.append(max(0, 100 - (frame_dist * 10)))

        return {
            "similarity_score": similarity_score,
            "frame_scores": frame_scores,
            "dtw_path": path,
        }

    def generate_feedback(self, comparison_results):
        """Generate feedback based on comparison results."""
        score = comparison_results["similarity_score"]
        frame_scores = comparison_results["frame_scores"]

        feedback = {
            "overall_score": score,
            "rating": self._get_rating(score),
            "weak_points": self._identify_weak_points(frame_scores),
        }

        return feedback

    def _get_rating(self, score):
        """Convert numerical score to rating."""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Very Good"
        elif score >= 70:
            return "Good"
        elif score >= 60:
            return "Fair"
        else:
            return "Needs Practice"

    def _identify_weak_points(self, frame_scores):
        """Identify portions of the sign that need improvement."""
        if not frame_scores:
            return "Unable to identify specific areas for improvement."

        # Find segments with low scores
        weak_segments = []
        current_segment = {"start": 0, "scores": []}

        for i, score in enumerate(frame_scores):
            current_segment["scores"].append(score)

            # Check if we should end this segment
            if (
                i == len(frame_scores) - 1  # Last frame
                or (i > 0 and abs(score - frame_scores[i - 1]) > 15)
            ):  # Score change
                # Calculate average score for this segment
                avg_score = sum(current_segment["scores"]) / len(
                    current_segment["scores"]
                )

                # If score is low, add to weak segments
                if avg_score < 70:
                    current_segment["end"] = i
                    current_segment["avg_score"] = avg_score
                    weak_segments.append(current_segment)

                # Start a new segment
                current_segment = {"start": i + 1, "scores": []}

        # Generate feedback
        if not weak_segments:
            return "Your sign matches the template well throughout the entire motion."

        feedback = []
        for segment in weak_segments:
            segment_desc = f"Segment {segment['start']} to {segment['end']} needs improvement (score: {segment['avg_score']:.1f})"
            feedback.append(segment_desc)

        return feedback

    def save_frames_as_gif(self, frames, output_path=None):
        """Save frames as a GIF file."""
        if not output_path:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
                output_path = tmp.name

        # Save as GIF
        imageio.mimsave(output_path, frames, duration=0.1)

        return output_path

    def create_comparison_gif(self, template_frames, learner_frames, output_path=None):
        """Create a side-by-side comparison GIF of template and learner."""
        from .sign_visualizer import SignVisualizer

        visualizer = SignVisualizer()
        comparison_frames = visualizer.create_comparison_frames(
            template_frames, learner_frames
        )

        return self.save_frames_as_gif(comparison_frames, output_path)
