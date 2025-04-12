# Luka Pona Sign Language Learning Module

This Django app provides an interactive learning experience for Luka Pona, the sign language version of Toki Pona. It uses MediaPipe Hands for real-time hand tracking and sign recognition.

## Features

- Practice Toki Pona signs with real-time feedback
- Compare your signing attempt with reference videos
- Track your progress and mastery of signs
- Categories for beginner, intermediate, and advanced signs

## Video Management Strategy

Since video files are large and shouldn't be committed to Git, we use a flexible approach:

### For Development

1. **Download on demand**: Videos are not included in the repository but can be downloaded when needed.
2. **Local caching**: Once downloaded, videos are stored locally for faster access.
3. **Landmark extraction**: Hand landmarks are extracted and stored in the database, keeping the important data in Git while leaving the raw videos out.

### For Production

1. **S3 Storage**: Videos are stored in an S3-compatible storage service.
2. **Automatic fallback**: If a video isn't available locally, it's downloaded from S3.

## Setup Instructions

### Prerequisites

- Python 3.11+
- Django 4.2+
- OpenCV
- MediaPipe
- AWS S3 credentials (for production)

### Installation

1. Install Python dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

2. Run migrations:

   ```bash
   python manage.py migrate
   ```

3. Download sign videos for development:

   ```bash
   python manage.py download_sign_videos
   ```

4. Process videos to extract landmarks:

   ```bash
   python manage.py process_sign_videos
   ```

### Video Management Commands

#### Download Videos

```bash
# Download all sign videos from S3
python manage.py download_sign_videos

# Force redownload, overwriting existing files
python manage.py download_sign_videos --force

# Download a specific sign
python manage.py download_sign_videos --sign toki

# Download from a custom URL source
python manage.py download_sign_videos --source url --url https://your-video-host.com/signs/
```

#### Process Videos

```bash
# Process all available videos to extract landmarks
python manage.py process_sign_videos

# Process even if landmarks already exist
python manage.py process_sign_videos --force

# Download missing videos from S3 then process
python manage.py process_sign_videos --download

# Process a specific sign
python manage.py process_sign_videos --sign toki
```

## Using Custom Video Sources

If you don't have S3 access, you can use any web server to host your sign videos:

1. Upload your MP4 files to a web server
2. Use the download command with the URL source option:

   ```bash
   python manage.py download_sign_videos --source url --url https://your-server.com/videos/
   ```

This will download the videos from your server to your local development environment.

## Development Workflow

1. **Initial setup**: Download and process the sign videos
2. **Development**: Work on the code, using the locally cached videos
3. **Git commits**: The videos are excluded by .gitignore, keeping your repository lean
4. **Deployment**: In production, videos are served from S3

## Troubleshooting

- **Videos not found**: Run `download_sign_videos` to get them from S3 or another source
- **Landmark extraction fails**: Check the video quality and format, and ensure MediaPipe is properly installed
- **S3 access issues**: Verify your AWS credentials and bucket permissions
