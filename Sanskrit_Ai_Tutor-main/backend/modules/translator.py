
"""
Enhanced Translator for SanskritaAI with Dynamic Dataset and Sentence Generation.
Includes local NLLB model translation, API fallback, and automatic database expansion.
"""

import os
import json
import random
import re
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

# Local NLLB model is optional: importing torch/transformers at startup is
# slow and the packages may be absent. Resolve lazily on first use so the
# API starts fast and dictionary/API translation keeps working regardless.
_local_translator_instance = None
_LOCAL_MODEL_LOAD_ATTEMPTED = False

def _get_local_translator():
    """Return the local NLLB translator, loading it on first use."""
    global _local_translator_instance, _LOCAL_MODEL_LOAD_ATTEMPTED
    if _local_translator_instance is not None:
        return _local_translator_instance
    if _LOCAL_MODEL_LOAD_ATTEMPTED:
        return None
    _LOCAL_MODEL_LOAD_ATTEMPTED = True
    try:
        from modules.local_translator import local_translator as instance
        _local_translator_instance = instance
        return instance
    except FileNotFoundError:
        print("Local translation model not found (adapter directories missing); continuing without it.")
        return None
    except Exception as exc:
        print(f"Local translation model unavailable ({type(exc).__name__}); continuing without it.")
        return None

# Try to import Google Translator.
try:
    from deep_translator import GoogleTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    DEEP_TRANSLATOR_AVAILABLE = False
    print("deep-translator not installed. Run: pip install deep-translator")

# Load environment variables explicitly from backend folder.
env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".env",
)
load_dotenv(dotenv_path=env_path)


class SanskritTranslator:

    # Ollama Cloud keys are `<32 hex>.<token>` — a shape no other supported
    # provider uses, so a key pasted into the wrong variable still routes
    # correctly. Kept in sync with SanskritNLP.OLLAMA_KEY_SHAPE.
    _OLLAMA_KEY_SHAPE = re.compile(r'^[0-9a-f]{32}\.')

    def __init__(
        self,
        csv_path="data/sanskrit_words.csv",
        sentences_path="data/sanskrit_sentences.json",
    ):
        # Resolve paths relative to the backend root.
        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        self.csv_path = os.path.join(base_dir, csv_path)
        self.sentences_path = os.path.join(base_dir, sentences_path)
        self.main_db_path = os.path.join(
            base_dir, "data", "sanskrit_translation_db.csv"
        )

        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.sentences_path), exist_ok=True)

        self.main_df = self.load_main_db()
        self.new_words_df = self.load_data()

        # Merge both dictionaries into memory.
        if not self.main_df.empty and not self.new_words_df.empty:
            self.df = pd.concat(
                [self.main_df, self.new_words_df],
                ignore_index=True,
            )
        elif not self.main_df.empty:
            self.df = self.main_df
        else:
            self.df = self.new_words_df

        self.sentences = self.load_sentences()
        self.api_calls_today = 0
        self.max_api_calls = 100

        # AI configuration.
        #
        # Routing mirrors SanskritNLP exactly (see modules/nlp_processor.py) so
        # both AI features come up on whatever provider is actually configured,
        # instead of the translator silently using a different — and, until now,
        # retired — one.
        ollama_key = (os.getenv("OLLAMA_API_KEY") or "").strip()
        legacy_key = (os.getenv("XAI_API_KEY") or "").strip()
        self.api_key = ollama_key or legacy_key
        self.base_url = os.getenv("BASE_URL")
        self.ai_provider = "Local"
        self.ai_model = "None"

        if self.api_key and isinstance(self.api_key, str):
            if ollama_key or self._OLLAMA_KEY_SHAPE.match(self.api_key):
                self.ai_provider = "Ollama Cloud"
                self.base_url = "https://ollama.com/v1"
                self.ai_model = os.getenv("AI_MODEL") or "gemma4:31b-cloud"
            elif self.api_key.startswith("gsk_"):
                self.ai_provider = "Groq"
                self.base_url = "https://api.groq.com/openai/v1"
                self.ai_model = "llama-3.3-70b-versatile"
            else:
                self.ai_provider = "Grok"
                self.base_url = self.base_url or "https://api.x.ai/v1"
                # xAI retired `grok-beta`, so hardcoding it meant even a VALID
                # key came back 400/404 and translation fell back to the local
                # database with no visible reason. Override with AI_MODEL.
                self.ai_model = os.getenv("AI_MODEL") or "grok-4-fast"

            print(
                f"✅ SanskritTranslator: AI Engine initialized "
                f"({self.ai_provider})"
            )
        else:
            print(
                "⚠️ SanskritTranslator: AI Engine key NOT found. "
                "Local database and model translation are available."
            )

    # ---------------------------------------------------------
    # LOCAL MODEL AND SAVED SENTENCE LOOKUP
    # ---------------------------------------------------------

    def _find_saved_sentence(
        self,
        text: str,
        direction: str,
    ) -> Optional[Dict]:
        """Find an exact sentence match in the saved sentence dataset."""

        query = text.strip().rstrip("।.!?").casefold()

        for sentence in self.sentences.get("sentences", []):
            if direction == "en_to_sa":
                candidate = str(
                    sentence.get("translation", "")
                ).strip()
            else:
                candidate = str(
                    sentence.get("devanagari")
                    or sentence.get("sanskrit", "")
                ).strip()

            if candidate.rstrip("।.!?").casefold() == query:
                sanskrit = str(
                    sentence.get("sanskrit")
                    or sentence.get("devanagari", "")
                )
                devanagari = str(
                    sentence.get("devanagari") or sanskrit
                )
                english = str(sentence.get("translation", ""))

                return {
                    "sanskrit": sanskrit,
                    "devanagari": devanagari,
                    "english": english,
                    "pronunciation": sanskrit,
                    "word_type": "sentence",
                    "meanings": [english] if english else [],
                    "example": sanskrit,
                    "category": "saved-sentence",
                    "source": "database",
                }

        return None

    def _translate_locally(
        self,
        text: str,
        direction: str,
    ) -> Optional[Dict]:
        """Translate using the local NLLB adapter without external APIs."""

        translator = _get_local_translator()
        if translator is None:
            return None
        try:
            translated = translator.translate(text, direction)
        except Exception as exc:
            print(f"Local translation error: {exc}")
            return None

        if (
            not translated
            or translated.strip().casefold()
            == text.strip().casefold()
        ):
            return None

        is_sentence = len(text.split()) > 1 or len(text) > 25

        if direction == "en_to_sa":
            return {
                "sanskrit": translated,
                "devanagari": translated,
                "english": text,
                "pronunciation": "",
                "word_type": "sentence" if is_sentence else "unknown",
                "meanings": [translated],
                "example": "",
                "category": "local-model",
                "source": "local_model",
            }

        return {
            "sanskrit": text,
            "devanagari": text,
            "english": translated,
            "pronunciation": "",
            "word_type": "sentence" if is_sentence else "unknown",
            "meanings": [translated],
            "example": "",
            "category": "local-model",
            "source": "local_model",
        }

    # ---------------------------------------------------------
    # DATA LOADING
    # ---------------------------------------------------------

    def load_main_db(self):
        """Load the core Sanskrit dictionary."""

        try:
            if os.path.exists(self.main_db_path):
                df = pd.read_csv(
                    self.main_db_path,
                    encoding="utf-8",
                )
                df = df.fillna("")

                mapping = {
                    "sanskrit_word": "sanskrit",
                    "pos": "word_type",
                    "example_meaning": "meaning",
                }
                df = df.rename(columns=mapping)

                if "pronunciation" not in df.columns:
                    df["pronunciation"] = df.get("sanskrit", "")

                if "source" not in df.columns:
                    df["source"] = "translation_db"

                if "tags" not in df.columns:
                    df["tags"] = "database"

                for col in df.columns:
                    df[col] = df[col].astype(str)

                print(
                    f"✅ Loaded {len(df)} core Sanskrit words "
                    "from main dictionary"
                )
                return df

            return pd.DataFrame()

        except Exception as exc:
            print(f"Error loading main DB: {exc}")
            return pd.DataFrame()

    def load_data(self):
        """Load user/API-translated words from CSV."""

        try:
            if os.path.exists(self.csv_path):
                df = pd.read_csv(
                    self.csv_path,
                    encoding="utf-8",
                )
                df = df.fillna("")

                required_columns = [
                    "sanskrit",
                    "devanagari",
                    "english",
                    "pronunciation",
                    "word_type",
                    "meaning",
                    "example",
                    "category",
                    "tags",
                    "source",
                ]

                for col in required_columns:
                    if col not in df.columns:
                        df[col] = ""

                for col in required_columns:
                    df[col] = df[col].astype(str)

                print(
                    f"✅ Loaded {len(df)} newly learned Sanskrit words "
                    f"from {self.csv_path}"
                )
                return df

            print(
                f"CSV file not found at {self.csv_path}. "
                "Creating demo data."
            )
            return self.create_demo_data()

        except Exception as exc:
            print(f"Error loading CSV: {exc}")
            return self.create_demo_data()

    def load_sentences(self):
        """Load sentences from JSON or create the default dataset."""

        try:
            if os.path.exists(self.sentences_path):
                with open(
                    self.sentences_path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    return json.load(file)

            default_sentences = {
                "sentences": self.generate_default_sentences(),
                "patterns": self.generate_patterns(),
            }
            self.save_sentences(default_sentences)
            return default_sentences

        except Exception as exc:
            print(f"Error loading sentences: {exc}")
            return {"sentences": [], "patterns": []}

    def generate_default_sentences(self):
        """Generate default sentence examples."""

        return [
            {
                "id": 1,
                "sanskrit": "रामः वनं गच्छति।",
                "devanagari": "रामः वनं गच्छति।",
                "translation": "Rama goes to the forest.",
                "words": ["रामः", "वनं", "गच्छति"],
                "pattern": "Subject Object Verb",
                "difficulty": "beginner",
                "tags": ["action", "movement"],
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": 2,
                "sanskrit": "सीता फलं खादति।",
                "devanagari": "सीता फलं खादति।",
                "translation": "Sita eats fruit.",
                "words": ["सीता", "फलं", "खादति"],
                "pattern": "Subject Object Verb",
                "difficulty": "beginner",
                "tags": ["action", "eating"],
                "created_at": datetime.now().isoformat(),
            },
        ]

    def generate_patterns(self):
        """Generate sentence patterns."""

        return [
            {
                "pattern": "Subject Object Verb",
                "template": "{subject} {object} {verb}।",
                "examples": [
                    "रामः वनं गच्छति।",
                    "सीता फलं खादति।",
                ],
            },
            {
                "pattern": "Subject Verb",
                "template": "{subject} {verb}।",
                "examples": [
                    "सीता अस्ति।",
                    "वर्षा भवति।",
                ],
            },
        ]

    def create_demo_data(self):
        """Create demo dictionary data."""

        data = {
            "sanskrit": [
                "agniḥ", "jalaṃ", "vāyuḥ", "bhūmiḥ",
                "sūryaḥ", "candraḥ", "putraḥ", "phalam",
                "granthaḥ", "gacchati", "asti", "khādati",
            ],
            "devanagari": [
                "अग्निः", "जलं", "वायुः", "भूमिः",
                "सूर्यः", "चन्द्रः", "पुत्रः", "फलम्",
                "ग्रन्थः", "गच्छति", "अस्ति", "खादति",
            ],
            "english": [
                "fire", "water", "air", "earth", "sun", "moon",
                "son", "fruit", "book", "goes", "is", "eats",
            ],
            "pronunciation": [
                "agniḥ", "jalam", "vāyuḥ", "bhūmiḥ",
                "sūryaḥ", "candraḥ", "putraḥ", "phalam",
                "granthaḥ", "gacchati", "asti", "khādati",
            ],
            "word_type": [
                "noun", "noun", "noun", "noun", "noun", "noun",
                "noun", "noun", "noun", "verb", "verb", "verb",
            ],
            "meaning": [
                "fire; heat", "water; fluid", "air; wind",
                "earth; ground", "sun", "moon", "son; child",
                "fruit", "book; text", "to go; to move",
                "to be; exists", "to eat",
            ],
            "example": [
                "अग्निः उष्णः अस्ति।",
                "जलं शीतलं अस्ति।",
                "वायुः वहति।",
                "भूमिः स्थिरा अस्ति।",
                "सूर्यः उदेति।",
                "चन्द्रः शोभते।",
                "पुत्रः पठति।",
                "फलं मधुरम् अस्ति।",
                "ग्रन्थः विशालः अस्ति।",
                "रामः गच्छति।",
                "सीता अस्ति।",
                "बालः खादति।",
            ],
            "category": [
                "elements", "elements", "elements", "elements",
                "celestial", "celestial", "family", "food",
                "objects", "actions", "actions", "actions",
            ],
            "tags": [
                "basic,fire", "basic,water", "basic,air",
                "basic,earth", "sun,celestial", "moon,celestial",
                "family,people", "food,fruit", "education,objects",
                "verb,movement", "verb,existence", "verb,eating",
            ],
            "source": ["database"] * 12,
        }

        return pd.DataFrame(data)

    def save_sentences(self, sentences_data=None):
        """Save sentence data to JSON."""

        if sentences_data is None:
            sentences_data = self.sentences

        os.makedirs(
            os.path.dirname(self.sentences_path),
            exist_ok=True,
        )

        with open(
            self.sentences_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                sentences_data,
                file,
                ensure_ascii=False,
                indent=2,
            )

    # ---------------------------------------------------------
    # EXTERNAL TRANSLATION PROVIDERS
    # ---------------------------------------------------------

    def translate_with_deep_translator(
        self,
        text,
        source="en",
        target="sa",
    ):
        """Translate using deep-translator GoogleTranslator."""

        if not DEEP_TRANSLATOR_AVAILABLE:
            return None

        try:
            translator = GoogleTranslator(
                source=source,
                target=target,
            )
            translation = translator.translate(text)

            if translation and translation != text:
                is_sentence = " " in text.strip() or len(text) > 20
                meanings = (
                    [translation]
                    if is_sentence
                    else [f"Translation of {text}"]
                )

                return {
                    "sanskrit": translation if target == "sa" else text,
                    "devanagari": (
                        translation if target == "sa" else text
                    ),
                    "english": translation if target == "en" else text,
                    "pronunciation": translation,
                    "word_type": (
                        "sentence" if is_sentence else "noun"
                    ),
                    "meanings": meanings,
                    "example": "",
                    "category": "api-added",
                    "source": "google_api",
                }

        except Exception as exc:
            print(f"Deep translator error: {exc}")

        return None

    def translate_with_mymemory(
        self,
        text,
        source="en",
        target="sa",
    ):
        """Translate using the MyMemory Translation API."""

        try:
            url = "https://api.mymemory.translated.net/get"
            params = {
                "q": text,
                "langpair": f"{source}|{target}",
            }

            response = requests.get(
                url,
                params=params,
                timeout=10,
            )
            data = response.json()

            if (
                response.status_code == 200
                and data.get("responseStatus") == 200
            ):
                translation = data.get(
                    "responseData", {}
                ).get("translatedText", "")

                translation = (
                    translation.replace("&#39;", "'")
                    .replace("&quot;", '"')
                )

                if translation and translation != text:
                    is_sentence = (
                        " " in text.strip() or len(text) > 20
                    )
                    meanings = (
                        [translation]
                        if is_sentence
                        else [f"Translation of {text}"]
                    )

                    return {
                        "sanskrit": (
                            translation if target == "sa" else text
                        ),
                        "devanagari": (
                            translation if target == "sa" else text
                        ),
                        "english": (
                            translation if target == "en" else text
                        ),
                        "pronunciation": translation,
                        "word_type": (
                            "sentence" if is_sentence else "noun"
                        ),
                        "meanings": meanings,
                        "example": "",
                        "category": "api-added",
                        "source": "mymemory_api",
                    }

        except Exception as exc:
            print(f"MyMemory API error: {exc}")

        return None

    def translate_with_libretranslate(
        self,
        text,
        source="en",
        target="sa",
    ):
        """Translate using the LibreTranslate API."""

        try:
            url = "https://libretranslate.com/translate"
            payload = {
                "q": text,
                "source": source,
                "target": target,
                "format": "text",
            }

            response = requests.post(
                url,
                json=payload,
                timeout=10,
            )
            data = response.json()

            if (
                response.status_code == 200
                and "translatedText" in data
            ):
                translation = data["translatedText"]

                if translation and translation != text:
                    is_sentence = (
                        " " in text.strip() or len(text) > 20
                    )
                    meanings = (
                        [translation]
                        if is_sentence
                        else [f"Translation of {text}"]
                    )

                    return {
                        "sanskrit": (
                            translation if target == "sa" else text
                        ),
                        "devanagari": (
                            translation if target == "sa" else text
                        ),
                        "english": (
                            translation if target == "en" else text
                        ),
                        "pronunciation": translation,
                        "word_type": (
                            "sentence" if is_sentence else "noun"
                        ),
                        "meanings": meanings,
                        "example": "",
                        "category": "api-added",
                        "source": "libretranslate_api",
                    }

        except Exception as exc:
            print(f"LibreTranslate error: {exc}")

        return None

    def translate_with_ai(
        self,
        text,
        direction="en_to_sa",
    ):
        """Translate using the configured Ollama/Groq/xAI provider."""

        if not self.api_key:
            print("⚠️ No API key for AI translation")
            return None

        try:
            target_lang = (
                "Sanskrit (Devanagari)"
                if direction == "en_to_sa"
                else "English"
            )
            source_lang = (
                "English"
                if direction == "en_to_sa"
                else "Sanskrit (Devanagari)"
            )

            prompt = f"""
Translate the following {source_lang} text to {target_lang}.

Text: "{text}"

Return strictly a JSON object with these fields:
{{
    "sanskrit": "Sanskrit transliteration",
    "devanagari": "Sanskrit in Devanagari",
    "english": "English translation",
    "pronunciation": "pronunciation",
    "word_type": "sentence or part of speech",
    "meanings": ["meaning 1", "meaning 2"],
    "example": "example usage in Sanskrit"
}}
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.ai_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a professional Sanskrit-English "
                            "translator with deep knowledge of Vedic "
                            "and Classical Sanskrit."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=20,
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                json_match = re.search(
                    r"\{.*\}",
                    content,
                    re.DOTALL,
                )

                if json_match:
                    item = json.loads(json_match.group(0))
                    item["source"] = f"{self.ai_provider}_ai"
                    return item

            else:
                print(
                    f"AI API error: {response.status_code} - "
                    f"{response.text}"
                )

        except Exception as exc:
            print(f"AI Translation Error: {exc}")

        return None

    # ---------------------------------------------------------
    # DATABASE EXPANSION
    # ---------------------------------------------------------

    def save_to_database(self, word_data):
        """Save a new translation to CSV and update memory."""

        try:
            os.makedirs(
                os.path.dirname(self.csv_path),
                exist_ok=True,
            )

            existing = self.df[
                self.df["english"].astype(str).str.casefold()
                == str(word_data.get("english", "")).casefold()
            ]

            if not existing.empty:
                print(
                    f"Word '{word_data.get('english', '')}' "
                    "already exists, not saving."
                )
                return False

            new_row = pd.DataFrame(
                [{
                    "sanskrit": word_data.get("sanskrit", ""),
                    "devanagari": word_data.get("devanagari", ""),
                    "english": word_data.get("english", ""),
                    "pronunciation": word_data.get(
                        "pronunciation",
                        word_data.get("sanskrit", ""),
                    ),
                    "word_type": word_data.get("word_type", "noun"),
                    "meaning": "; ".join(
                        word_data.get(
                            "meanings",
                            [word_data.get("english", "")],
                        )
                    ),
                    "example": word_data.get("example", ""),
                    "category": word_data.get("category", "api-added"),
                    "tags": (
                        f"api,{word_data.get('source', 'unknown')}"
                    ),
                    "source": word_data.get("source", "api"),
                }]
            )

            self.df = pd.concat(
                [self.df, new_row],
                ignore_index=True,
            )
            self.new_words_df = pd.concat(
                [self.new_words_df, new_row],
                ignore_index=True,
            )

            self.new_words_df.to_csv(
                self.csv_path,
                index=False,
                encoding="utf-8",
            )

            print(
                f"✅ Saved new word '{word_data.get('english', '')}' "
                f"to {self.csv_path}"
            )

            self.generate_sentences_for_word(word_data)
            return True

        except Exception as exc:
            print(f"❌ Error saving to database: {exc}")
            return False

    def generate_sentences_for_word(self, word_data):
        """Generate basic example sentences for a new dictionary entry."""

        word = word_data.get("sanskrit", "")
        english = word_data.get("english", "")

        templates = [
            f"{word} अस्ति।",
            f"{word} गच्छति।",
            f"{word} पठति।",
        ]
        translations = [
            f"{english.title()} is.",
            f"{english.title()} goes.",
            f"{english.title()} reads.",
        ]

        new_sentences = []
        starting_id = len(
            self.sentences.get("sentences", [])
        ) + 1

        for i, (sans, trans) in enumerate(
            zip(templates, translations)
        ):
            new_sentences.append(
                {
                    "id": starting_id + i,
                    "sanskrit": sans,
                    "devanagari": sans,
                    "translation": trans,
                    "words": [word],
                    "pattern": "Subject Verb",
                    "difficulty": "beginner",
                    "tags": ["auto-generated", "api-added"],
                    "created_at": datetime.now().isoformat(),
                }
            )

        self.sentences.setdefault("sentences", []).extend(
            new_sentences
        )
        self.save_sentences()

        return new_sentences

    # ---------------------------------------------------------
    # ENGLISH TO SANSKRIT
    # ---------------------------------------------------------

    def English_to_sanskrit(
        self,
        English_word: str,
        use_api: bool = True,
    ) -> Dict:
        """Translate English to Sanskrit using DB, local model, then APIs."""

        English_word = English_word.strip()
        results = []

        # 1. Search the merged dictionary.
        for _, row in self.df.iterrows():
            row_english = str(
                row.get("english", "")
            ).strip().casefold()

            if (
                English_word.casefold() == row_english
                and row_english not in ("nan", "")
            ):
                meaning_val = row.get("meaning", "")
                meanings = (
                    str(meaning_val).split("; ")
                    if pd.notna(meaning_val) and str(meaning_val).strip()
                    else [str(row.get("english", ""))]
                )

                results.append(
                    {
                        "sanskrit": str(row.get("sanskrit", "")),
                        "devanagari": str(row.get("devanagari", "")),
                        "english": str(row.get("english", "")),
                        "pronunciation": str(
                            row.get("pronunciation", "")
                        ),
                        "word_type": str(row.get("word_type", "")),
                        "meanings": meanings,
                        "example": str(row.get("example", "")),
                        "category": str(row.get("category", "")),
                        "source": str(row.get("source", "database")),
                    }
                )

        if results:
            return {
                "source": "database",
                "results": results,
                "count": len(results),
            }

        # 2. Check saved sentences.
        saved_sentence = self._find_saved_sentence(
            English_word,
            "en_to_sa",
        )

        if saved_sentence:
            return {
                "source": "database",
                "results": [saved_sentence],
                "count": 1,
            }

        # 3. Branch by AI Engine toggle:
        #    - OFF (use_api=False) → fine-tuned local NLLB model
        #    - ON  (use_api=True)  → external AI/API providers
        if not use_api:
            # Local model path (AI Engine OFF)
            local_result = self._translate_locally(
                English_word,
                "en_to_sa",
            )

            if local_result:
                # Persist to registry so future lookups hit the dictionary
                self.save_to_database(local_result)
                local_result["source"] = "local_model (saved)"
                return {
                    "source": "database",
                    "results": [local_result],
                    "count": 1,
                }
        else:
            # External API path (AI Engine ON)
            print(
                f"🌐 Word '{English_word}' not in DB. "
                "Attempting AI/API translation..."
            )

            api_result = None

            if self.api_key:
                api_result = self.translate_with_ai(
                    English_word,
                    direction="en_to_sa",
                )

            if (
                not api_result
                and self.api_calls_today < self.max_api_calls
            ):
                if DEEP_TRANSLATOR_AVAILABLE:
                    api_result = self.translate_with_deep_translator(
                        English_word,
                        source="en",
                        target="sa",
                    )

                if not api_result:
                    api_result = self.translate_with_mymemory(
                        English_word,
                        source="en",
                        target="sa",
                    )

                if not api_result:
                    api_result = self.translate_with_libretranslate(
                        English_word,
                        source="en",
                        target="sa",
                    )

            if api_result:
                self.api_calls_today += 1

                api_result.setdefault("english", English_word)
                api_result.setdefault("sanskrit", English_word)
                api_result.setdefault("devanagari", English_word)
                api_result.setdefault("meanings", [English_word])

                saved = self.save_to_database(api_result)

                if saved:
                    api_result["source"] = (
                        f"{api_result.get('source', 'api')} (saved)"
                    )
                    return {
                        "source": "database",
                        "results": [api_result],
                        "count": 1,
                    }

                return {
                    "source": "api",
                    "results": [api_result],
                    "count": 1,
                }

            print(
                f"❌ No translation found for '{English_word}' "
                "from any source."
            )

        return {
            "source": "none",
            "results": [],
            "count": 0,
        }

    # ---------------------------------------------------------
    # SANSKRIT TO ENGLISH
    # ---------------------------------------------------------

    def sanskrit_to_English(
        self,
        sanskrit_word: str,
        use_api: bool = True,
    ) -> Dict:
        """Translate Sanskrit to English using DB, local model, then APIs."""

        sanskrit_word = sanskrit_word.strip()
        results = []

        # 1. Exact dictionary lookup: transliteration or Devanagari.
        for _, row in self.df.iterrows():
            s_val = str(
                row.get("sanskrit", "")
            ).strip().casefold()

            d_val = str(
                row.get("devanagari", "")
            ).strip()

            if (
                s_val not in ("nan", "")
                and (
                    sanskrit_word.casefold() == s_val
                    or sanskrit_word == d_val
                )
            ):
                meaning_val = row.get("meaning", "")
                meanings = (
                    str(meaning_val).split("; ")
                    if pd.notna(meaning_val) and str(meaning_val).strip()
                    else [str(row.get("english", ""))]
                )

                results.append(
                    {
                        "sanskrit": str(row.get("sanskrit", "")),
                        "devanagari": str(row.get("devanagari", "")),
                        "english": str(row.get("english", "")),
                        "pronunciation": str(
                            row.get("pronunciation", "")
                        ),
                        "word_type": str(row.get("word_type", "")),
                        "meanings": meanings,
                        "example": str(row.get("example", "")),
                        "category": str(row.get("category", "")),
                        "source": str(row.get("source", "database")),
                    }
                )

        if results:
            return {
                "source": "database",
                "results": results,
                "count": len(results),
            }

        # 2. Check saved Sanskrit sentences.
        saved_sentence = self._find_saved_sentence(
            sanskrit_word,
            "sa_to_en",
        )

        if saved_sentence:
            return {
                "source": "database",
                "results": [saved_sentence],
                "count": 1,
            }

        # 3. Branch by AI Engine toggle:
        #    - OFF (use_api=False) → fine-tuned local NLLB model
        #    - ON  (use_api=True)  → external AI/API providers
        if not use_api:
            # Local model path (AI Engine OFF)
            local_result = self._translate_locally(
                sanskrit_word,
                "sa_to_en",
            )

            if local_result:
                # Persist to registry so future lookups hit the dictionary
                self.save_to_database(local_result)
                local_result["source"] = "local_model (saved)"
                return {
                    "source": "database",
                    "results": [local_result],
                    "count": 1,
                }
        else:
            # External API path (AI Engine ON)
            print(
                f"🌐 Sanskrit text '{sanskrit_word}' not in DB. "
                "Attempting AI/API translation..."
            )

            api_result = None

            if self.api_key:
                api_result = self.translate_with_ai(
                    sanskrit_word,
                    direction="sa_to_en",
                )

            if (
                not api_result
                and self.api_calls_today < self.max_api_calls
            ):
                if DEEP_TRANSLATOR_AVAILABLE:
                    api_result = self.translate_with_deep_translator(
                        sanskrit_word,
                        source="sa",
                        target="en",
                    )

                if not api_result:
                    api_result = self.translate_with_mymemory(
                        sanskrit_word,
                        source="sa",
                        target="en",
                    )

                if not api_result:
                    api_result = self.translate_with_libretranslate(
                        sanskrit_word,
                        source="sa",
                        target="en",
                    )

            if api_result:
                self.api_calls_today += 1

                english_translation = api_result.get("english", "")

                if (
                    not english_translation
                    and api_result.get("meanings")
                ):
                    english_translation = api_result["meanings"][0]

                if (
                    str(english_translation).strip().casefold()
                    == sanskrit_word.casefold()
                ):
                    return {
                        "source": "none",
                        "results": [],
                        "count": 0,
                    }

                self.save_to_database(api_result)

                return {
                    "source": "api",
                    "results": [api_result],
                    "count": 1,
                }

        return {
            "source": "none",
            "results": [],
            "count": 0,
        }

    # ---------------------------------------------------------
    # SENTENCE AND DICTIONARY UTILITIES
    # ---------------------------------------------------------

    def get_meaning(self, word):
        """Get the first stored meaning of a Sanskrit word."""

        row = self.df[self.df["sanskrit"] == word]

        if not row.empty:
            return str(row.iloc[0]["meaning"]).split(";")[0]

        return word

    def auto_generate_sentences(
        self,
        count: int = 5,
    ) -> List[Dict]:
        """Generate example sentences from available dictionary words."""

        generated = []

        nouns = self.df[
            self.df["word_type"] == "noun"
        ]["sanskrit"].tolist()

        verbs = self.df[
            self.df["word_type"] == "verb"
        ]["sanskrit"].tolist()

        for i in range(count):
            if not nouns or not verbs:
                break

            subject = random.choice(nouns)
            verb = random.choice(verbs)
            obj = (
                random.choice(nouns)
                if random.random() > 0.3
                else None
            )

            if obj and obj != subject:
                sentence = f"{subject} {obj} {verb}।"
                pattern = "Subject Object Verb"
                words = [subject, obj, verb]
            else:
                sentence = f"{subject} {verb}।"
                pattern = "Subject Verb"
                words = [subject, verb]

            subject_meaning = self.get_meaning(subject)
            verb_meaning = self.get_meaning(verb).split()[0]
            obj_meaning = (
                self.get_meaning(obj).split()[0]
                if obj
                else ""
            )

            if obj:
                translation = (
                    f"{subject_meaning} {obj_meaning} "
                    f"{verb_meaning}s."
                )
            else:
                translation = (
                    f"{subject_meaning} {verb_meaning}s."
                )

            new_sentence = {
                "id": len(
                    self.sentences.get("sentences", [])
                ) + i + 1,
                "sanskrit": sentence,
                "devanagari": sentence,
                "translation": translation.capitalize(),
                "words": words,
                "pattern": pattern,
                "difficulty": "auto-generated",
                "tags": ["auto-generated"],
                "created_at": datetime.now().isoformat(),
            }

            generated.append(new_sentence)

        self.sentences.setdefault("sentences", []).extend(generated)
        self.save_sentences()

        return generated

    def get_random_sentence(self) -> Optional[Dict]:
        """Return a random sentence from the saved dataset."""

        sentences = self.sentences.get("sentences", [])

        if sentences:
            return random.choice(sentences)

        return None

    def get_database_stats(self) -> Dict:
        """Return dictionary and translation statistics."""

        source_series = (
            self.df["source"].astype(str)
            if "source" in self.df.columns
            else pd.Series("", index=self.df.index)
        )

        word_type_series = (
            self.df["word_type"].astype(str)
            if "word_type" in self.df.columns
            else pd.Series("", index=self.df.index)
        )

        return {
            "total_words": len(self.df),
            "database_words": int(
                (source_series == "database").sum()
            ),
            "api_words": int(
                source_series.str.contains(
                    "api",
                    case=False,
                    na=False,
                ).sum()
            ),
            "nouns": int(
                (word_type_series == "noun").sum()
            ),
            "verbs": int(
                (word_type_series == "verb").sum()
            ),
            "total_sentences": len(
                self.sentences.get("sentences", [])
            ),
            "api_calls_today": self.api_calls_today,
        }
