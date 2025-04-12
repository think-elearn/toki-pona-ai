"""
Service for visualizing sign language gestures and comparisons.
Adapted from the standalone implementation in signing-app/sign_visualizer.py.
"""

import base64
import io
import logging
import tempfile

import cv2
import imageio
import mediapipe as mp
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class SignVisualizer:
    """
    Service for visualizing sign language gestures and landmarks.
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

    def process_video_frames(self, video_path):
        """Extract frames from a video file."""
        frames = []

        # Open the video file
        video = cv2.VideoCapture(video_path)

        if not video.isOpened():
            logger.error(f"Error opening video file: {video_path}")
            return frames

        # Read frames
        while True:
            success, frame = video.read()
            if not success:
                break

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)

        video.release()
        return frames

    def process_gif_frames(self, gif_path):
        """Extract frames from a GIF file."""
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

            return frames
        except Exception as e:
            logger.error(f"Error processing GIF: {e}")
            return []

    def process_base64_frames(self, base64_frames):
        """Convert base64 encoded frames to RGB frames."""
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

        return frames

    def extract_frames_with_landmarks(self, frames):
        """Process frames and extract landmarks."""
        processed_frames = []
        landmarks_data = []

        for frame in frames:
            # Create a copy for drawing on
            annotated_frame = frame.copy()

            # Process with MediaPipe
            results = self.hands.process(frame)

            # Store landmark data
            frame_landmarks = []
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Extract landmarks
                    hand_points = []
                    for landmark in hand_landmarks.landmark:
                        hand_points.append([landmark.x, landmark.y, landmark.z])
                    frame_landmarks.append(hand_points)

                    # Draw landmarks on the frame
                    self.mp_drawing.draw_landmarks(
                        annotated_frame,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing_styles.get_default_hand_landmarks_style(),
                        self.mp_drawing_styles.get_default_hand_connections_style(),
                    )

            processed_frames.append(annotated_frame)
            landmarks_data.append(frame_landmarks)

        return processed_frames, landmarks_data

    def create_comparison_frames(self, template_frames, learner_frames):
        """Create side-by-side comparison frames of template and learner."""
        # Process frames to add landmarks
        template_processed, _ = self.extract_frames_with_landmarks(template_frames)
        learner_processed, _ = self.extract_frames_with_landmarks(learner_frames)

        # Create a side-by-side comparison
        max_frames = max(len(template_processed), len(learner_processed))
        comparison_frames = []

        # Choose a common size for both frames
        target_height = 400
        target_width = 600

        for i in range(max_frames):
            # Get template frame or create blank
            if i < len(template_processed):
                template_frame = template_processed[i]
                # Resize template frame
                template_frame = cv2.resize(
                    template_frame,
                    (target_width, target_height),
                    interpolation=cv2.INTER_AREA,
                )
            else:
                template_frame = np.zeros(
                    (target_height, target_width, 3), dtype=np.uint8
                )

            # Get learner frame or create blank
            if i < len(learner_processed):
                learner_frame = learner_processed[i]
                # Resize learner frame
                learner_frame = cv2.resize(
                    learner_frame,
                    (target_width, target_height),
                    interpolation=cv2.INTER_AREA,
                )
            else:
                learner_frame = np.zeros(
                    (target_height, target_width, 3), dtype=np.uint8
                )

            # Create side-by-side frame
            comparison_frame = np.zeros(
                (target_height, target_width * 2, 3), dtype=np.uint8
            )
            comparison_frame[:, :target_width] = template_frame
            comparison_frame[:, target_width:] = learner_frame

            # Add labels
            cv2.putText(
                comparison_frame,
                "Template",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                comparison_frame,
                "Learner",
                (target_width + 10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )

            # Add frame number
            cv2.putText(
                comparison_frame,
                f"Frame: {i + 1}/{max_frames}",
                (10, target_height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            comparison_frames.append(comparison_frame)

        return comparison_frames

    def save_comparison_gif(self, comparison_frames, output_path=None):
        """Save comparison frames as a GIF."""
        if not output_path:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
                output_path = tmp.name

        # Save as GIF
        imageio.mimsave(output_path, comparison_frames, duration=0.1)

        return output_path

    def generate_thumbnail(self, frame, size=(200, 200)):
        """Generate a thumbnail image from a frame."""
        # Create a copy with landmarks
        annotated_frame, _ = self.extract_frames_with_landmarks([frame])
        annotated_frame = annotated_frame[0]

        # Resize to thumbnail
        thumbnail = cv2.resize(annotated_frame, size, interpolation=cv2.INTER_AREA)

        # Convert to PIL Image for Django compatibility
        pil_image = Image.fromarray(thumbnail)

        # Save to bytes buffer
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer

    def create_landmark_heatmap(self, template_landmarks, learner_landmarks):
        """Create a heatmap image showing landmark differences."""
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        from matplotlib.figure import Figure

        # Ensure both sequences have the same length
        min_frames = min(len(template_landmarks), len(learner_landmarks))

        # Calculate differences for each frame
        differences = []

        for i in range(min_frames):
            # Skip frames without detected hands
            if not template_landmarks[i] or not learner_landmarks[i]:
                continue

            # Get first hand from each frame
            template_hand = np.array(template_landmarks[i][0])
            learner_hand = np.array(learner_landmarks[i][0])

            # Calculate Euclidean distance for each landmark
            frame_diffs = []
            for j in range(21):  # 21 landmarks per hand
                dist = np.linalg.norm(template_hand[j] - learner_hand[j])
                frame_diffs.append(dist)

            differences.append(frame_diffs)

        if not differences:
            logger.warning("Not enough data to create heatmap")
            return None

        # Convert to numpy array
        diff_array = np.array(differences)

        # Create heatmap
        fig = Figure(figsize=(12, 8))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        im = ax.imshow(diff_array, aspect="auto", cmap="viridis")
        fig.colorbar(im, ax=ax, label="Euclidean Distance")
        ax.set_xlabel("Landmark Index")
        ax.set_ylabel("Frame")
        ax.set_title("Landmark Difference Heatmap")

        # Add landmark names
        landmark_names = [
            "WRIST",
            "THUMB_CMC",
            "THUMB_MCP",
            "THUMB_IP",
            "THUMB_TIP",
            "INDEX_MCP",
            "INDEX_PIP",
            "INDEX_DIP",
            "INDEX_TIP",
            "MIDDLE_MCP",
            "MIDDLE_PIP",
            "MIDDLE_DIP",
            "MIDDLE_TIP",
            "RING_MCP",
            "RING_PIP",
            "RING_DIP",
            "RING_TIP",
            "PINKY_MCP",
            "PINKY_PIP",
            "PINKY_DIP",
            "PINKY_TIP",
        ]
        ax.set_xticks(range(21))
        ax.set_xticklabels(landmark_names, rotation=90)

        fig.tight_layout()

        # Save to buffer
        buffer = io.BytesIO()
        canvas.print_png(buffer)
        buffer.seek(0)

        return buffer
