"""
NLP processor for Sanskrit text analysis
Uses rule-based and pre-trained models for demo
"""

import re
import random
import os
import requests
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables explicitly from current directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Handle NLTK import gracefully
try:
    import nltk
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True

    # Download required NLTK data if not already present
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Downloading NLTK punkt tokenizer...")
        nltk.download('punkt', quiet=True)

except ImportError:
    NLTK_AVAILABLE = False
    print("NLTK not installed. Using basic tokenization.")

class SanskritNLP:
    def __init__(self):
        # Mock Sanskrit vocabulary database
        self.vocabulary = {
            "रामः": {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular", "meaning": "Rama"},
            "वनम्": {"pos": "noun", "gender": "neuter", "case": "accusative", "number": "singular", "meaning": "forest"},
            "गच्छति": {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "goes"},
            "गच्छामि": {"pos": "verb", "tense": "present", "person": "first", "number": "singular", "meaning": "I go"},
            "सीता": {"pos": "noun", "gender": "feminine", "case": "nominative", "number": "singular", "meaning": "Sita"},
            "अस्ति": {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "is"},
            "सुतः": {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular", "meaning": "son"},
            "पुस्तकम्": {"pos": "noun", "gender": "neuter", "case": "nominative", "number": "singular", "meaning": "book"},
            "पठति": {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "reads"},
            "खादति": {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "eats"},
            "फलम्": {"pos": "noun", "gender": "neuter", "case": "nominative", "number": "singular", "meaning": "fruit"},
            "बालकः": {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular", "meaning": "boy"},
            "अहं": {"pos": "pronoun", "case": "nominative", "number": "singular", "meaning": "I"},
            "अहम्": {"pos": "pronoun", "case": "nominative", "number": "singular", "meaning": "I"},
            "विद्यालय": {"pos": "noun", "gender": "masculine", "case": "base", "number": "singular", "meaning": "school"},
            "विद्यालयम्": {"pos": "noun", "gender": "masculine", "case": "accusative", "number": "singular", "meaning": "school (to)"},
            "विद्यालयं": {"pos": "noun", "gender": "masculine", "case": "accusative", "number": "singular", "meaning": "school (to)"},
            # Additional words for multi-error test sentence
            "सः": {"pos": "pronoun", "case": "nominative", "number": "singular", "meaning": "he"},
            "तस्य": {"pos": "pronoun", "case": "genitive", "number": "singular", "meaning": "his"},
            "तम्": {"pos": "pronoun", "case": "accusative", "number": "singular", "meaning": "him"},
            "ग्राम": {"pos": "noun", "gender": "masculine", "case": "base", "number": "singular", "meaning": "village"},
            "ग्रामम्": {"pos": "noun", "gender": "masculine", "case": "accusative", "number": "singular", "meaning": "village (to)"},
            "ग्रामं": {"pos": "noun", "gender": "masculine", "case": "accusative", "number": "singular", "meaning": "village (to)"},
        }

        # Grammar rules (simplified for demo)
        self.grammar_rules = [
            {"rule": "Subject-verb agreement", "pattern": r".*ः.*ति$", "description": "Nominative noun should agree with verb"},
            {"rule": "Case endings", "pattern": r".*म्$", "description": "Accusative case ending for objects"},
        ]

        # AI Configuration - Support both xAI (Grok) and Groq (gsk_...)
        self.api_key = os.getenv("XAI_API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.ai_provider: str = "Local"
        self.ai_model: str = "None"

        if self.api_key and isinstance(self.api_key, str):
            api_key_str: str = self.api_key
            if api_key_str.startswith("gsk_"):
                # It's a Groq key
                self.ai_provider = "Groq"
                self.base_url = "https://api.groq.com/openai/v1" # Force Groq URL
                self.ai_model = "openai/gpt-oss-120b"
                print(f"SanskritNLP: Detected Groq API Key. Setting provider to {self.ai_provider}...")
            else:
                # Assume it's an xAI (Grok) key
                self.ai_provider = "Grok"
                self.base_url = self.base_url or "https://api.x.ai/v1"
                self.ai_model = "grok-beta"
                print(f"SanskritNLP: Detected {self.ai_provider} API Key.")

            print("SanskritNLP: AI Engine initialized")
        else:
            print("SanskritNLP: AI Engine key NOT found. Check your .env file.")

    def tokenize(self, text: str) -> List[str]:
        """Tokenize Sanskrit text"""
        # Simple tokenization by splitting on spaces and punctuation
        if NLTK_AVAILABLE:
            try:
                # Basic cleanup for common punctuations often used as sentence ends
                clean_text = text.replace('|', '।').replace('.', '।')
                return word_tokenize(clean_text)
            except:
                pass

        # Fallback tokenization
        words = re.findall(r'[\u0900-\u097F]+|[.,!?;।|]', text)
        return [w for w in words if w.strip()]

    # -----------------------------------------------------------------------
    # NEW HELPER: build a structured issue dict
    # -----------------------------------------------------------------------
    def _make_issue(self, rule: str, error_type: str, description: str) -> Dict[str, Any]:
        """
        Create a structured issue dict that downstream skill-mapping can consume.

        Every issue produced by the local NLP or normalised from the AI response
        must have these three keys:
          - rule         : short human-readable label (for UI display)
          - error_type   : canonical snake_case type for SkillMapper
          - description  : longer explanation shown to the learner
        """
        return {
            "rule": rule,
            "error_type": error_type,
            "description": description,
        }

    def analyze_text(self, text: str, mode: str = "Basic", use_ai: bool = False) -> Dict[str, Any]:
        """Analyze Sanskrit text for grammar and syntax"""

        # If AI mode is requested and we have a key
        if use_ai and self.api_key:
            return self.analyze_with_grok(text)

        # Normalize common markers before tokenizing
        normalized_text = text.replace('|', '।').replace('.', '।')
        words = self.tokenize(normalized_text)
        sanskrit_words = [w for w in words if re.match(r'[\u0900-\u097F]+', w)]

        # Breakdown with robust lookup
        breakdown = []
        for word in sanskrit_words:
            # Clean word for lookup (remove trailing punctuation)
            clean_word = re.sub(r'[.,!?;।|]$', '', word).strip()

            if clean_word in self.vocabulary:
                breakdown.append({
                    "word": word,
                    "pos": self.vocabulary[clean_word]["pos"],
                    "meaning": self.vocabulary[clean_word]["meaning"],
                    "analysis": self.vocabulary[clean_word]
                })
            else:
                # Try one more time with common variations (e.g. anusvara vs ma-kara)
                alt_word = clean_word
                if clean_word.endswith('ं'):
                    alt_word = clean_word[:-1] + 'म्'
                elif clean_word.endswith('म्'):
                    alt_word = clean_word[:-1] + 'ं'

                if alt_word in self.vocabulary:
                    breakdown.append({
                        "word": word,
                        "pos": self.vocabulary[alt_word]["pos"],
                        "meaning": self.vocabulary[alt_word]["meaning"],
                        "analysis": self.vocabulary[alt_word]
                    })
                else:
                    breakdown.append({
                        "word": word,
                        "pos": "unknown",
                        "meaning": "unknown",
                        "analysis": {"note": "Word not in local dictionary"}
                    })

        # -----------------------------------------------------------------------
        # Generate structured issues
        # -----------------------------------------------------------------------
        issues = []
        if len(sanskrit_words) < 1:
             return {"error": "Please enter some text to analyze"}

        # Build a clean word set (trailing punctuation stripped) used by all
        # detection rules. sanskrit_words keeps the raw tokens for breakdown display.
        clean_words = {re.sub(r'[.,!?;।|]+$', '', w).strip() for w in sanskrit_words}

        # ------------------------------------------------------------------
        # Rule 1 — Punctuation: sentence must end with Purna Virama (।)
        # ------------------------------------------------------------------
        if (not text.strip().endswith('।') and
                not text.strip().endswith('|') and
                not text.strip().endswith('.')):
            issues.append(self._make_issue(
                rule="Purna Virama",
                error_type="punctuation_error",
                description="Sentence must end with a Purna Virama (।). Every complete Sanskrit sentence requires this stop mark.",
            ))

        # ------------------------------------------------------------------
        # Rule 2 — Vibhakti (case): destination noun must be in Accusative
        #
        # Detects: अहं विद्यालय गच्छामि।
        #   → विद्यालय is in base form, should be विद्यालयं (dvitiya vibhakti)
        # ------------------------------------------------------------------
        has_aham = any(w in ["अहं", "अहम्"] for w in clean_words)
        has_gachhami = any(w == "गच्छामि" for w in clean_words)
        has_gachhati = any(w == "गच्छति" for w in clean_words)

        # Destination nouns known to the local lexicon that can be in base form (error)
        _destination_nouns_base = {"विद्यालय", "ग्राम"}
        # Correct accusative forms of those nouns
        _destination_nouns_correct = {"विद्यालयम्", "विद्यालयं", "ग्रामम्", "ग्रामं"}

        motion_verb_present = has_gachhami or has_gachhati
        destination_base = _destination_nouns_base.intersection(clean_words)
        destination_correct = _destination_nouns_correct.intersection(clean_words)

        if motion_verb_present and destination_base and not destination_correct:
            bad_noun = next(iter(destination_base))
            issues.append(self._make_issue(
                rule="Case selection (Dvitiya Vibhakti)",
                error_type="vibhakti_error",
                description=(
                    f"Destination noun '{bad_noun}' must be in Accusative Case (Dvitīyā Vibhakti). "
                    f"When a motion verb like गच्छति/गच्छामि is used, the destination requires the "
                    f"second case ending (e.g., विद्यालयं, ग्रामम्)."
                ),
            ))

        # ------------------------------------------------------------------
        # Rule 3 — Pronoun error
        #
        # Detects: सः + गच्छामि (third-person pronoun with first-person verb)
        # The pronoun सः (he) pairs with गच्छति, not गच्छामि (I go).
        # ------------------------------------------------------------------
        has_sah = any(w == "सः" for w in clean_words)

        if has_sah and has_gachhami:
            issues.append(self._make_issue(
                rule="Pronoun-verb agreement",
                error_type="pronoun_error",
                description=(
                    "Pronoun सः (he/she/it, 3rd person) does not agree with verb गच्छामि "
                    "(1st person singular). Use गच्छति for 3rd person, or change the pronoun "
                    "to अहम् for 1st person."
                ),
            ))

        # ------------------------------------------------------------------
        # Score: deduct 15 per issue, floor at 0
        # ------------------------------------------------------------------
        score = max(0, 100 - len(issues) * 15)

        # Generate live translation via Hugging Face Serverless
        translation = self.translate_sanskrit_to_english(normalized_text)

        # Initialize default correction variables
        corrected_sentence = text
        correction_summary = "No errors found."

        if score < 100:
            # Smart mock correction for common student mistakes
            if ("विद्यालय" in corrected_sentence and motion_verb_present and
                    "विद्यालयं" not in corrected_sentence and "विद्यालयम्" not in corrected_sentence):
                corrected_sentence = corrected_sentence.replace("विद्यालय", "विद्यालयं")

                # Basic fallback for remaining bare nouns.
                # Skip destination nouns that were just corrected to accusative above.
                _already_fixed = _destination_nouns_base | _destination_nouns_correct
                for w in sanskrit_words:
                    clean_w = re.sub(r'[.,!?;।|]+$', '', w).strip()
                    if clean_w in _already_fixed:
                        continue
                    if (self.vocabulary.get(clean_w, {}).get("pos") == "noun" and
                            not clean_w.endswith("ः") and not clean_w.endswith("म्") and not clean_w.endswith("ं")):
                        corrected_sentence = re.sub(re.escape(clean_w), clean_w + "ः", corrected_sentence)

                correction_summary = "Corrected sentence structure and morphological markers."

        # Final cleanup for punctuation
        corrected_sentence = corrected_sentence.strip()
        if corrected_sentence.endswith('.'):
            corrected_sentence = corrected_sentence[:-1] + "।"
        elif not corrected_sentence.endswith('।') and not corrected_sentence.endswith('|'):
            corrected_sentence += " ।"

        return {
            "score": score,
            "issues": issues,          # ← Now a list of structured dicts, NOT plain strings
            "corrected_sentence": corrected_sentence,
            "correction_summary": correction_summary,
            "breakdown": breakdown,
            "word_count": len(sanskrit_words),
            "translation": translation,
            "analysis_mode": mode,
            "ai_verified": False
        }

    def analyze_with_grok(self, text: str) -> Dict[str, Any]:
        """Use xAI's Grok API for professional morphological and syntactic analysis"""
        print(f"SanskritNLP: Starting AI Analysis for: {text} using {self.ai_provider}")
        try:
            prompt = f"""
            Task: You are an expert Sanskrit grammarian and Pāṇini scholar. Analyze the following Sanskrit sentence: "{text}"

            Instructions:
            1. Separate the sentence into individual Sanskrit words (tokens).
            2. For each word, provide morphological analysis (Vibhakti, Gender, Number, Tense, Person, Root).
            3. CRITICAL: Check for missing case endings (e.g., "विद्यालय" when it should be "विद्यालयं" for objects) and subject-verb agreement (e.g., "छात्राः पठति" to "छात्राः पठन्ति").
               - Purna Virama (।): Every Sanskrit sentence MUST end with '।'. If it is missing, or if they used a period (.), add an issue with error_type "punctuation_error".
            4. Provide an overall grammar score (0-100). Prioritize morphological and syntactic correctness.
            5. EXTREMELY CRITICAL FOR "corrected_sentence":
               - You MUST NOT add any new words.
               - You MUST NOT remove any user words.
               - ONLY fix case endings (vibhakti) and verb endings (lakāra/puruṣa/vacana).
               - Ensure the sentence ends with '।'. If the user used '.' or nothing, replace/add '।'.

               Examples of EXACT corrections:
               User: "अहं विद्यालय गच्छामि" -> Correct: "अहं विद्यालयं गच्छामि" (ONLY adding Anusvara)
               User: "छात्राः पुस्तकम् पठति" -> Correct: "छात्राः पुस्तकम् पठन्ति" (ONLY fixing verb number to match plural subject)
               BAD Correction (DO NOT DO THIS): "छात्राः पुस्तकम् पठति" -> "छात्राः पुस्तकं पठितुम् इच्छन्ति" (Added new words! Forbidden!)

            6. "correction_summary" must explain the specific grammatical rule (e.g., "Karka-Siddhanta: Destination requires Dvitiya Vibhakti").

            CRITICAL for issues: Each issue MUST be a JSON object with these exact fields:
              - "rule": short label (e.g. "Case selection")
              - "error_type": one of: vibhakti_error, sandhi_error, tense_error, mood_error,
                              pronoun_error, pronoun_case_error, upasarga_error, voice_error,
                              samasa_error, verb_agreement_error, noun_gender_error,
                              punctuation_error, agreement_error, unknown_error
              - "description": detailed explanation for the learner

            Output Format: STRICT JSON object with these fields:
            {{
                "score": int,
                "issues": [
                    {{
                        "rule": "Case selection",
                        "error_type": "vibhakti_error",
                        "description": "Destination noun requires Dvitīyā Vibhakti..."
                    }}
                ],
                "corrected_sentence": "Properly corrected version in Devanagari",
                "correction_summary": "Linguistic reason for changes",
                "breakdown": [
                    {{
                        "word": "original",
                        "pos": "POS Tag",
                        "meaning": "English",
                        "analysis": {{ "root": "...", "vibhakti": "...", "vachana": "...", "linga": "...", "details": "..." }}
                    }}
                ],
                "translation": "Full English translation"
            }}
            """

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.ai_model,
                "messages": [
                    {"role": "system", "content": "You are an expert Sanskrit grammarian. Pay close attention to morphology, syntax, and punctuation. Every complete Sanskrit sentence must end with a Purna Virama (।). Always return issues as a JSON array of objects with rule, error_type, and description fields."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }

            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                print(f"{self.ai_provider} API ERROR: {response.status_code} - {response.text}")
                return self.analyze_text(text, mode=f"API Error {response.status_code}", use_ai=False)

            result = response.json()
            analysis_text = result['choices'][0]['message']['content']

            # Robust JSON extraction (in case AI wraps it in markdown blocks)
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                analysis_json = json.loads(json_match.group(0))
            else:
                analysis_json = json.loads(analysis_text)

            analysis_json["analysis_mode"] = f"{self.ai_provider} AI Engine"
            analysis_json["ai_verified"] = True

            # Final cleanup: Ensure corrected_sentence properly ends with Purna Virama (।)
            if "corrected_sentence" in analysis_json:
                corrected = analysis_json["corrected_sentence"].strip()
                if corrected.endswith('.'):
                    corrected = corrected[:-1] + "।"
                elif not corrected.endswith('।') and not corrected.endswith('|'):
                    corrected += " ।"
                analysis_json["corrected_sentence"] = corrected

            # Recalculate word count for AI results
            words = self.tokenize(text)
            s_words = [w for w in words if re.match(r'[\u0900-\u097F]+', w)]
            analysis_json["word_count"] = len(s_words)

            # ---------------------------------------------------------------
            # Normalize AI-returned issues to structured dicts
            # Each issue must have: rule, error_type, description
            # ---------------------------------------------------------------
            raw_issues = analysis_json.get("issues", [])
            normalized_issues = self._normalize_ai_issues(raw_issues)
            analysis_json["issues"] = normalized_issues

            print(f"SanskritNLP: Successfully analyzed with {self.ai_provider} AI")
            return analysis_json

        except Exception as e:
            print(f"CRITICAL API Error: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fallback to local analysis if AI fails
            return self.analyze_text(text, mode="AI Fallback", use_ai=False)

    def _normalize_ai_issues(self, raw_issues: list) -> List[Dict[str, Any]]:
        """
        Ensure every issue returned by the AI is a structured dict with
        rule, error_type, and description.

        The AI sometimes returns plain strings (old format) or dicts without
        an error_type. This method normalises both formats so the downstream
        skill-mapping layer always receives a consistent structure.
        """
        # Import here to avoid circular imports at module level
        from modules.skill_mapper import SkillMapper
        _mapper = SkillMapper()

        normalized = []
        for item in raw_issues:
            if isinstance(item, str):
                # Old-format plain string — wrap it and try to infer error_type
                normalized_type = _mapper.normalize_error_type(item)
                normalized.append(self._make_issue(
                    rule=item,
                    error_type=normalized_type,
                    description=item,
                ))
            elif isinstance(item, dict):
                # Structured dict — normalise the error_type field
                raw_type = item.get("error_type") or item.get("type") or ""
                normalized_type = _mapper.normalize_error_type(raw_type)
                normalized.append({
                    "rule": item.get("rule") or item.get("type") or normalized_type,
                    "error_type": normalized_type,
                    "description": item.get("description") or item.get("message") or str(item),
                })
            else:
                # Unexpected format — treat as unknown
                normalized.append(self._make_issue(
                    rule="Unknown",
                    error_type="unknown_error",
                    description=str(item),
                ))
        return normalized

    def mock_translate(self, text: str) -> str:
        """Mock translation for demo"""
        translations = {
            "रामः वनं गच्छति।": "Rama goes to the forest.",
            "सीता अस्ति।": "Sita is.",
            "सुतः पुस्तकं पठति।": "The son reads a book.",
            "बालकः फलं खादति।": "The boy eats fruit.",
        }

        if text in translations:
            return translations[text]

        # Generic translation
        words = text.split()
        if words:
            return f"Translation of '{words[0]}...' would appear here"

        return "Translation unavailable"

    def translate_sanskrit_to_english(self, text: str) -> str:
        """Translate Sanskrit text to English using Hugging Face Serverless API"""
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            return "Translation unavailable: HUGGINGFACE_TOKEN not found."

        # The 2026 updated HF Serverless Router URL
        API_URL = "https://router.huggingface.co/hf-inference/models/ai4bharat/indictrans2-indic-en-dist-200M"

        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }

        # IndicTrans2 uses specific language tags: 'san_Deva' for Sanskrit, 'eng_Latn' for English
        payload = {
            "inputs": text,
            "parameters": {
                "src_lang": "san_Deva",
                "tgt_lang": "eng_Latn"
            }
        }

        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=15)

            if response.status_code == 200:
                result = response.json()
                # Extract the translated string from the HF response format
                if isinstance(result, list) and len(result) > 0 and 'translation_text' in result[0]:
                    return result[0]['translation_text']
                elif 'generated_text' in result: # Fallback format
                    return result['generated_text']
            elif response.status_code == 503:
                # 503 means the model is "cold" and loading into memory.
                estimated_time = response.json().get('estimated_time', 20)
                return f"Model is warming up. Please try again in {int(estimated_time)} seconds."
            else:
                print(f"HF Translation Error: {response.status_code} - {response.text}")
                return "Translation failed."

        except Exception as e:
            print(f"HF Request Exception: {str(e)}")
            return "Translation request timed out."

        return "Translation unavailable"

    def check_grammar(self, text: str) -> List[Dict]:
        """Check grammar against rules"""
        issues = []

        for rule in self.grammar_rules:
            if not re.search(rule["pattern"], text.replace(" ", "")):
                issues.append({
                    "rule": rule["rule"],
                    "description": rule["description"],
                    "suggestion": f"Check {rule['rule'].lower()}"
                })

        return issues

    def get_word_details(self, word: str) -> Dict:
        """Get detailed analysis of a Sanskrit word"""
        if word in self.vocabulary:
            return self.vocabulary[word]

        # Generate mock analysis for unknown words
        return {
            "pos": random.choice(["noun", "verb", "adjective"]),
            "meaning": "Meaning not in database",
            "note": "This word needs to be added to vocabulary"
        }