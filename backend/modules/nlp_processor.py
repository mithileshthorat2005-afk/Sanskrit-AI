"""
NLP processor for Sanskrit text analysis

Pipeline:
  1. Dictionary lookup (highest priority)
     - Verb entries are enriched with Paninian morphology
  2. Noun analyzer (declension rules)
  3. Paninian verb analyzer (Prakriya)
  4. AI fallback (only when use_ai=True)

Output contract:
  { score, issues, corrected_sentence, breakdown, word_count,
    translation, analysis_mode, ai_verified, source_counts }
"""

import re
import random
import os
import requests
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# ── NLTK (optional) ─────────────────────────────────────────────
try:
    import nltk
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Downloading NLTK punkt tokenizer...")
        nltk.download('punkt', quiet=True)
except ImportError:
    NLTK_AVAILABLE = False
    print("NLTK not installed. Using basic tokenization.")

# ── Paninian verb analyzer ──────────────────────────────────────
try:
    from modules.paninian_analyzer import PaninianAnalyzer
    PANINIAN_AVAILABLE = True
except ImportError as e:
    PANINIAN_AVAILABLE = False
    print(f"⚠️ Paninian analyzer not available: {e}")

# ── Noun analyzer ───────────────────────────────────────────────
try:
    from modules.noun_analyzer import NounAnalyzer
    NOUN_AVAILABLE = True
except ImportError as e:
    NOUN_AVAILABLE = False
    print(f"⚠️ Noun analyzer not available: {e}")


class SanskritNLP:
    def __init__(self):
        # ── Dictionary (curated) ────────────────────────────────
        self.vocabulary = {
            # Nouns
            "रामः":    {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular", "meaning": "Rama"},
            "वनम्":    {"pos": "noun", "gender": "neuter",    "case": "accusative", "number": "singular", "meaning": "forest"},
            "सीता":    {"pos": "noun", "gender": "feminine",  "case": "nominative", "number": "singular", "meaning": "Sita"},
            "सुतः":    {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular", "meaning": "son"},
            "पुस्तकम्": {"pos": "noun", "gender": "neuter",    "case": "nominative", "number": "singular", "meaning": "book"},
            "फलम्":    {"pos": "noun", "gender": "neuter",    "case": "nominative", "number": "singular", "meaning": "fruit"},
            "बालकः":   {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular", "meaning": "boy"},
            "बालिका":  {"pos": "noun", "gender": "feminine",  "case": "nominative", "number": "singular", "meaning": "girl"},
            "विद्यालय": {"pos": "noun", "gender": "masculine", "case": "base",       "number": "singular", "meaning": "school"},
            "विद्यालयम्": {"pos": "noun", "gender": "masculine", "case": "accusative", "number": "singular", "meaning": "school (to)"},
            "विद्यालयं":  {"pos": "noun", "gender": "masculine", "case": "accusative", "number": "singular", "meaning": "school (to)"},
            "गृहम्":   {"pos": "noun", "gender": "neuter",    "case": "nominative", "number": "singular", "meaning": "house"},
            "जलम्":    {"pos": "noun", "gender": "neuter",    "case": "nominative", "number": "singular", "meaning": "water"},

            # Pronouns
            "अहं":     {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "first",  "meaning": "I"},
            "अहम्":    {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "first",  "meaning": "I"},
            "सः":      {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "third",  "gender": "masculine", "meaning": "he"},
            "सा":      {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "third",  "gender": "feminine",  "meaning": "she"},
            "तत्":     {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "third",  "gender": "neuter",    "meaning": "it"},
            "त्वम्":   {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "second", "meaning": "you"},
            "ते":      {"pos": "pronoun", "case": "nominative", "number": "plural",   "person": "third",  "meaning": "they"},
            "वयम्":    {"pos": "pronoun", "case": "nominative", "number": "plural",   "person": "first",  "meaning": "we"},

            # Verbs
            "गच्छति":  {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "goes"},
            "गच्छामि": {"pos": "verb", "tense": "present", "person": "first", "number": "singular", "meaning": "I go"},
            "गच्छसि":  {"pos": "verb", "tense": "present", "person": "second", "number": "singular", "meaning": "you go"},
            "अस्ति":   {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "is"},
            "पठति":    {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "reads"},
            "खादति":   {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "eats"},
            "पिबति":   {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "drinks"},
            "करोति":   {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "does"},
            "भवति":    {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "becomes"},
        }

        self.grammar_rules = [
            {"rule": "Subject-verb agreement", "pattern": r".*ः.*ति$",
             "description": "Nominative noun should agree with verb"},
            {"rule": "Case endings", "pattern": r".*म्$",
             "description": "Accusative case ending for objects"},
        ]

        # ── Analyzers ───────────────────────────────────────────
        self.paninian = None
        if PANINIAN_AVAILABLE:
            try:
                self.paninian = PaninianAnalyzer()
                print("✅ SanskritNLP: Paninian verb analyzer ready")
            except Exception as e:
                print(f"⚠️ SanskritNLP: Paninian init failed: {e}")

        self.noun_analyzer = None
        if NOUN_AVAILABLE:
            try:
                self.noun_analyzer = NounAnalyzer()
                print("✅ SanskritNLP: Noun analyzer ready")
            except Exception as e:
                print(f"⚠️ SanskritNLP: Noun init failed: {e}")

        # ── AI config ───────────────────────────────────────────
        self.api_key = os.getenv("XAI_API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.ai_provider: str = "Local"
        self.ai_model: str = "None"

        if self.api_key and isinstance(self.api_key, str):
            if self.api_key.startswith("gsk_"):
                self.ai_provider = "Groq"
                self.base_url = "https://api.groq.com/openai/v1"
                self.ai_model = "openai/gpt-oss-120b"
                print("SanskritNLP: Groq API key detected (fallback only)")
            else:
                self.ai_provider = "Grok"
                self.base_url = self.base_url or "https://api.x.ai/v1"
                self.ai_model = "grok-beta"
                print(f"SanskritNLP: {self.ai_provider} API key detected (fallback only)")
        else:
            print("SanskritNLP: No AI fallback key found")

    # ==============================================================
    # Tokenization
    # ==============================================================
    def tokenize(self, text: str) -> List[str]:
        if NLTK_AVAILABLE:
            try:
                clean_text = text.replace('|', '।').replace('.', '।')
                return word_tokenize(clean_text)
            except Exception:
                pass
        words = re.findall(r'[\u0900-\u097F]+|[.,!?;।|]', text)
        return [w for w in words if w.strip()]

    # ==============================================================
    # Word classification — three-layer pipeline
    # ==============================================================
    def _classify_word(self, word: str) -> Dict[str, Any]:
        """
        Classify one word:
          1. Dictionary (with Paninian enrichment for verbs)
          2. Noun analyzer
          3. Paninian verb analyzer
          4. Unknown
        """
        clean = re.sub(r'[.,!?;।|]$', '', word).strip()

        # ── Layer 1: Dictionary ─────────────────────────────────
        entry = None
        if clean in self.vocabulary:
            entry = self.vocabulary[clean]
        else:
            alt = clean
            if clean.endswith('ं'):
                alt = clean[:-1] + 'म्'
            elif clean.endswith('म्'):
                alt = clean[:-1] + 'ं'
            if alt in self.vocabulary:
                entry = self.vocabulary[alt]

        if entry:
            analysis = dict(entry)  # copy so we don't mutate vocabulary

            # If dictionary says it's a verb, enrich with Paninian morphology
            if entry.get('pos') == 'verb' and self.paninian:
                try:
                    verb = self.paninian.analyze_verb(clean)
                    if verb.get('is_verb'):
                        analysis.update({
                            'root': verb.get('root', ''),
                            'root_slp1': verb.get('root_slp1', ''),
                            'lakara': verb.get('tense', ''),
                            'purusha': verb.get('person', ''),
                            'vacana': verb.get('number', ''),
                            'gana': verb.get('class', ''),
                            'pada': verb.get('pada', ''),
                            'suffix': verb.get('suffix', ''),
                            'rules_applied': verb.get('rules_applied', []),
                        })
                except Exception:
                    pass

            return {
                'word': word,
                'pos': entry.get('pos', 'unknown'),
                'source': 'dictionary',
                'meaning': entry.get('meaning', ''),
                'analysis': analysis,
            }

        # ── Layer 2: Noun analyzer ──────────────────────────────
        if self.noun_analyzer:
            try:
                noun = self.noun_analyzer.analyze_best(clean)
                if noun.get('pos') == 'noun' and noun.get('method') == 'declension_rule':
                    stem = noun.get('stem', '')
                    if len(stem) >= 2:
                        return {
                            'word': word,
                            'pos': 'noun',
                            'source': 'noun_rule',
                            'meaning': 'unknown (not in dictionary)',
                            'analysis': {
                                'stem': stem,
                                'gender': noun.get('gender', ''),
                                'case': noun.get('case', ''),
                                'number': noun.get('number', ''),
                                'pattern': noun.get('pattern', ''),
                            },
                        }
            except Exception:
                pass

        # ── Layer 3: Paninian verb analyzer ─────────────────────
        if self.paninian:
            try:
                verb = self.paninian.analyze_verb(clean)
                if verb.get('is_verb'):
                    return {
                        'word': word,
                        'pos': 'verb',
                        'source': 'paninian',
                        'meaning': f"root: {verb.get('root', '?')}",
                        'analysis': {
                            'root': verb.get('root', ''),
                            'root_slp1': verb.get('root_slp1', ''),
                            'lakara': verb.get('tense', ''),
                            'purusha': verb.get('person', ''),
                            'vacana': verb.get('number', ''),
                            'gana': verb.get('class', ''),
                            'pada': verb.get('pada', ''),
                            'suffix': verb.get('suffix', ''),
                            'rules_applied': verb.get('rules_applied', []),
                            'derivation_steps': len(verb.get('derivation', [])),
                        },
                    }
            except Exception:
                pass

        # ── Layer 4: Unknown ────────────────────────────────────
        return {
            'word': word,
            'pos': 'unknown',
            'source': 'none',
            'meaning': 'unknown',
            'analysis': {'note': 'Not resolved by any layer'},
        }

    # ==============================================================
    # Sentence-level checks
    # ==============================================================
    @staticmethod
    def _normalize_agreement_value(value: Any, aliases: Dict[str, str]) -> str:
        if isinstance(value, (list, tuple)):
            if len(value) != 1:
                return ""
            value = value[0]
        if value is None:
            return ""
        return aliases.get(str(value).strip().lower(), "")

    def _run_checks(self, text: str, breakdown: List[Dict]) -> List[str]:
        issues = []

        # 1. Punctuation
        if not text.strip().endswith(('।', '|', '.')):
            issues.append("Sentence must end with a Purna Virama (।)")

        # 2. Missing verb
        has_verb = any(b['pos'] == 'verb' for b in breakdown)
        if breakdown and not has_verb:
            issues.append("Sentence has no verb.")

        # 3. Subject-verb agreement
        number_aliases = {
            'eka': 'singular', 'dvi': 'dual', 'bahu': 'plural',
            'singular': 'singular', 'dual': 'dual', 'plural': 'plural',
            'एकवचन': 'singular', 'द्विवचन': 'dual', 'बहुवचन': 'plural',
        }
        person_aliases = {
            'uttama': 'first', 'first': 'first',
            'madhyama': 'second', 'madyama': 'second', 'second': 'second',
            'pratama': 'third', 'prathama': 'third', 'third': 'third',
        }

        verb_entries = [b for b in breakdown if b['pos'] == 'verb']
        subjects = [
            b for b in breakdown
            if b['pos'] in ('noun', 'pronoun')
            and str(b['analysis'].get('case', '')).lower() == 'nominative'
        ]
        if verb_entries and subjects:
            verb = verb_entries[0]['analysis']
            subject = subjects[0]
            subject_analysis = subject['analysis']

            verb_number = self._normalize_agreement_value(
                verb.get('vacana') or verb.get('number'), number_aliases
            )
            subject_number = self._normalize_agreement_value(
                subject_analysis.get('number'), number_aliases
            )
            if subject_number and verb_number and subject_number != verb_number:
                issues.append(
                    f"Subject is {subject_number} but verb is {verb_number} — check subject-verb agreement."
                )

            verb_person = self._normalize_agreement_value(
                verb.get('purusha') or verb.get('person'), person_aliases
            )
            subject_person_value = subject_analysis.get('person')
            if not subject_person_value and subject['pos'] == 'noun':
                subject_person_value = 'third'
            subject_person = self._normalize_agreement_value(
                subject_person_value, person_aliases
            )
            if subject_person and verb_person and subject_person != verb_person:
                issues.append(
                    f"Subject is {subject_person} person but verb is {verb_person} person — check subject-verb agreement."
                )

        # 4. Destination → accusative
        has_motion = False
        for b in breakdown:
            if b['pos'] != 'verb':
                continue
            a = b['analysis']
            if str(a.get('root_slp1', '')).lower().startswith('gam'):
                has_motion = True
                break
            if 'go' in str(a.get('meaning', '')).lower():
                has_motion = True
                break

        has_first_person = any(
            b['word'] in ('अहं', 'अहम्')
            or b.get('analysis', {}).get('stem') == 'अहम्'
            for b in breakdown
        )

        if has_first_person and has_motion:
            for b in breakdown:
                stem = b.get('analysis', {}).get('stem', '')
                if stem == 'विद्यालय' or b['word'].startswith('विद्यालय'):
                    case = str(b['analysis'].get('case', '')).lower()
                    if case and case != 'accusative':
                        issues.append(
                            "Destination 'विद्यालय' should be in Accusative Case (Dvitiya Vibhakti)."
                        )

        return issues

    # ==============================================================
    # Simple correction builder
    # ==============================================================
    def _build_correction(self, original: str, breakdown: List[Dict],
                          issues: List[str]) -> str:
        corrected = original

        # Destination fix
        if any('Dvitiya' in i or 'Accusative' in i for i in issues):
            if "विद्यालय" in corrected and "विद्यालयं" not in corrected:
                corrected = corrected.replace("विद्यालय", "विद्यालयं")

        # Punctuation fix
        corrected = corrected.strip()
        if corrected.endswith('.'):
            corrected = corrected[:-1] + "।"
        elif not corrected.endswith(('।', '|')):
            corrected += " ।"

        return corrected

    # ==============================================================
    # Main entry point
    # ==============================================================
    def analyze_text(self, text: str, mode: str = "Basic",
                     use_ai: bool = False) -> Dict[str, Any]:

        # Explicit AI mode → straight to AI
        if use_ai and self.api_key:
            return self.analyze_with_grok(text)

        normalized = text.replace('|', '।').replace('.', '।')
        words = self.tokenize(normalized)
        sanskrit_words = [w for w in words if re.match(r'[\u0900-\u097F]+', w)]

        if len(sanskrit_words) < 1:
            return {"error": "Please enter some text to analyze"}

        # Word-by-word classification
        breakdown = [self._classify_word(w) for w in sanskrit_words]

        # Sentence-level issues
        issues = self._run_checks(text, breakdown)

        # Score
        score = max(0, 100 - len(issues) * 15)

        # Translation (with graceful fallback on rate-limit)
        try:
            translation = self.translate_sanskrit_to_english(normalized)
        except Exception as e:
            print(f"Translation error: {e}")
            translation = self.mock_translate(normalized)

        # Corrected sentence
        corrected = self._build_correction(text, breakdown, issues)
        correction_summary = (
            "Corrected sentence structure." if issues else "No errors found."
        )

        # Source counts
        source_counts: Dict[str, int] = {}
        for b in breakdown:
            source_counts[b['source']] = source_counts.get(b['source'], 0) + 1

        return {
            "score": score,
            "issues": issues,
            "corrected_sentence": corrected,
            "correction_summary": correction_summary,
            "breakdown": breakdown,
            "word_count": len(sanskrit_words),
            "translation": translation,
            "analysis_mode": "Hybrid (Paninian + Noun + Dictionary)",
            "ai_verified": False,
            "source_counts": source_counts,
        }

    # ==============================================================
    # AI fallback
    # ==============================================================
    def analyze_with_grok(self, text: str) -> Dict[str, Any]:
        print(f"SanskritNLP: AI analysis for: {text} using {self.ai_provider}")
        try:
            prompt = f"""
            Task: You are an expert Sanskrit grammarian and Pāṇini scholar. Analyze: "{text}"

            Output STRICT JSON:
            {{
                "score": int,
                "issues": ["list of strings"],
                "corrected_sentence": "corrected version in Devanagari",
                "correction_summary": "reason",
                "breakdown": [
                    {{"word": "w", "pos": "POS", "meaning": "English", "analysis": {{}}}}
                ],
                "translation": "English translation"
            }}
            """
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.ai_model,
                "messages": [
                    {"role": "system",
                     "content": "You are an expert Sanskrit grammarian. Output valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers, json=payload, timeout=30,
            )
            if response.status_code != 200:
                print(f"{self.ai_provider} API ERROR: {response.status_code}")
                return self.analyze_text(text, mode="Local Fallback", use_ai=False)

            result = response.json()
            analysis_text = result['choices'][0]['message']['content']
            m = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            analysis_json = json.loads(m.group(0)) if m else json.loads(analysis_text)

            if not isinstance(analysis_json, dict):
                raise ValueError("AI analysis response must be a JSON object")

            normalized = text.replace('|', '।').replace('.', '।')
            sanskrit_words = [
                word for word in self.tokenize(normalized)
                if re.match(r'[\u0900-\u097F]+', word)
            ]
            issues = analysis_json.setdefault("issues", [])
            breakdown = analysis_json.setdefault("breakdown", [])
            if not isinstance(issues, list) or not isinstance(breakdown, list):
                raise ValueError("AI analysis issues and breakdown must be lists")

            analysis_json.setdefault("score", max(0, 100 - len(issues) * 15))
            analysis_json.setdefault("corrected_sentence", self._build_correction(
                text, breakdown, issues
            ))
            analysis_json.setdefault(
                "correction_summary",
                "Corrected sentence structure." if issues else "No errors found.",
            )
            analysis_json.setdefault("word_count", len(sanskrit_words))
            analysis_json.setdefault("translation", self.mock_translate(normalized))
            source_counts: Dict[str, int] = {}
            for item in breakdown:
                if isinstance(item, dict) and item.get("source"):
                    source = str(item["source"])
                    source_counts[source] = source_counts.get(source, 0) + 1
            analysis_json.setdefault("source_counts", source_counts)
            analysis_json["analysis_mode"] = f"{self.ai_provider} AI"
            analysis_json["ai_verified"] = True
            return analysis_json

        except Exception as e:
            print(f"AI Error: {e}")
            return self.analyze_text(text, mode="AI Fallback", use_ai=False)

    # ==============================================================
    # Translation
    # ==============================================================
    def mock_translate(self, text: str) -> str:
        translations = {
            "रामः वनं गच्छति।": "Rama goes to the forest.",
            "सीता अस्ति।": "Sita is.",
            "सुतः पुस्तकं पठति।": "The son reads a book.",
            "बालकः फलं खादति।": "The boy eats fruit.",
        }
        if text in translations:
            return translations[text]
        return "Translation unavailable"

    def translate_sanskrit_to_english(self, text: str) -> str:
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source='auto', target='en')
            translation = translator.translate(text)
            if translation and translation != text:
                return translation
            return self.mock_translate(text)
        except Exception as e:
            print(f"Translation error: {e}")
            return self.mock_translate(text)

    # ==============================================================
    # Legacy helpers (kept for compatibility)
    # ==============================================================
    def check_grammar(self, text: str) -> List[Dict]:
        issues = []
        for rule in self.grammar_rules:
            if not re.search(rule["pattern"], text.replace(" ", "")):
                issues.append({
                    "rule": rule["rule"],
                    "description": rule["description"],
                    "suggestion": f"Check {rule['rule'].lower()}",
                })
        return issues

    def get_word_details(self, word: str) -> Dict:
        if word in self.vocabulary:
            return self.vocabulary[word]
        return {"pos": "unknown", "meaning": "Not in database"}