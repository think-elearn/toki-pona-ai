from django.test import TestCase
from apps.listening.models import TokiPonaPhrase
from apps.listening.services import TranslationService, TranscriptService


class TranslationServiceTests(TestCase):
    def setUp(self):
        self.phrase = TokiPonaPhrase.objects.create(
            title="Test Phrase",
            text="mi pona.",
            translations=["I am good.", "I am fine.", "I am well."],
        )
        self.service = TranslationService()

    def test_exact_match_validation(self):
        """Test that exact matches are correctly validated"""
        result = self.service.validate_translation(self.phrase.id, "I am good.")
        self.assertTrue(result["is_correct"])
        self.assertEqual(result["match"], "i am good.")

    def test_case_insensitive_validation(self):
        """Test that case differences don't affect validation"""
        result = self.service.validate_translation(self.phrase.id, "i AM gOOd.")
        self.assertTrue(result["is_correct"])
        self.assertEqual(result["match"], "i am good.")

    def test_whitespace_handling(self):
        """Test that extra whitespace is properly handled"""
        result = self.service.validate_translation(self.phrase.id, "  I am good.  ")
        self.assertTrue(result["is_correct"])
        self.assertEqual(result["match"], "i am good.")

    def test_incorrect_translation(self):
        """Test that incorrect translations are properly identified"""
        result = self.service.validate_translation(self.phrase.id, "I am bad.")
        self.assertFalse(result["is_correct"])
        self.assertEqual(result["correct_translations"], self.phrase.translations)

    def test_nonexistent_phrase(self):
        """Test handling of non-existent phrase IDs"""
        result = self.service.validate_translation(9999, "Test")
        self.assertFalse(result["is_correct"])
        self.assertEqual(result["feedback"], "Error: Phrase not found.")


class TranscriptServiceTests(TestCase):
    def test_parse_empty_transcript(self):
        """Test parsing an empty transcript"""
        result = TranscriptService.parse_transcript("")
        self.assertEqual(result, [])

    def test_parse_transcript(self):
        """Test parsing a valid VTT transcript"""
        sample_vtt = """WEBVTT

00:00:00.000 --> 00:00:05.000
First line of text

00:00:05.000 --> 00:00:10.000
Second line of text
"""
        result = TranscriptService.parse_transcript(sample_vtt)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "First line of text")
        self.assertEqual(result[0]["start_time"], "00:00:00.000")
        self.assertEqual(result[1]["text"], "Second line of text")
        self.assertEqual(result[1]["start_time"], "00:00:05.000")

    def test_parse_transcript_with_extra_lines(self):
        """Test parsing a VTT transcript with extra blank lines and headers"""
        sample_vtt = """WEBVTT

NOTE This is a comment

00:00:00.000 --> 00:00:05.000
First line of text


00:00:05.000 --> 00:00:10.000
Second line of text
"""
        result = TranscriptService.parse_transcript(sample_vtt)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "First line of text")
        self.assertEqual(result[1]["text"], "Second line of text")
