from .models import TokiPonaPhrase


class TranslationService:
    def validate_translation(self, phrase_id, user_translation):
        """
        Validate a user's translation against known valid translations
        Returns feedback dictionary with correctness and explanation
        """
        # Basic version: Check against stored translations
        phrase = TokiPonaPhrase.objects.get(id=phrase_id)
        valid_translations = [t.lower() for t in phrase.translations]
        user_input = user_translation.lower().strip()

        if user_input in valid_translations:
            return {
                "is_correct": True,
                "feedback": "Correct! Well done.",
                "match": user_input,
            }

        # Enhanced version: Use OpenAI to check semantic similarity
        # [OpenAI API integration code here]

        return {
            "is_correct": False,
            "feedback": "Not quite right. Try again.",
            "correct_translations": phrase.translations,
        }
