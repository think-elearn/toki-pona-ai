# apps/listening/services.py

class TranslationService:
    """Service class for validating translations."""

    def validate_translation(self, phrase_id, user_translation):
        """
        Validate a user's translation against known valid translations.
        Returns feedback dictionary with correctness and explanation.
        """
        from .models import TokiPonaPhrase

        # Basic version: Check against stored translations
        try:
            phrase = TokiPonaPhrase.objects.get(id=phrase_id)
            valid_translations = [t.lower().strip() for t in phrase.translations]
            user_input = user_translation.lower().strip()

            if user_input in valid_translations:
                return {
                    "is_correct": True,
                    "feedback": "Correct! Well done.",
                    "match": user_input,
                }

            # Check for close matches (basic semantic similarity)
            # This could be enhanced with OpenAI API later
            for valid in valid_translations:
                # Simple check: If user's translation is
                # at least 80% similar to a valid one
                if self._similarity_score(user_input, valid) > 0.8:
                    return {
                        "is_correct": True,
                        "feedback": f""""Close enough!
                            A precise translation would be: '{valid}'""",
                        "match": valid,
                    }

            return {
                "is_correct": False,
                "feedback": "Not quite right. Try again.",
                "correct_translations": phrase.translations,
            }

        except TokiPonaPhrase.DoesNotExist:
            return {
                "is_correct": False,
                "feedback": "Error: Phrase not found.",
                "correct_translations": [],
            }

    def _similarity_score(self, str1, str2):
        """
        Calculate a simple similarity score between two strings.
        Returns a value between 0 (completely different) and 1 (identical).
        """
        # This is a very basic implementation -
        # to be replaced with more sophisticated algorithms
        words1 = set(str1.split())
        words2 = set(str2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)


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
