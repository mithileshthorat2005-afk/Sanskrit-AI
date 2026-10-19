"""
NLP processor for Sanskrit text analysis

Pipeline:
  1. Dictionary lookup (highest priority)
     - Verb entries are enriched with Paninian morphology
  2. Paninian verb analyzer (Prakriya) — authoritative for verbs
  3. Local PARADIGM_TABLE reverse lookup (regular लट् active verbs)
  4. Local passive (यक् / कर्मणि प्रयोग) reverse lookup — regular
     लट् passives of a curated root set (see PASSIVE_ROOT_STEMS)
  5. Noun analyzer (declension rules) — for non-verbs
  6. AI fallback (only when use_ai=True)

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
import math
import random
import os
import csv
import requests
import json
from typing import Dict, List, Any, Tuple, Optional
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


# ─────────────────────────────────────────────────────────────
# Passive (यक्-pratyaya / कर्मणि प्रयोग) support
#
# A यक्-passive of root R is R + य + आत्मनेपद लट् suffix, e.g.
# गम् → गम्य + ते → गम्यते. The key of PASSIVE_ROOT_STEMS is the
# यक्-extended stem (root + य), written with its explicit virama,
# so that stem + ending concatenates to the correct surface form.
#
# Only roots whose passive is a transparent root+य extension are
# listed. Roots with irregular passive stems are deliberately
# EXCLUDED because the generated form would be unattested:
#   कृ → क्रियते (notकृयते), पा → पीयते (not पायते),
#   भू → भव्यते (not भूयते), श्रु → श्रूयते (not श्रुयते)
# Values are the SLP1 root keys of PARADIGM_TABLE.
# ─────────────────────────────────────────────────────────────
PASSIVE_ROOT_STEMS = {  # यक्-extended stem (root + य) → SLP1 root
    'गम्य':  'gam',   # गम् — to go       → गम्यते
    'पठ्य':  'paW',   # पठ् — to read     → पठ्यते
    'खाद्य': 'KAd',   # खाद् — to eat     → खाद्यते
    'अस्य':  'as',    # अस् — to throw/be → अस्यते
    'लिख्य': 'liK',   # लिख् — to write   → लिख्यते
    'क्रीड्य': 'krIq',# क्रीड् — to play  → क्रीड्यते
    'चर्य':  'car',   # चर् — to walk     → चर्यते
    'धाव्य': 'DAv',   # धाव् — to run     → धाव्यते
    'स्वप्य': 'svap', # स्वप् — to sleep  → स्वप्यते
    'दृश्य': 'dRz',   # दृश् — to see    → दृश्यते
    'वद्य':  'vad',   # वद् — to speak   → वद्यते
    'हस्य':  'has',   # हस् — to laugh   → हस्यते
}

# आत्मनेपद लट् suffixes keyed by (person, number), written in their
# post-consonantal form so they concatenate directly after a यक् stem:
#   गम्य + ते   → गम्यते    गम्य + न्ते  → गम्यन्ते
#   गम्य + ेते  → गम्येते   गम्य + े    → गम्ये
#   गम्य + ावहे → गम्यावहे  गम्य + ध्वे  → गम्यध्वे
PASSIVE_LAT_ENDINGS = {
    ('third',  'singular'): 'ते',
    ('third',  'dual'):     'ेते',
    ('third',  'plural'):   'न्ते',
    ('second', 'singular'): 'से',
    ('second', 'dual'):     'ेथे',
    ('second', 'plural'):   'ध्वे',
    ('first',  'singular'): 'े',
    ('first',  'dual'):     'ावहे',
    ('first',  'plural'):   'ामहे',
}


class SanskritNLP:
    # Ollama Cloud issues keys shaped "<32 hex chars>.<token>" — a shape no
    # other provider uses. Matching on it lets a key pasted into the wrong
    # variable still reach the right endpoint, instead of being handed to
    # xAI and rejected with a misleading "Incorrect API key provided".
    OLLAMA_KEY_SHAPE = re.compile(r'^[0-9a-f]{32}\.')

    # Ollama Cloud's free plan serves only a few models; calling any other
    # one answers HTTP 402 "not included in your free usage".
    OLLAMA_FREE_MODEL = "gemma4:31b-cloud"
    OLLAMA_BASE_URL = "https://ollama.com/v1"

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
            # Dual/plural personal pronouns. Without explicit entries the noun
            # rule matches their final -म् as accusative singular, which drops
            # them out of the nominative-subject set and disables agreement
            # checking entirely for sentences built on them.
            "आवाम्":   {"pos": "pronoun", "case": "nominative", "number": "dual",    "person": "first",  "meaning": "we two"},
            "युवाम्":  {"pos": "pronoun", "case": "nominative", "number": "dual",    "person": "second", "meaning": "you two"},
            "यूयम्":   {"pos": "pronoun", "case": "nominative", "number": "plural",   "person": "second", "meaning": "you all"},
            # Genitive possessives. Prakriya accepts SLP1 "mama" (मम) as a
            # finite form of √mā and would otherwise classify मम as a VERB,
            # making it the agreement partner for the real subject and
            # producing a phantom mismatch on correct sentences.
            "मम":     {"pos": "pronoun", "case": "genitive",    "number": "singular", "person": "first",  "meaning": "my"},
            "तव":     {"pos": "pronoun", "case": "genitive",    "number": "singular", "person": "second", "meaning": "your"},

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

        # Reverse index of PARADIGM_TABLE: surface form -> (person, number, root_slp1).
        # _classify_word consults it to recognise regular present-tense (lat) verb
        # forms when the Paninian analyzer is unavailable (e.g. prakriya not
        # installed). Exact matching against curated conjugations keeps this safe:
        # indeclinables (इति, प्रति) and abstract nouns (शक्ति) that merely share a
        # verb ending are not matched.
        self._verb_paradigm_index: Dict[str, Tuple[str, str, str]] = {}
        for _root, _persons in PARADIGM_TABLE.items():
            for _person, _numbers in _persons.items():
                for _number, _form in _numbers.items():
                    # setdefault: first root wins when tables repeat a form
                    # (e.g. the 'Bav' alias repeats the 'BU' paradigm).
                    self._verb_paradigm_index.setdefault(_form, (_person, _number, _root))

        # Reverse index + per-root paradigm for यक्-passive (कर्मणि प्रयोग) लट्
        # forms, assembled from curated morphology (root+य+ending) — never
        # guessed. _passive_index   → recognition in _classify_word (Layer 3b).
        # _passive_paradigm        → voice-preserving correction.
        # _passive_stem_by_root    → inverts PASSIVE_ROOT_STEMS for correction.
        self._passive_index: Dict[str, Tuple[str, str, str]] = {}
        self._passive_paradigm: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._passive_stem_by_root: Dict[str, str] = {}
        for _stem, _root in PASSIVE_ROOT_STEMS.items():
            self._passive_stem_by_root.setdefault(_root, _stem)
            _para: Dict[str, Dict[str, str]] = {}
            for (_p, _n), _ending in PASSIVE_LAT_ENDINGS.items():
                _form = _stem + _ending
                _para.setdefault(_p, {})[_n] = _form
                # setdefault: first stem wins on any future collision
                self._passive_index.setdefault(_form, (_p, _n, _root))
            self._passive_paradigm[_root] = _para

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
        # Provider is chosen from which variable is set, then from key
        # shape. Ollama Cloud goes first because its key shape is unique,
        # so a key pasted into the wrong variable still routes correctly.
        # XAI_API_KEY stays supported for Groq (gsk_) and xAI keys, which
        # is what the deployed Render instance already configures.
        ollama_key = (os.getenv("OLLAMA_API_KEY") or "").strip()
        legacy_key = (os.getenv("XAI_API_KEY") or "").strip()

        self.api_key = ollama_key or legacy_key
        self.base_url = os.getenv("BASE_URL")
        self.ai_provider: str = "Local"
        self.ai_model: str = "None"
        # Why the most recent AI call failed, in the provider's own words.
        # Carried onto the degraded response so "no key", "bad key", "retired
        # model" and "provider down" are distinguishable instead of every
        # failure looking like a generic silent fallback.
        self.last_ai_error: str = ""
        # Model id discovered from GET /models after a model-related rejection.
        # None = not tried yet; "" = tried and found nothing usable.
        self._discovered_model: Optional[str] = None

        if self.api_key:
            if ollama_key or self.OLLAMA_KEY_SHAPE.match(self.api_key):
                self.ai_provider = "Ollama Cloud"
                self.base_url = self.OLLAMA_BASE_URL
                self.ai_model = os.getenv("AI_MODEL") or self.OLLAMA_FREE_MODEL
                print("SanskritNLP: Ollama Cloud API key detected (fallback only)")
            elif self.api_key.startswith("gsk_"):
                self.ai_provider = "Groq"
                self.base_url = "https://api.groq.com/openai/v1"
                self.ai_model = os.getenv("AI_MODEL") or "openai/gpt-oss-120b"
                print("SanskritNLP: Groq API key detected (fallback only)")
            else:
                self.ai_provider = "Grok"
                self.base_url = self.base_url or "https://api.x.ai/v1"
                # xAI retired `grok-beta`, so hardcoding a dead model name meant
                # even a VALID key would come back 400/404. Override with
                # AI_MODEL; otherwise use a current default and let
                # _resolve_model() confirm it against GET /models on first use.
                self.ai_model = os.getenv("AI_MODEL") or "grok-4-fast"
                print(f"SanskritNLP: {self.ai_provider} API key detected (fallback only)")
        else:
            print("SanskritNLP: No AI fallback key found")

        # ── On-disk lexicon ─────────────────────────────────────
        # `self.vocabulary` above is a hand-curated literal. The project
        # also ships ~1,370 words in data/*.csv. Those load into a
        # SEPARATE structure consulted only where the analysers come up
        # empty, so they can never take a word away from a layer that
        # already parsed it (see _classify_word).
        self._lexicon: Dict[str, Dict[str, str]] = {}
        self._load_lexicon()

        # ── Declension attestation index ───────────────────────
        # For every headword in the dictionaries above, record which
        # (stem, paradigm) pairs it proves. Used by Layer 4 to pick between
        # competing declension readings of the same token, e.g.
        #   विद्यालयः → a-masc/विद्यालय  (attested by विद्यालयम्)
        #             → i-masc/विद्याल    (attested by nothing)
        # Longest-match alone chose the second, mis-parsing a singular as a
        # plural. A token's own entry is excluded from vouching for itself,
        # or विद्यालयः would attest its own wrong parse.
        self._stem_attestation: Dict[Tuple[str, str], set] = {}
        self._build_stem_attestation()

    # ==============================================================
    # On-disk lexicon (data/*.csv)
    # ==============================================================
    # Two dictionaries ship with the project and are already used by
    # SanskritTranslator for translation:
    #
    #   data/sanskrit_translation_db.csv   1,267 rows
    #   data/sanskrit_words.csv              105 rows
    #
    # Layer 1 (`self.vocabulary`) never consulted them, with two results:
    #
    #   * layers 3/3b/4 return a real parse but no English gloss, so
    #     known words surfaced as "unknown (not in dictionary)";
    #   * a word absent from the curated literal but present in these
    #     files reached Layer 5 and was called unknown. That is the one
    #     thing the uncertainty contract forbids: an unknown word has to
    #     mean EVERY layer failed — and the dictionary is a layer.
    #
    # So the lexicon is a FALLBACK. It never preempts an analyser: it
    # only supplies a missing gloss, or rescues a word all five layers
    # missed. Curated entries always win.
    # ==============================================================
    DEVANAGARI_ONLY = re.compile(r'^[ऀ-ॿ]+$')

    # (filename, part-of-speech column, gloss columns in priority order).
    # Both files carry a clean `english` column, which is what gets used.
    # `meaning` is only a fallback and is filtered by LEXICON_JUNK_GLOSS.
    LEXICON_SOURCES = (
        ("sanskrit_translation_db.csv", "pos", ("english",)),
        ("sanskrit_words.csv", "word_type", ("english", "meaning")),
    )

    # The import script that wrote sanskrit_words.csv left placeholders
    # such as "Translation of agnih" in 49 of its 105 rows. Those are not
    # glosses, and showing one to a learner would be worse than showing
    # nothing at all.
    LEXICON_JUNK_GLOSS = re.compile(r'(?i)^translation of\b')

    # Parts of speech the pipeline understands. The CSVs also contain
    # stray values ("easy", "farmer", "invalid input", "not applicable")
    # which are data entry mistakes, not POS, and must never be reported
    # as a part of speech.
    LEXICON_POS = frozenset({
        'noun', 'verb', 'adjective', 'adverb', 'pronoun', 'auxiliary',
        'conjunction', 'interjection', 'numeral', 'particle',
        'preposition', 'direction', 'phrase', 'sentence',
    })

    def _load_lexicon(self) -> None:
        """Read the shipped CSV dictionaries into `self._lexicon`."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for filename, pos_col, gloss_cols in self.LEXICON_SOURCES:
            path = os.path.join(base_dir, "data", filename)
            if not os.path.exists(path):
                print(f"SanskritNLP: lexicon {filename} not found — skipped")
                continue
            try:
                with open(path, encoding="utf-8-sig", newline="") as fh:
                    for row in csv.DictReader(fh):
                        word = (row.get("devanagari") or "").strip()
                        # Single, purely-Devanagari tokens only. Rows the
                        # translator concatenates may be transliterations or
                        # multi-word phrases, which are not word entries.
                        if not word or not self.DEVANAGARI_ONLY.match(word):
                            continue
                        # Hand-tuned curated entries keep precedence.
                        if word in self.vocabulary or word in self._lexicon:
                            continue
                        gloss = self._pick_gloss(row, gloss_cols)
                        pos = (row.get(pos_col) or "").strip().lower()
                        if pos == "proper noun":
                            pos = "noun"
                        self._lexicon[word] = {
                            "pos": pos if pos in self.LEXICON_POS else "",
                            "meaning": gloss,
                        }
            except (OSError, csv.Error) as exc:
                print(f"SanskritNLP: lexicon {filename} unreadable — skipped ({exc})")

        print(f"SanskritNLP: lexicon loaded {len(self._lexicon)} words from disk")

    def _pick_gloss(self, row: Dict[str, str], gloss_cols: Tuple[str, ...]) -> str:
        """First usable English gloss among `gloss_cols`, or ''.

        A candidate is rejected when it is blank, is an import-script
        placeholder ("Translation of agnih"), or is itself Devanagari —
        a gloss is only a gloss if it is in the learner's language.
        """
        for col in gloss_cols:
            candidate = (row.get(col) or "").strip()
            if not candidate:
                continue
            if self.LEXICON_JUNK_GLOSS.search(candidate):
                continue
            if self.DEVANAGARI_ONLY.match(candidate):
                continue
            return candidate
        return ""

    def _lexicon_lookup(self, word: str) -> Optional[Dict[str, str]]:
        """Lexicon entry for `word`, honouring the ं/म् alternation Layer 1
        uses (विद्यालयं ↔ विद्यालयम्)."""
        entry = self._lexicon.get(word)
        if entry is not None:
            return entry
        alt = word
        if word.endswith('ं'):
            alt = word[:-1] + 'म्'
        elif word.endswith('म्'):
            alt = word[:-1] + 'ं'
        return self._lexicon.get(alt)

    def _lexicon_meaning(self, word: str) -> str:
        """English gloss for `word`, or '' when the lexicon lacks it."""
        entry = self._lexicon_lookup(word)
        return entry.get("meaning", "") if entry else ""

    def _build_stem_attestation(self) -> None:
        """Index which (stem, paradigm) pairs the shipped dictionaries prove.

        Stripping a declension ending off a headword is evidence that the
        stem really exists in that paradigm: विद्यालयम् proves
        (विद्यालय, a_masc). This is used only to CHOOSE between competing
        readings of a token — never to accept or reject one — so unseen but
        genuine vocabulary still parses normally.
        """
        if not self.noun_analyzer:
            return
        for headword in list(self.vocabulary) + list(self._lexicon):
            if not self.DEVANAGARI_ONLY.match(headword):
                continue
            for ending, _gender, _case, _number, pattern in self.noun_analyzer.endings:
                if len(headword) <= len(ending) or not headword.endswith(ending):
                    continue
                stem = headword[:-len(ending)]
                if len(stem) < 2:
                    continue
                self._stem_attestation.setdefault((stem, pattern), set()).add(headword)
        print(f"SanskritNLP: attested {len(self._stem_attestation)} "
              f"(stem, paradigm) pairs from disk")

    def _attested_candidates(self, word: str,
                             candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Competing readings of `word` that some OTHER headword vouches for.

        An empty list means the dictionaries have no opinion, and the caller
        must fall back to its existing behaviour rather than guess.
        """
        return [
            c for c in candidates
            if self._stem_attestation.get((c.get('stem', ''), c.get('pattern', '')),
                                          set()) - {word}
        ]

    def _disambiguate(self, word: str, readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Choose between the competing declension readings of one token.

        One surface ending can belong to several paradigms, and picking
        blindly is what produced two different bugs:

          * विद्यालयः matched the longer 'यः' ending and came out an i-masc
            nominative PLURAL of a stem विद्याल that exists nowhere. The
            dictionaries prove the a-masc reading instead (विद्यालयम् strips
            to विद्यालय), so attestation decides it.
          * सुन्दरी matched 'ी' and came out an i-masc nominative DUAL, so a
            correct sentence was told its subject disagreed with the verb.

        So:
          1. prefer readings some OTHER headword vouches for;
          2. when the dictionaries have no opinion, keep today's rule — the
             longest matching ending wins, unchanged;
          3. either way, a NUMBER that another plausible reading of the same
             token contradicts is simply not established. ी is an ī-stem
             nominative singular AND an i-masc nominative dual, so claiming
             'dual' for सुन्दरी would invent an agreement error. Report the
             feature as undecidable and let agreement stay silent.
        """
        attested = self._attested_candidates(word, readings)
        pool = attested or readings[:1]
        best = dict(pool[0])
        best.pop('word', None)          # the breakdown item already carries it

        # Contest the NUMBER only among readings of the SAME stem. Same stem
        # with the same case but a different number is a true homograph —
        # one word with two readings — so nobody can honestly assert either:
        #   सुन्दरी → (सुन्दर, ii-fem, nom, SINGULAR)  or
        #              (सुन्दर, a-neut, nom, DUAL)
        # A different STEM instead means a segmentation choice, and ending
        # length already settles that (सिंहाः = सिंह+ाः plural, not सिंहा+ः
        # singular; गुरवः = गुर+वः plural, not गुरव+ः singular). Blanking
        # the number there would just silence agreement on ordinary
        # plural subjects.
        contested_number = any(
            r.get('stem') == best.get('stem')
            and r.get('case') == best.get('case')
            and r.get('number') != best.get('number')
            for r in readings
        )
        if contested_number:
            best['number'] = ''
            best['number_ambiguous'] = True
            best['alternatives'] = [
                {k: r.get(k, '') for k in ('stem', 'gender', 'case', 'number', 'pattern')}
                for r in readings[:5]
            ]
        return best

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
    # Word classification — layered pipeline
    #
    # Priority:  Dictionary → Verb (Prakriya) → Active paradigm table
    #            → Passive paradigm table → Noun (declension) → Unknown
    #
    # NOTE: The verb layers run BEFORE the noun layer. Prakriya's
    # validation gate rejects non-verbs, so words like रामः still fall
    # through to the noun analyzer. Meanwhile verb forms ending in "ः"
    # (e.g. क्रीडामः, गच्छामः) are correctly recognized as verbs, and
    # passives (गम्यते, पठ्यते) are recognized before the noun analyzer's
    # bare "े" (locative) ending can steal them.
    # ==============================================================
    # ── Surface-form variants ──────────────────────────────────
    # Sanskrit spells the same word more than one way, and every layer
    # below matches literal endings, so a token has to be tried in each of
    # its spellings before it can honestly be called unresolvable.
    #
    #   anusvāra   बालकं  ↔  बालकम्   one accusative, two spellings. The
    #              table only ever held the explicit-virāma form, so the
    #              far commoner anusvāra spelling came out "unknown".
    #   visarga    बालको  ←  बालकः     ः → ओ before a voiced consonant
    #              मुनिर्  ←  मुनिः     ः → र् after इ/उ/ऋ
    #
    # Sandhi reversal is never speculative: it sits behind the token's own
    # spelling (Layer 1 never sees it unless the direct spelling already
    # failed), and the reversed base then has to survive the same real
    # layers — a dictionary hit or a declension parse — so a nonsense string
    # cannot be talked into a parse.
    def _surface_variants(self, clean: str) -> List[str]:
        variants = [clean]
        if clean.endswith('ं'):
            variants.append(clean[:-1] + 'म्')
        elif clean.endswith('म्'):
            variants.append(clean[:-1] + 'ं')
        for suffix, base in (('ो', 'ः'), ('र्', 'ः')):
            if clean.endswith(suffix) and len(clean) > len(suffix) + 1:
                variants.append(clean[:-len(suffix)] + base)
        return variants

    def _classify_word(self, word: str) -> Dict[str, Any]:
        clean = re.sub(r'[.,!?;।|]$', '', word).strip()
        variants = self._surface_variants(clean)

        # ── Layer 1: Dictionary — first claim on EVERY spelling ──
        # Layer priority has to outrank spelling priority. If the analysers
        # below were allowed to try the anusvāra spelling first, त्वं would
        # parse as a bare a-stem accusative and drop the person/number the
        # pronoun entry त्वम् carries — silencing agreement on the sentence.
        for surface in variants:
            entry = self.vocabulary.get(surface)
            if entry:
                return self._dictionary_result(word, clean, surface, entry)

        # ── Layers 2-5: analysers, one spelling at a time ────────
        for surface in variants:
            result = self._classify_analysers(word, clean, surface)
            if result is not None:
                return result

        return {
            'word': word,
            'pos': 'unknown',
            'source': 'none',
            'meaning': 'unknown',
            'analysis': {'note': 'Not resolved by any layer'},
        }

    def _dictionary_result(self, word: str, clean: str, surface: str,
                           entry: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 1's answer: a hand-curated vocabulary hit.

        The stored entry is copied, never mutated, so the class-level
        vocabulary literal stays pristine across requests.
        """
        analysis = dict(entry)

        if entry.get('pos') == 'verb' and self.paninian:
            try:
                verb = self.paninian.analyze_verb(surface)
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

        if surface != clean:
            analysis['resolved_from'] = surface

        return {
            'word': word,
            'pos': entry.get('pos', 'unknown'),
            'source': 'dictionary',
            'meaning': entry.get('meaning', ''),
            'analysis': analysis,
        }

    def _classify_analysers(self, word: str, clean: str,
                            surface: str) -> Optional[Dict[str, Any]]:
        """Run layers 2-5 against ONE spelling of `clean`.

        Layer 1 has already had first claim on every spelling (see
        `_classify_word`). `surface` is the spelling being tested, `clean`
        is the token as written, and `word` (with any trailing punctuation)
        is what gets reported. Returns None when nothing recognised this
        spelling, so the driver can try the next one.
        """
        # ── Layer 2: Paninian verb analyzer ─────────────────────
        # Moved BEFORE the noun analyzer. Prakriya's validation gate
        # ensures only genuine verb forms are accepted.
        if self.paninian:
            try:
                verb = self.paninian.analyze_verb(surface)
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

        # ── Layer 3: Local PARADIGM_TABLE (regular लट् verbs) ─────
        # The Paninian analyzer is authoritative but may be unavailable
        # (prakriya not installed). Fall back to an exact reverse lookup of the
        # curated PARADIGM_TABLE so regular present-tense forms are still
        # recognised with their person and number. Exact matching — rather than
        # a bare-suffix heuristic — cannot fire on indeclinables (इति, प्रति) or
        # abstract nouns (शक्ति) that merely share a verb ending, and it runs
        # before the noun analyzer, which otherwise mis-parses dual/plural verb
        # endings (गच्छतः, पठामः, …) as noun declensions.
        if surface in self._verb_paradigm_index:
            person, number, root_slp1 = self._verb_paradigm_index[surface]
            return {
                'word': word,
                'pos': 'verb',
                'source': 'paradigm_table',
                # Gloss comes from the lexicon: this layer parses
                # person/number but has no English meaning of its own.
                'meaning': self._lexicon_meaning(surface),
                'analysis': {
                    'root_slp1': root_slp1,
                    'tense': 'present',
                    'lakara': 'lat',
                    'person': person,
                    'number': number,
                },
            }

        # ── Layer 3b: Passive (यक् / कर्मणि प्रयोग) लट् forms ─────
        # Same exact-match safety model as Layer 3: only forms assembled
        # from PASSIVE_ROOT_STEMS × PASSIVE_LAT_ENDINGS are recognised, so
        # indeclinables/nouns that merely share an ending cannot match.
        # This MUST run before the noun analyzer, whose bare "े" (locative)
        # ending would otherwise steal passives: गम्यते → "locative of
        # गम्यत" — a fake noun that makes the sentence look verbless and
        # re-arms the "Sentence has no verb." false positive.
        if surface in self._passive_index:
            person, number, root_slp1 = self._passive_index[surface]
            return {
                'word': word,
                'pos': 'verb',
                'source': 'passive_table',
                # Gloss comes from the lexicon (see Layer 3).
                'meaning': self._lexicon_meaning(surface),
                'analysis': {
                    'root_slp1': root_slp1,
                    'tense': 'present',
                    'lakara': 'lat',
                    'voice': 'passive',
                    'person': person,
                    'number': number,
                },
            }

        # ── Layer 4: Noun analyzer ──────────────────────────────
        # Defensive guard (NOT a verb classifier): a word carrying an
        # unambiguous यक्-passive ending (यते/यन्ते/यसे/…) that no root in
        # PASSIVE_ROOT_STEMS matched (e.g. क्रियते, पीयते) must not be
        # accepted as a noun merely because its final matra matches a
        # declension. Fall through to Unknown instead, which keeps the
        # has_unknown guard from asserting "Sentence has no verb."
        # Genuine locatives that happen to end in य+े (भये, क्रये) are NOT
        # blocked, because bare "ये" is deliberately excluded below.
        if not re.search(r'(यते|यन्ते|यसे|येते|येथे|यध्वे|यावहे|यामहे)$', surface) \
                and self.noun_analyzer:
            try:
                # Every reading, not just the best: choosing between them is
                # what the attestation index below is for.
                readings = [
                    r for r in self.noun_analyzer.analyze(surface)
                    if r.get('method') == 'declension_rule'
                ]
                if readings:
                    reading = self._disambiguate(surface, readings)
                    stem = reading.get('stem', '')
                    if len(stem) >= 2:
                        if surface != clean:
                            reading.setdefault('resolved_from', surface)
                        return {
                            'word': word,
                            'pos': 'noun',
                            'source': 'noun_rule',
                            # The rule layers parse morphology but carry no
                            # gloss of their own. Ask the lexicon before
                            # claiming the word is not in the dictionary —
                            # for most nouns on disk, it very much is.
                            'meaning': (
                                self._lexicon_meaning(surface)
                                or 'unknown (not in dictionary)'
                            ),
                            'analysis': reading,
                        }
            except Exception:
                pass

        # ── Layer 5: full on-disk lexicon, then Unknown ─────────
        # Every analyser above failed to PARSE this token. That still does
        # not make it an unknown word: if a dictionary on disk contains it,
        # we do know what it is, and reporting `source: none` would tell the
        # user we cannot verify a word the project already holds — exactly
        # what the uncertainty contract forbids ("unknown = every layer
        # failed"). The dictionary counts as a layer, so it gets the final
        # say before Unknown.
        lexicon = self._lexicon_lookup(surface)
        if lexicon:
            pos = lexicon.get('pos', '')
            # The three verb layers ALL declined this token, so a dictionary
            # headword marked `verb` must not be promoted to `pos: verb`
            # here: agreement checking takes the FIRST verb in the sentence
            # and reads person/number from it. An unparsed token in that
            # slot would silently suppress the check on the sentence's real
            # verb, so an unparseable "verb" stays unknown instead.
            if pos == 'verb':
                pos = 'unknown'
            return {
                'word': word,
                'pos': pos or 'unknown',
                'source': 'dictionary',
                'meaning': lexicon.get('meaning', ''),
                # Deliberately no `meaning` inside `analysis`: the
                # motion-verb heuristic reads analysis['meaning'] and must
                # not take a lexicon gloss for evidence of motion.
                'analysis': {
                    'note': 'Resolved from the on-disk dictionary; '
                            'no morphological parse available',
                },
            }

        # Nothing recognised this spelling. Do not return Unknown yet — the
        # driver still has other spellings of the same token to try.
        return None

    # ==============================================================
    # Unknown-word (uncertainty) handling
    #
    # "Unknown" means NO layer could verify the word: it is absent from the
    # dictionary, neither verb analyser nor either paradigm table matched it,
    # and the noun declension analyser found no match. It is deliberately not
    # the same as "incorrect" — we must not invent a grammatical fault for a
    # form we failed to parse, nor silently treat it as correct.
    # ==============================================================
    UNKNOWN_STATUS = "Uncertain \u2014 Unable to Verify"
    # Points deducted per confirmed finding. Unchanged from the original
    # scoring; reused as the unit for the uncertainty adjustment below.
    CONFIRMED_ERROR_PENALTY = 15

    def _collect_unknown_words(self, breakdown: List[Dict]) -> List[Dict]:
        """Words the pipeline could not resolve, in sentence order.

        A word counts as unknown only when every layer failed. Any other
        `source` (dictionary, paninian, paradigm_table, passive_table,
        noun_rule) means some analyser did validate it, so it is NOT unknown
        even if another analyser would have rejected it.
        """
        return [
            b for b in breakdown
            if b.get('pos') == 'unknown' or b.get('source') == 'none'
        ]

    def _uncertainty_note(self, word: str) -> Tuple[str, str]:
        """Honest reason + suggestion for a word we could not verify.

        The wording reflects what the pipeline actually tried, and the
        suggestion is chosen from the word's shape rather than being generic.
        """
        clean = re.sub(r'[.,!?;।|]$', '', word).strip()
        if re.search(r'(यते|यन्ते|यसे|येते|येथे|यध्वे|यावहे|यामहे)$', clean):
            reason = (
                "The ending looks like a passive verb form, but no root in the "
                "passive table produced it, and it was deliberately not passed "
                "to the noun analyser because that would yield a false parse."
            )
            suggestion = (
                "Check the verb root and the spelling. Supplying a fuller "
                "sentence may let the form be identified."
            )
        elif len(clean) >= 9:
            reason = (
                "Not present in the dictionary, and not matched as a single "
                "verb or noun form. Longer forms are often compounds (samāsa) "
                "or the result of sound-joining (sandhi)."
            )
            suggestion = (
                "Try splitting the word into its parts, or re-check the "
                "spelling of each part."
            )
        else:
            reason = (
                "No analyser recognised it: it is not in the Sanskrit "
                "dictionary, the verb analysers and paradigm tables did not "
                "match it, and the noun declension analyser found no match."
            )
            suggestion = (
                "Check the spelling and verify whether this is a valid Sanskrit "
                "form. Adding more context may also help."
            )
        return reason, suggestion

    def _score_with_uncertainty(
        self,
        issues: List[Any],
        breakdown: List[Dict],
        base_score: int = 100,
        reported_score: Optional[int] = None,
    ) -> Tuple[int, Dict[str, Any], List[Dict], bool]:
        """Score a sentence, keeping confirmed errors and uncertainty apart.

        Confirmed findings keep the pre-existing unit (CONFIRMED_ERROR_PENALTY
        points each). Unknown words are charged on that same unit but weighted
        by the share of the sentence they represent, so a single unknown word
        in a long sentence costs less than one in a four-word sentence — the
        adjustment is derived from the existing scoring design rather than
        being an arbitrary fixed penalty.

        Guarantees:
          * uncertainty is never charged as a confirmed error;
          * a sentence containing any unknown word can never score 100;
          * a fully analysed, error-free sentence still scores 100.
        """
        unknown = self._collect_unknown_words(breakdown)
        total = max(1, len(breakdown))
        verified = len(breakdown) - len(unknown)

        confirmed_penalty = len(issues) * self.CONFIRMED_ERROR_PENALTY
        uncertainty_penalty = (
            int(math.ceil(self.CONFIRMED_ERROR_PENALTY * len(unknown) / total))
            if unknown else 0
        )

        if reported_score is not None:
            # AI mode supplies its own score; uncertainty still caps it.
            score = max(0, min(100, int(reported_score)) - uncertainty_penalty)
        else:
            score = max(0, base_score - confirmed_penalty - uncertainty_penalty)

        if unknown:
            score = min(score, 99)

        entries: List[Dict] = []
        for b in unknown:
            reason, suggestion = self._uncertainty_note(b.get('word', ''))
            entries.append({
                'word': b.get('word', ''),
                'status': self.UNKNOWN_STATUS,
                'reason': reason,
                'suggestion': suggestion,
            })

        info = {
            'confirmed_errors': len(issues),
            'confirmed_penalty': confirmed_penalty,
            'unknown_words': len(unknown),
            'uncertainty_penalty': uncertainty_penalty,
            'verified_words': verified,
            'verification_coverage': round(verified / total, 4),
        }
        return score, info, entries, bool(unknown)

    # ==============================================================
    # Sentence-level helpers
    # ==============================================================
    @staticmethod
    def _normalize_agreement_value(value: Any, aliases: Dict[str, str]) -> str:
        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                return ""
            # One value repeated (Prakriya emits one entry per matching dhātu)
            # is not ambiguity — accept it. Distinct values stay undecidable.
            if len(value) > 1 and all(item == value[0] for item in value):
                value = value[0]
            else:
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
          0. Passive voice (voice == 'passive') — passive paradigm ONLY.
             The active PARADIGM_TABLE (step 2) and the active suffix
             stripping (step 3) would silently emit an ACTIVE form (e.g.
             गच्छन्ति) for a passive verb, changing the sentence's voice.
             We therefore resolve passives against the passive paradigm
             and stop; if no passive form is known we return None rather
             than fall through to an active generator.
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

        # ── 0. Passive voice — never suggest an active-voice form ──
        if str(analysis.get('voice', '')).lower() == 'passive':
            root_slp1 = analysis.get('root_slp1') or ''
            paradigm = self._passive_paradigm.get(root_slp1)
            if not paradigm:
                # Unknown passive root — no safe suggestion exists.
                return None
            return paradigm.get(person, {}).get(number)

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

    def _destination_errors(self, breakdown: List[Dict]) -> List[Dict]:
        """Non-pronoun nominative nominals that a motion verb must govern.

        The check used to know exactly two words — विद्यालय and ग्राम — so the
        identical error with any other stem went unreported. What the rule
        actually says is linguistic, not lexical: a motion verb in the first
        person takes its goal in द्वितीया, so a nominal standing in the
        nominative cannot be that goal.

        Guards, each needed to keep this off correct sentences:
          * motion verb only (root gam, or glossed "go");
          * first person only, exactly as before — and a first-person nominal
            is always a pronoun (अहं, वयम्, …), which the `pos != 'noun'`
            test below skips, so the subject never flags itself;
          * neuter and म्-final tokens are skipped: a neuter a-stem spells
            its nominative and accusative the same way (गृहम्, वनम् — the
            curated entries even disagree about which one those are), so
            there the two cases genuinely cannot be told apart;
          * nominative only — anything already accusative or otherwise
            marked is left alone.

        The flagged list feeds BOTH the issue text and the correction, so the
        two can never disagree about what was wrong.
        """
        has_motion = False
        for b in breakdown:
            if b['pos'] != 'verb':
                continue
            a = b.get('analysis') or {}
            if str(a.get('root_slp1', '')).lower().startswith('gam'):
                has_motion = True
                break
            if 'go' in str(a.get('meaning', '')).lower():
                has_motion = True
                break
        if not has_motion:
            return []

        if not any(
            b['pos'] in ('noun', 'pronoun')
            and str((b.get('analysis') or {}).get('person', '')).lower() == 'first'
            for b in breakdown
        ):
            return []

        # The agreement subject is the first nominative, and a pronoun is
        # never a goal: neither may be accused of a missing द्वितीया.
        first_subject = next(
            (b for b in breakdown
             if b['pos'] in ('noun', 'pronoun')
             and str((b.get('analysis') or {}).get('case', '')).lower() == 'nominative'),
            None,
        )

        flagged = []
        for b in breakdown:
            if b['pos'] != 'noun':
                continue
            if first_subject is not None and b is first_subject:
                continue
            a = b.get('analysis') or {}
            if str(a.get('case', '')).lower() != 'nominative':
                continue
            gender = str(a.get('gender', '')).lower()
            surface = re.sub(r'[।॥.,!?;|]+$', '', str(b.get('word', '')))
            if gender == 'neuter':
                continue
            # A curated entry carries no `stem` at all, and a gender it does
            # not record on a म्-final token leaves the nominative/accusative
            # homograph undecidable — so only a bare म्/ं spelling, where we
            # genuinely cannot tell द्वितीया from कर्ता, is left alone.
            if not gender and surface.endswith(('म्', 'ं')):
                continue
            stem = str(a.get('stem', ''))
            # The stem-length guard only ever meant to reject a degenerate
            # declension parse (over-stripping). Dictionary hits have no stem
            # to test, and their gender/case are curated — those must pass.
            if stem and len(stem) < 2:
                continue
            flagged.append(b)
        return flagged

    def _destination_accusative(self, flagged: Dict) -> Optional[str]:
        """Accusative of `flagged`, generated from the declension table.

        None rather than a guess when the paradigm carries no such cell or
        the reading left the number undecidable — the issue can still be
        reported; the rewrite simply is not offered.
        """
        if not self.noun_analyzer:
            return None
        a = flagged.get('analysis') or {}
        number = str(a.get('number', '')).strip()
        if not number:
            return None
        return self.noun_analyzer.accusative_form(
            str(a.get('stem', '')),
            str(a.get('pattern', '')),
            number,
        )

    def _fix_destination_accusative(self, sentence: str,
                                    flagged: List[Dict]) -> str:
        """Rewrite each flagged destination into its accusative.

        The replacement is generated from stem + paradigm + number by
        `_destination_accusative`, not read off a table of individual words,
        so any noun the rule fires on is handled (नायकः → नायकम्,
        सिंहः → सिंहम्) rather than only the two stems that used to be
        hardcoded here. Only whole tokens are ever replaced, so a word that
        merely contains the stem as a substring is untouched.
        """
        accusative_map: Dict[str, str] = {}
        for b in flagged:
            old = re.sub(r'[।॥.,!?;|]+$', '', str(b.get('word', ''))).strip()
            new = self._destination_accusative(b)
            if old and new and old != new:
                accusative_map[old] = new
        if not accusative_map:
            return sentence
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

        # 0. Stray mid-sentence comma. Sanskrit prose is punctuated with the
        # danda (।), not commas, and the rest of the pipeline ignored a comma
        # entirely — so inserting one mid-sentence still scored as "correct".
        # Flag any comma (Devanagari , or Latin ,) that is not immediately
        # followed by the closing danda/pipe/period.
        for m in re.finditer(r'[,,]', text):
            if not re.match(r'\s*[।|.]', text[m.end():]):
                issues.append(
                    "Unnecessary comma mid-sentence — remove it "
                    "(Sanskrit uses the danda । to punctuate)."
                )
                corrections.append({'type': 'remove_comma', 'old': m.group()})
                break

        # 1. Punctuation
        if not text.strip().endswith(('।', '|', '.')):
            issues.append("Sentence must end with a Purna Virama (।)")

        # 2. Missing verb
        # Only assert "no verb" when every word was resolved AND the sentence
        # has no nominative to serve as the other half of a nominal sentence.
        # If some word is still unknown (e.g. a verb outside the
        # dictionary/paradigm coverage), there is no evidence that the sentence
        # lacks a verb, so reporting one would fabricate an error on input we
        # could not parse. And Sanskrit freely builds sentences with no verb at
        # all — रामः राजा।, सीता सुन्दरी। — where the noun in the nominative
        # IS the predicate, so "no verb" is only a defect when there is no
        # nominative either.
        has_verb = any(b['pos'] == 'verb' for b in breakdown)
        has_unknown = any(b['pos'] == 'unknown' for b in breakdown)
        has_nominative = any(
            b['pos'] in ('noun', 'pronoun')
            and str(b['analysis'].get('case', '')).lower() == 'nominative'
            for b in breakdown
        )
        if breakdown and not has_verb and not has_unknown and not has_nominative:
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
        flagged_destination = self._destination_errors(breakdown)
        for b in flagged_destination:
            issues.append(
                f"Destination '{b.get('word', '')}' should be in Accusative "
                f"Case (Dvitiya Vibhakti)."
            )

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

        # 2. Destination accusative fix (whole-token replacement).
        # The same list that produced the issue produces the rewrite, so a
        # token is never rewritten for a fault that was not reported (or
        # vice versa).
        flagged_destination = self._destination_errors(breakdown)
        if flagged_destination:
            corrected = self._fix_destination_accusative(corrected,
                                                         flagged_destination)

        # 3. Punctuation
        # 3b. Strip stray mid-sentence commas flagged above.
        if any(c.get('type') == 'remove_comma' for c in corrections):
            corrected = re.sub(
                r'\s*,(?=\s*[^\s।|.])|,(?=[^\s।|.\d])',
                '',
                corrected,
            )
            corrected = re.sub(r'\s*,\s*$', '', corrected)
            corrected = re.sub(r'\s{2,}', ' ', corrected)
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
        if use_ai:
            if not self.api_key:
                # This used to fall through silently, so pressing "AI Scan" with
                # no credential returned a rule-based analysis that looked like
                # a successful AI run. Say so instead.
                return self._degrade(
                    text,
                    "No AI key configured (set XAI_API_KEY in backend/.env).",
                    "no key",
                )
            return self.analyze_with_grok(text)

        normalized = text.replace('|', '।').replace('.', '।')
        words = self.tokenize(normalized)
        sanskrit_words = [w for w in words if re.match(r'[\u0900-\u097F]+', w)]

        if len(sanskrit_words) < 1:
            # Distinguish "you sent nothing" from "you sent text that contains
            # no Devanagari at all", so the message tells the user what to
            # change instead of claiming they sent nothing.
            if not text or not text.strip():
                return {"error": "Please enter some text to analyze"}
            return {
                "error": (
                    "No Devanagari characters were found in the input. The "
                    "grammar checker analyses Sanskrit written in Devanagari "
                    "script, e.g. \u0930\u093e\u092e\u0903 \u0935\u0928\u0902 "
                    "\u0917\u091a\u094d\u091b\u0924\u093f\u0964"
                )
            }

        # Word-by-word classification
        breakdown = [self._classify_word(w) for w in sanskrit_words]

        # Sentence-level checks
        issues, corrections = self._run_checks(text, breakdown)

        # Score. Confirmed findings keep the original 15-point unit; words the
        # pipeline could not verify add a separate, proportional adjustment so
        # an unverified sentence can never be reported as fully correct.
        score, score_info, unknown_words, partially_verified = (
            self._score_with_uncertainty(issues, breakdown, base_score=100)
        )

        # Keep grammar analysis independent of translation pipelines.
        translation = ""

        # Corrected sentence
        corrected = self._build_correction(text, breakdown, issues, corrections)
        correction_summary = (
            "Corrected sentence structure." if issues else "No errors found."
        )
        # Never claim "no errors found" when part of the sentence was never
        # analysed — that would present an unverified sentence as confirmed.
        if partially_verified:
            correction_summary = (
                f"Partially verified \u2014 {len(unknown_words)} word"
                f"{'s' if len(unknown_words) != 1 else ''} could not be analysed."
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
            # Uncertainty contract, consumed by the Grammar Checker UI.
            "unknown_words": unknown_words,
            "partially_verified": partially_verified,
            "score_breakdown": score_info,
        }

    # ==============================================================
    # AI fallback
    # ==============================================================
    def _provider_error(self, response) -> str:
        """Render a provider failure body as a short, printable reason.

        The old code logged only `response.status_code`, which threw away the
        body — the only part that says WHY a call failed (bad key, retired
        model, quota exceeded). A bare `400` looks identical in every one of
        those cases, which is why this stayed undiagnosable: the payload and
        the model name were both blamed when the credential was the problem.
        """
        try:
            payload = response.json()
        except Exception:
            payload = None

        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                message = str(err.get("message") or "").strip()
                code = str(err.get("code") or "").strip()
                if message and code:
                    return f"{message} [{code}]"
                if message:
                    return message
                if code:
                    return code
            elif isinstance(err, str) and err.strip():
                return err.strip()
            for key in ("message", "detail", "code"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        return (getattr(response, "text", "") or "").strip()[:300] or "no error body"

    @staticmethod
    def _looks_like_model_error(response) -> bool:
        """Distinguish 'you asked for a model we don't serve' from auth/quota.

        Deliberately narrow: an invalid credential returns 400 with
        "Incorrect API key provided", and retrying with a different model after
        that would only add a pointless second request on top of the real
        failure.
        """
        if getattr(response, "status_code", 0) == 404:
            return True
        body = (getattr(response, "text", "") or "").lower()
        return any(
            marker in body
            for marker in (
                "model not found", "does not exist", "unknown model",
                "invalid model", "no such model", "model_decommissioned",
                "decommissioned model", "is not supported",
            )
        )

    def _discover_model(self) -> str:
        """Ask GET /models for an id this credential can actually call."""
        if self._discovered_model is not None:
            return self._discovered_model
        self._discovered_model = ""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=20,
            )
            if response.status_code != 200:
                return ""
            data = response.json()
            ids = [
                str(m.get("id"))
                for m in (data.get("data") or [])
                if isinstance(m, dict) and m.get("id")
            ]
            if self.ai_model in ids:
                self._discovered_model = self.ai_model
                return self.ai_model
            preferred = [
                mid for mid in ids
                if any(t in mid.lower() for t in ("grok-4", "grok-3", "gpt-oss", "llama"))
            ]
            chosen = (preferred or ids or [""])[0]
            self._discovered_model = chosen
            return chosen
        except Exception as exc:
            print(f"SanskritNLP: model discovery failed: {exc}")
            return ""

    def _degrade(self, text: str, reason: str, label: str) -> Dict[str, Any]:
        """Fall back to rule-based analysis AND carry the reason across.

        `ai_error` is intentionally not `error`: main.py treats a top-level
        `error` as a rejected request and returns HTTP 400, whereas a provider
        outage should still return a usable rule-based analysis.
        """
        self.last_ai_error = reason
        print(f"SanskritNLP: AI unavailable ({label}) -> {reason}")
        result = self.analyze_text(text, mode="Local Fallback", use_ai=False)
        if isinstance(result, dict):
            result["ai_verified"] = False
            result["ai_error"] = reason
        return result

    def analyze_with_grok(self, text: str) -> Dict[str, Any]:
        print(f"SanskritNLP: AI grammar analysis using {self.ai_provider}")
        try:
            prompt = f"""
            Task: You are an expert Sanskrit grammarian and Pāṇini scholar. Analyze: "{text}"

            Rules:
            - "score" is an INTEGER on a 0-100 scale, where 100 means the sentence is
              fully grammatical and 0 means it is completely ungrammatical. Never use
              a 0-1 scale, a percentage fraction, or a pass/fail marker.
            - If the sentence is already grammatical, return an empty "issues" list,
              set "score" to 100, and set "corrected_sentence" equal to the input.
            - Do NOT rewrite a correctly formed passive construction into an active
              one. Only suggest a change of voice when the original voice itself is
              ungrammatical; when in doubt, preserve the original voice.
            - Report only issues you are confident about.

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
                     "content": (
                         "You are an expert Sanskrit grammarian. Output valid JSON only. "
                         "The 'score' field is an integer on a 0-100 scale. Preserve a "
                         "correctly formed passive construction in its original voice."
                     )},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            }
            url = f"{self.base_url}/chat/completions"
            response = requests.post(
                url, headers=headers, json=payload, timeout=30,
            )

            # Model-name drift is a different failure from a bad credential, so
            # it is the only case worth a second attempt: resolve an id this key
            # is actually served and retry once.
            if response.status_code != 200 and self._looks_like_model_error(response):
                discovered = self._discover_model()
                if discovered and discovered != payload["model"]:
                    print(
                        f"SanskritNLP: {payload['model']!r} not served; "
                        f"retrying with {discovered!r}"
                    )
                    payload["model"] = discovered
                    response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                reason = f"HTTP {response.status_code}: {self._provider_error(response)}"
                return self._degrade(text, reason, self.ai_provider)

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

            # The prompt asks for an integer on the 0-100 scale, but the model can
            # still emit a fraction, a string, or an out-of-range number. Normalise
            # it here so the stored score always honours the documented contract
            # instead of being passed through verbatim.
            raw_score = analysis_json.get("score")
            try:
                score_value = int(round(float(raw_score)))
            except (TypeError, ValueError):
                score_value = max(0, 100 - len(issues) * 15)
            analysis_json["score"] = max(0, min(100, score_value))
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

            # The AI supplies its own score and its own findings, so confirmed
            # errors are NOT re-charged here (that would double-count). The
            # uncertainty contract still applies, and only to what the model
            # itself flagged as unresolvable — nothing is invented.
            ai_breakdown = [b for b in breakdown if isinstance(b, dict)]
            ai_score, ai_info, ai_unknown, ai_partial = (
                self._score_with_uncertainty(
                    issues, ai_breakdown,
                    reported_score=int(analysis_json["score"]),
                )
            )
            analysis_json["score"] = ai_score
            analysis_json["score_breakdown"] = ai_info
            analysis_json["unknown_words"] = ai_unknown
            analysis_json["partially_verified"] = ai_partial
            if ai_partial:
                analysis_json["correction_summary"] = (
                    f"Partially verified \u2014 {len(ai_unknown)} word"
                    f"{'s' if len(ai_unknown) != 1 else ''} could not be analysed."
                )
            return analysis_json

        except Exception as e:
            # Network failure, malformed model output, JSON parse error — all
            # degrade the same way, but the reason is still carried out so the
            # caller can show it rather than a bare "rule-based" label.
            return self._degrade(text, f"{type(e).__name__}: {e}", "exception")

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