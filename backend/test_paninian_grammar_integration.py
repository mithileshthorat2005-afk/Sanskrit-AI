import unittest
import json
from unittest.mock import Mock, patch

from modules.nlp_processor import SanskritNLP


class StubPaninianAnalyzer:
    forms = {
        "गच्छामि": {"person": "uttama", "number": "eka"},
        "गच्छसि": {"person": "maDyama", "number": "eka"},
        "गच्छतः": {"person": "praTama", "number": "dvi"},
    }

    def analyze_verb(self, form):
        morphology = self.forms.get(form)
        if morphology is None:
            return {"is_verb": False}
        return {
            "is_verb": True,
            "root": "गम्",
            "root_slp1": "gam",
            "person": morphology["person"],
            "number": morphology["number"],
            "rules_applied": ["3.4.78"],
            "derivation": [{"sutra_num": "3.4.78"}],
        }


class PaninianGrammarIntegrationTests(unittest.TestCase):
    def setUp(self):
        with patch("modules.nlp_processor.PANINIAN_AVAILABLE", False), patch(
            "modules.nlp_processor.NOUN_AVAILABLE", False
        ):
            self.nlp = SanskritNLP()
        self.nlp.paninian = StubPaninianAnalyzer()
        self.nlp.translate_sanskrit_to_english = lambda text: "translation"

    def test_paninian_person_mismatch_is_reported_in_grammar_result(self):
        result = self.nlp.analyze_text("अहं गच्छसि।")

        self.assertEqual(result["breakdown"][1]["source"], "dictionary")
        self.assertIn(
            "Subject is first person but verb is second person — check subject-verb agreement.",
            result["issues"],
        )
        self.assertEqual(result["breakdown"][1]["analysis"]["purusha"], "maDyama")

    def test_matching_paninian_person_and_number_passes_agreement_check(self):
        result = self.nlp.analyze_text("अहं गच्छामि।")

        self.assertEqual(result["issues"], [])
        self.assertEqual(result["breakdown"][1]["analysis"]["purusha"], "uttama")
        self.assertEqual(result["breakdown"][1]["analysis"]["vacana"], "eka")

    def test_paninian_only_verb_uses_person_and_number_for_checks(self):
        breakdown = [
            {
                "word": "अहं",
                "pos": "pronoun",
                "analysis": {
                    "case": "nominative",
                    "number": "singular",
                    "person": "first",
                },
            },
            self.nlp._classify_word("गच्छतः"),
        ]

        issues = self.nlp._run_checks("अहं गच्छतः।", breakdown)

        self.assertEqual(breakdown[1]["source"], "paninian")
        self.assertTrue(any("Subject is singular but verb is dual" in issue for issue in issues))
        self.assertTrue(any("Subject is first person but verb is third person" in issue for issue in issues))

    @patch("modules.nlp_processor.requests.post")
    def test_ai_result_includes_fields_required_by_grammar_endpoint(self, post):
        post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "score": 95,
                                    "issues": ["Example issue"],
                                    "corrected_sentence": "रामः वनं गच्छति।",
                                    "breakdown": [
                                        {
                                            "word": "रामः",
                                            "pos": "noun",
                                            "source": "dictionary",
                                        }
                                    ],
                                    "translation": "Rama goes to the forest.",
                                }
                            )
                        }
                    }
                ]
            },
        )
        self.nlp.api_key = "test-key"
        self.nlp.base_url = "https://example.invalid"
        self.nlp.ai_model = "test-model"
        self.nlp.ai_provider = "Groq"

        with patch("builtins.print"):
            result = self.nlp.analyze_with_grok("रामः वनं गच्छति।")

        self.assertEqual(result["analysis_mode"], "Groq AI")
        self.assertTrue(result["ai_verified"])
        self.assertEqual(result["word_count"], 3)
        self.assertEqual(result["source_counts"], {"dictionary": 1})


if __name__ == "__main__":
    unittest.main()
