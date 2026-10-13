"""
NLP processor for Sanskrit text analysis

Pipeline:
  1. Dictionary lookup (highest priority)
     - Verb entries are enriched with Paninian morphology
  2. Paninian verb analyzer (Prakriya) — authoritative for verbs
  3. Noun analyzer (declension rules) — for non-verbs
  4. AI fallback (only when use_ai=True)

Correction:
  - Missing Purna Virama
  - Destination → accusative (motion verbs)
  - Subject-verb agreement, via:
      1. Prakriya VerbFormGenerator (general)
      2. Local PARADIGM_TABLE (common roots)
      3. Suffix-stripping fallback (regular लट् verbs)

Output contract:
  { score, issues, corrected_sentence, breakdown, word_count,
    translation, analysis_mode, ai_verified, source_counts }
"""

import re
import random
import os
import requests
import json
from typing import Dict, List, Any, Tuple
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
    print(f"Paninian analyzer not available: {e}")

# ── Noun analyzer ───────────────────────────────────────────────
try:
    from modules.noun_analyzer import NounAnalyzer
    NOUN_AVAILABLE = True
except ImportError as e:
    NOUN_AVAILABLE = False
    print(f"Noun analyzer not available: {e}")


# ─────────────────────────────────────────────────────────────
# Fallback verb paradigm table
# Used only when the Prakriya generator cannot produce the form.
# Covers लट् (present tense) for ~15 common roots.
# ─────────────────────────────────────────────────────────────
PARADIGM_TABLE = {
    'gam': {  # गम् — to go
        'first':  {'singular': 'गच्छामि', 'dual': 'गच्छावः', 'plural': 'गच्छामः'},
        'second': {'singular': 'गच्छसि',  'dual': 'गच्छथः', 'plural': 'गच्छथ'},
        'third':  {'singular': 'गच्छति',  'dual': 'गच्छतः', 'plural': 'गच्छन्ति'},
    },
    'paW': {  # पठ् — to read
        'first':  {'singular': 'पठामि', 'dual': 'पठावः', 'plural': 'पठामः'},
        'second': {'singular': 'पठसि',  'dual': 'पठथः', 'plural': 'पठथ'},
        'third':  {'singular': 'पठति',  'dual': 'पठतः', 'plural': 'पठन्ति'},
    },
    'KAd': {  # खाद् — to eat
        'first':  {'singular': 'खादामि', 'dual': 'खादावः', 'plural': 'खादामः'},
        'second': {'singular': 'खादसि',  'dual': 'खादथः', 'plural': 'खादथ'},
        'third':  {'singular': 'खादति',  'dual': 'खादतः', 'plural': 'खादन्ति'},
    },
    'pA': {   # पा — to drink
        'first':  {'singular': 'पिबामि', 'dual': 'पिबावः', 'plural': 'पिबामः'},
        'second': {'singular': 'पिबसि',  'dual': 'पिबथः', 'plural': 'पिबथ'},
        'third':  {'singular': 'पिबति',  'dual': 'पिबतः', 'plural': 'पिबन्ति'},
    },
    'as': {   # अस् — to be
        'first':  {'singular': 'अस्मि',  'dual': 'स्वः', 'plural': 'स्मः'},
        'second': {'singular': 'असि',   'dual': 'स्थः', 'plural': 'स्थ'},
        'third':  {'singular': 'अस्ति',  'dual': 'स्तः', 'plural': 'सन्ति'},
    },
    'kR': {   # कृ — to do
        'first':  {'singular': 'करोमि', 'dual': 'कुर्वः',  'plural': 'कुर्मः'},
        'second': {'singular': 'करोषि', 'dual': 'कुरुथः', 'plural': 'कुरुथ'},
        'third':  {'singular': 'करोति', 'dual': 'कुरुतः', 'plural': 'कुर्वन्ति'},
    },
    'BU': {   # भू — to be / become
        'first':  {'singular': 'भवामि', 'dual': 'भवावः', 'plural': 'भवामः'},
        'second': {'singular': 'भवसि',  'dual': 'भवथः', 'plural': 'भवथ'},
        'third':  {'singular': 'भवति',  'dual': 'भवतः', 'plural': 'भवन्ति'},
    },
    'Bav': {  # alternate SLP1 key
        'first':  {'singular': 'भवामि', 'dual': 'भवावः', 'plural': 'भवामः'},
        'second': {'singular': 'भवसि',  'dual': 'भवथः', 'plural': 'भवथ'},
        'third':  {'singular': 'भवति',  'dual': 'भवतः', 'plural': 'भवन्ति'},
    },
    'liK': {  # लिख् — to write
        'first':  {'singular': 'लिखामि', 'dual': 'लिखावः', 'plural': 'लिखामः'},
        'second': {'singular': 'लिखसि',  'dual': 'लिखथः', 'plural': 'लिखथ'},
        'third':  {'singular': 'लिखति',  'dual': 'लिखतः', 'plural': 'लिखन्ति'},
    },
    'krIq': {  # क्रीड् — to play
        'first':  {'singular': 'क्रीडामि', 'dual': 'क्रीडावः', 'plural': 'क्रीडामः'},
        'second': {'singular': 'क्रीडसि',  'dual': 'क्रीडथः', 'plural': 'क्रीडथ'},
        'third':  {'singular': 'क्रीडति',  'dual': 'क्रीडतः', 'plural': 'क्रीडन्ति'},
    },
    'car': {  # चर् — to walk
        'first':  {'singular': 'चरामि', 'dual': 'चरावः', 'plural': 'चरामः'},
        'second': {'singular': 'चरसि',  'dual': 'चरथः', 'plural': 'चरथ'},
        'third':  {'singular': 'चरति',  'dual': 'चरतः', 'plural': 'चरन्ति'},
    },
    'DAv': {  # धाव् — to run
        'first':  {'singular': 'धावामि', 'dual': 'धावावः', 'plural': 'धावामः'},
        'second': {'singular': 'धावसि',  'dual': 'धावथः', 'plural': 'धावथ'},
        'third':  {'singular': 'धावति',  'dual': 'धावतः', 'plural': 'धावन्ति'},
    },
    'svap': {  # स्वप् — to sleep
        'first':  {'singular': 'स्वपामि', 'dual': 'स्वपावः', 'plural': 'स्वपामः'},
        'second': {'singular': 'स्वपसि',  'dual': 'स्वपथः', 'plural': 'स्वपथ'},
        'third':  {'singular': 'स्वपति',  'dual': 'स्वपतः', 'plural': 'स्वपन्ति'},
    },
    'zru': {  # श्रु — to hear
        'first':  {'singular': 'शृणोमि', 'dual': 'शृणुवः',  'plural': 'शृणुमः'},
        'second': {'singular': 'शृणोषि', 'dual': 'शृणुथः', 'plural': 'शृणुथ'},
        'third':  {'singular': 'शृणोति', 'dual': 'शृणुतः', 'plural': 'शृण्वन्ति'},
    },
    'dRz': {  # दृश् — to see
        'first':  {'singular': 'पश्यामि', 'dual': 'पश्यावः', 'plural': 'पश्यामः'},
        'second': {'singular': 'पश्यसि',  'dual': 'पश्यथः', 'plural': 'पश्यथ'},
        'third':  {'singular': 'पश्यति',  'dual': 'पश्यतः', 'plural': 'पश्यन्ति'},
    },
    'vad': {  # वद् — to speak
        'first':  {'singular': 'वदामि', 'dual': 'वदावः', 'plural': 'वदामः'},
        'second': {'singular': 'वदसि',  'dual': 'वदथः', 'plural': 'वदथ'},
        'third':  {'singular': 'वदति',  'dual': 'वदतः', 'plural': 'वदन्ति'},
    },
    'has': {  # हस् — to laugh
        'first':  {'singular': 'हसामि', 'dual': 'हसावः', 'plural': 'हसामः'},
        'second': {'singular': 'हससि',  'dual': 'हसथः', 'plural': 'हसथ'},
        'third':  {'singular': 'हसति',  'dual': 'हसतः', 'plural': 'हसन्ति'},
    },
}


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
            "ग्रामः":  {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular", "meaning": "village"},
            "ग्रामम्": {"pos": "noun", "gender": "masculine", "case": "accusative", "number": "singular", "meaning": "village (to)"},
            "उद्यानम्": {"pos": "noun", "gender": "neuter",   "case": "nominative", "number": "singular", "meaning": "garden"},
            "उद्याने":  {"pos": "noun", "gender": "neuter",   "case": "locative",   "number": "singular", "meaning": "in the garden"},

            # Pronouns
            "अहं":     {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "first",  "meaning": "I"},
            "अहम्":    {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "first",  "meaning": "I"},
            "सः":      {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "third",  "gender": "masculine", "meaning": "he"},
            "सा":      {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "third",  "gender": "feminine",  "meaning": "she"},
            "तत्":     {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "third",  "gender": "neuter",    "meaning": "it"},
            "त्वम्":   {"pos": "pronoun", "case": "nominative", "number": "singular", "person": "second", "meaning": "you"},
            "ते":      {"pos": "pronoun", "case": "nominative", "number": "plural",   "person": "third",  "meaning": "they"},
            "वयम्":    {"pos": "pronoun", "case": "nominative", "number": "plural",   "person": "first",  "meaning": "we"},
            "वयं":     {"pos": "pronoun", "case": "nominative", "number": "plural",   "person": "first",  "meaning": "we"},

            # Verbs
            "गच्छति":  {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "goes"},
            "गच्छामि": {"pos": "verb", "tense": "present", "person": "first", "number": "singular", "meaning": "I go"},
            "गच्छसि":  {"pos": "verb", "tense": "present", "person": "second", "number": "singular", "meaning": "you go"},
            "गच्छन्ति": {"pos": "verb", "tense": "present", "person": "third", "number": "plural", "meaning": "they go"},
            "अस्ति":   {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "is"},
            "पठति":    {"pos": "verb", "tense": "present", "person": "third", "number": "singular", "meaning": "reads"},
            "पठन्ति":  {"pos": "verb", "tense": "present", "person": "third", "number": "plural", "meaning": "they read"},
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
                print("SanskritNLP: Paninian verb analyzer ready")
            except Exception as e:
                print(f"SanskritNLP: Paninian init failed: {e}")

        self.noun_analyzer = None
        if NOUN_AVAILABLE:
            try:
                self.noun_analyzer = NounAnalyzer()
                print("SanskritNLP: Noun analyzer ready")
            except Exception as e:
                print(f"SanskritNLP: Noun init failed: {e}")

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
    # Word classification — four-layer pipeline
    #
    # Priority:  Dictionary → Verb (Prakriya) → Noun (declension) → Unknown
    #
    # NOTE: The verb layer runs BEFORE the noun layer. Prakriya's
    # validation gate rejects non-verbs, so words like रामः still fall
    # through to the noun analyzer. Meanwhile verb forms ending in "ः"
    # (e.g. क्रीडामः, गच्छामः) are correctly recognized as verbs.
    # ==============================================================
    def _classify_word(self, word: str) -> Dict[str, Any]:
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
            analysis = dict(entry)

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

        # ── Layer 2: Paninian verb analyzer ─────────────────────
        # Moved BEFORE the noun analyzer. Prakriya's validation gate
        # ensures only genuine verb forms are accepted.
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
                            'raw_verb_with_markers': verb.get('raw_verb_with_markers', ''),
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

        # ── Layer 3: Noun analyzer ──────────────────────────────
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

        # ── Layer 4: Unknown ────────────────────────────────────
        return {
            'word': word,
            'pos': 'unknown',
            'source': 'none',
            'meaning': 'unknown',
            'analysis': {'note': 'Not resolved by any layer'},
        }

    # ==============================================================
    # Sentence-level helpers
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

    def _get_correct_verb_form(
        self,
        surface_form: str,
        analysis: Dict[str, Any],
        target_person: str,
        target_number: str,
    ) -> str:
        """
        Generate the correctly-inflected form of a verb for the given
        person and number.

        Resolution order:
          1. Prakriya VerbFormGenerator — general.
          2. Local PARADIGM_TABLE — fast lookup for ~15 common roots.
          3. Suffix-stripping fallback — last resort for regular लट् verbs.
        """
        person = str(target_person or '').lower()
        number = str(target_number or '').lower()

        if person not in ('first', 'second', 'third'):
            return None
        if number not in ('singular', 'dual', 'plural'):
            return None

        # ── 1. Try the Prakriya generator ────────────────────────
        if self.paninian and hasattr(self.paninian, 'generate_verb_form'):
            root_slp1 = analysis.get('root_slp1') or ''
            raw_root = analysis.get('raw_verb_with_markers') or ''
            lakara = analysis.get('lakara') or analysis.get('tense') or 'law'

            person_slp1 = {
                'first': 'uttama',
                'second': 'maDyama',
                'third': 'praTama',
            }[person]
            number_slp1 = {
                'singular': 'eka',
                'dual': 'dvi',
                'plural': 'bahu',
            }[number]

            try:
                generated = self.paninian.generate_verb_form(
                    root_slp1, lakara, person_slp1, number_slp1,
                    raw_root_with_markers=raw_root,
                )
                if generated:
                    return generated
            except Exception:
                pass

        # ── 2. Fall back to local paradigm table ─────────────────
        root_slp1 = analysis.get('root_slp1') or ''
        paradigm = PARADIGM_TABLE.get(root_slp1)
        if paradigm:
            found = paradigm.get(person, {}).get(number)
            if found:
                return found

        # ── 3. Last resort — suffix stripping (present tense only) ─
        lakara = str(analysis.get('lakara') or analysis.get('tense') or '').lower()
        if lakara not in ('law', 'लट्'):
            return None

        endings = ['न्ति', 'ामः', 'ावः', 'आमि', 'थः', 'सि', 'ति', 'तः', 'थ',
                   'न्ते', 'से', 'ते']
        stem = surface_form
        for ending in endings:
            if surface_form.endswith(ending) and len(surface_form) > len(ending) + 1:
                stem = surface_form[:-len(ending)]
                break

        if stem == surface_form:
            return None

        suffix = {
            ('first',  'singular'): 'आमि',
            ('first',  'dual'):     'आवः',
            ('first',  'plural'):   'आमः',
            ('second', 'singular'): 'सि',
            ('second', 'dual'):     'थः',
            ('second', 'plural'):   'थ',
            ('third',  'singular'): 'ति',
            ('third',  'dual'):     'तः',
            ('third',  'plural'):   'न्ति',
        }.get((person, number))

        if suffix:
            return stem + suffix
        return None

    def _replace_token(self, sentence: str, old: str, new: str) -> str:
        """
        Replace the first occurrence of the exact token `old` with `new`,
        preserving trailing punctuation. Never touches substrings.
        """
        tokens = sentence.split()
        result = []
        replaced = False
        for tok in tokens:
            if replaced:
                result.append(tok)
                continue
            m = re.match(r'^([\u0900-\u097F]+)([।॥.,!?;|]*)$', tok)
            if not m:
                result.append(tok)
                continue
            core, punct = m.group(1), m.group(2)
            if core == old:
                result.append(new + punct)
                replaced = True
            else:
                result.append(tok)
        return ' '.join(result)

    def _fix_destination_accusative(self, sentence: str) -> str:
        """
        Replace only the exact nominative/bare form of विद्यालय or ग्रामः
        with the accusative. Never touches विद्यालयम्, विद्यालयं, or any
        word that merely contains the stem as a substring.
        """
        accusative_map = {
            'विद्यालय':  'विद्यालयं',
            'विद्यालयः': 'विद्यालयं',
            'ग्राम':    'ग्रामम्',
            'ग्रामः':   'ग्रामम्',
        }
        tokens = sentence.split()
        fixed = []
        for tok in tokens:
            m = re.match(r'^([\u0900-\u097F]+)([।॥.,!?;|]*)$', tok)
            if not m:
                fixed.append(tok)
                continue
            core, punct = m.group(1), m.group(2)
            if core in accusative_map:
                fixed.append(accusative_map[core] + punct)
            else:
                fixed.append(tok)
        return ' '.join(fixed)

    def _run_checks(self, text: str, breakdown: List[Dict]) -> Tuple[List[str], List[Dict]]:
        """
        Run sentence-level checks.

        Returns:
            issues       : list of human-readable issue strings
            corrections  : list of machine-applicable correction dicts
        """
        issues: List[str] = []
        corrections: List[Dict[str, Any]] = []

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
            verb_surface = verb_entries[0]['word']
            subject = subjects[0]
            subject_analysis = subject['analysis']

            verb_number = self._normalize_agreement_value(
                verb.get('vacana') or verb.get('number'), number_aliases
            )
            subject_number = self._normalize_agreement_value(
                subject_analysis.get('number'), number_aliases
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

            number_mismatch = bool(subject_number and verb_number and subject_number != verb_number)
            person_mismatch = bool(subject_person and verb_person and subject_person != verb_person)

            if number_mismatch or person_mismatch:
                expected = self._get_correct_verb_form(
                    verb_surface,
                    verb,
                    subject_person or 'third',
                    subject_number or 'singular',
                )

                if number_mismatch and person_mismatch:
                    issues.append(
                        f"Subject '{subject['word']}' ({subject_person} person, {subject_number}) "
                        f"does not agree with verb '{verb_surface}' "
                        f"({verb_person} person, {verb_number}) — check subject-verb agreement."
                    )
                elif number_mismatch:
                    issues.append(
                        f"Subject is {subject_number} but verb is {verb_number} "
                        f"— check subject-verb agreement."
                    )
                else:
                    issues.append(
                        f"Subject is {subject_person} person but verb is {verb_person} person "
                        f"— check subject-verb agreement."
                    )

                if expected and expected != verb_surface:
                    corrections.append({
                        'type': 'verb_agreement',
                        'old': verb_surface,
                        'new': expected,
                    })

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
                w_text = b.get('word', '')
                if stem in ('विद्यालय', 'ग्राम') or w_text.startswith(('विद्यालय', 'ग्राम')):
                    if w_text in ('विद्यालयम्', 'विद्यालयं', 'ग्रामम्', 'ग्रामं'):
                        continue
                    case = str(b['analysis'].get('case', '')).lower()
                    if case and case != 'accusative':
                        issues.append(
                            f"Destination '{w_text}' should be in Accusative Case (Dvitiya Vibhakti)."
                        )
                        break

        return issues, corrections

    # ==============================================================
    # Correction builder
    # ==============================================================
    def _build_correction(
        self,
        original: str,
        breakdown: List[Dict],
        issues: List[str],
        corrections: List[Dict] = None,
    ) -> str:
        corrected = original
        corrections = corrections or []

        # 1. Verb-agreement corrections (token-boundary safe)
        for corr in corrections:
            if corr.get('type') != 'verb_agreement':
                continue
            old = corr.get('old')
            new = corr.get('new')
            if not old or not new or old == new:
                continue
            corrected = self._replace_token(corrected, old, new)

        # 2. Destination accusative fix (whole-token replacement)
        if any('Dvitiya' in i or 'Accusative' in i for i in issues):
            corrected = self._fix_destination_accusative(corrected)

        # 3. Punctuation
        corrected = corrected.strip()
        if corrected.endswith('.'):
            corrected = corrected[:-1] + "।"
        elif not corrected.endswith(('।', '|')):
            corrected += " ।"

        # 4. Final cleanup — no whitespace before a danda
        corrected = re.sub(r'\s+([।॥])', r'\1', corrected)

        return corrected.strip()

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

        # Sentence-level checks
        issues, corrections = self._run_checks(text, breakdown)

        # Score
        score = max(0, 100 - len(issues) * 15)

        # Keep grammar analysis independent of translation pipelines.
        translation = ""

        # Corrected sentence
        corrected = self._build_correction(text, breakdown, issues, corrections)
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
            "analysis_mode": "Grammar Check",
            "ai_verified": False,
            "source_counts": source_counts,
        }

    # ==============================================================
    # AI fallback
    # ==============================================================
    def analyze_with_grok(self, text: str) -> Dict[str, Any]:
        print(f"SanskritNLP: AI grammar analysis using {self.ai_provider}")
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
                ]
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
            analysis_json.setdefault(
                "corrected_sentence",
                self._build_correction(text, breakdown, issues, []),
            )
            analysis_json.setdefault(
                "correction_summary",
                "Corrected sentence structure." if issues else "No errors found.",
            )
            analysis_json.setdefault("word_count", len(sanskrit_words))
            analysis_json["translation"] = ""
            source_counts: Dict[str, int] = {}
            for item in breakdown:
                if isinstance(item, dict) and item.get("source"):
                    source = str(item["source"])
                    source_counts[source] = source_counts.get(source, 0) + 1
            analysis_json.setdefault("source_counts", source_counts)
            analysis_json["analysis_mode"] = "AI Scan"
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