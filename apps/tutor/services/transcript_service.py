class TranscriptService:
    """Service class for processing and displaying transcripts."""

    @staticmethod
    def parse_transcript(transcript_text):
        """
        Parse a VTT-formatted transcript into a list of timed text segments.
        """
        if not transcript_text:
            return []

        segments = []
        lines = transcript_text.strip().split("\n")

        i = 0
        while i < len(lines):
            # Skip empty lines and WEBVTT header
            if not lines[i] or lines[i] == "WEBVTT":
                i += 1
                continue

            # Look for timestamp lines (00:00:00.000 --> 00:00:00.000)
            if " --> " in lines[i]:
                timestamp = lines[i]

                # Next line should be the text
                if i + 1 < len(lines):
                    text = lines[i + 1]

                    # Parse start time for sorting/display
                    start_time = timestamp.split(" --> ")[0].strip()

                    segments.append(
                        {"timestamp": timestamp, "text": text, "start_time": start_time}
                    )

                    i += 2
                else:
                    i += 1
            else:
                i += 1

        return segments
