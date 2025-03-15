from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from apps.listening.models import TokiPonaPhrase


class CommandsTestCase(TestCase):
    def test_load_sample_phrases(self):
        """Test that the load_sample_phrases command works properly"""
        # Record output
        out = StringIO()

        # Call command
        call_command("load_sample_phrases", stdout=out)

        # Check that phrases were created
        self.assertTrue(TokiPonaPhrase.objects.exists())

        # Check output
        output = out.getvalue()
        self.assertIn("Loading sample Toki Pona phrases", output)
        self.assertIn("Successfully loaded sample phrases", output)

        # Check that at least a few phrases were created
        self.assertGreaterEqual(TokiPonaPhrase.objects.count(), 3)
