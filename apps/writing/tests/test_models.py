from django.contrib.auth.models import User
from django.test import TestCase

from apps.writing.models import Glyph, GlyphPracticeProgress


class GlyphModelTests(TestCase):
    def setUp(self):
        # Create a test glyph
        self.glyph = Glyph.objects.create(
            name="test",
            meaning="test meaning",
            description="test description",
            difficulty=Glyph.DifficultyLevel.BEGINNER,
            category=Glyph.Category.BASIC,
            example_sentence="mi test",
        )

    def test_str_method(self):
        """Test that the string representation of a glyph is its name"""
        self.assertEqual(str(self.glyph), "test")

    def test_glyph_creation(self):
        """Test that a glyph can be created with proper fields"""
        self.assertEqual(self.glyph.name, "test")
        self.assertEqual(self.glyph.meaning, "test meaning")
        self.assertEqual(self.glyph.description, "test description")
        self.assertEqual(self.glyph.difficulty, Glyph.DifficultyLevel.BEGINNER)
        self.assertEqual(self.glyph.category, Glyph.Category.BASIC)
        self.assertEqual(self.glyph.example_sentence, "mi test")
        self.assertEqual(str(self.glyph), "test")

    def test_glyph_defaults(self):
        """Test that default values are set correctly"""
        glyph = Glyph.objects.create(name="defaults", meaning="testing defaults")
        self.assertEqual(glyph.difficulty, Glyph.DifficultyLevel.BEGINNER)
        self.assertEqual(glyph.category, Glyph.Category.BASIC)
        self.assertEqual(glyph.description, "")
        self.assertEqual(glyph.example_sentence, "")

        # Check that image fields are None since null=True is set
        self.assertIsNone(glyph.image.name)
        self.assertIsNone(glyph.reference_image.name)


class GlyphPracticeProgressTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )

        # Create test glyph
        self.glyph = Glyph.objects.create(name="test", meaning="test meaning")

        # Create progress
        self.progress = GlyphPracticeProgress.objects.create(
            user=self.user, glyph=self.glyph, attempts=10, successful_attempts=7
        )

    def test_str_method(self):
        """Test the string representation of progress shows user and glyph names"""
        expected_str = f"{self.user.username}'s progress on '{self.glyph.name}'"
        self.assertEqual(str(self.progress), expected_str)

    def test_progress_creation(self):
        """Test that progress can be created and tracked"""
        self.assertEqual(self.progress.user, self.user)
        self.assertEqual(self.progress.glyph, self.glyph)
        self.assertEqual(self.progress.attempts, 10)
        self.assertEqual(self.progress.successful_attempts, 7)
        self.assertFalse(self.progress.mastered)

    def test_accuracy_calculation(self):
        """Test the accuracy percentage calculation"""
        # 7 out of 10 = 70%
        self.assertEqual(self.progress.accuracy, 70)

        # Test with no attempts
        empty_progress = GlyphPracticeProgress.objects.create(
            user=self.user,
            glyph=Glyph.objects.create(name="empty", meaning="empty test"),
        )
        self.assertEqual(empty_progress.accuracy, 0)

    def test_mastery_tracking(self):
        """Test that mastery is tracked correctly"""
        # Default is false
        self.assertFalse(self.progress.mastered)

        # Set to true
        self.progress.mastered = True
        self.progress.save()

        # Retrieve and check
        updated_progress = GlyphPracticeProgress.objects.get(id=self.progress.id)
        self.assertTrue(updated_progress.mastered)
