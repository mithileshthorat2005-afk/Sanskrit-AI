"""
Paninian Grammar Analyzer
-------------------------
A wrapper around the `prakriya` Sanskrit verb analyzer and generator.

Scope (deliberately limited):
- Devanagari → SLP1 via indic-transliteration.
- Uses Prakriya's documented get_info() API for analysis.
- Uses Prakriya's VerbFormGenerator for correction synthesis.
- Recognizes finite (tiṅanta) verb forms.
- Extracts: dhatu, lakara, purusha, vacana, gana, pada, suffix,
  derivation sutras.
- Generates correct verb forms for any root the generator knows.
- Does NOT do: subanta analysis, sandhi splitting, samasa, karaka,
  or syntactic parsing.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

# ─── Prakriya analyzer import ─────────────────────────────
try:
    from prakriya import Prakriya
    PRAKRIYA_AVAILABLE = True
except ImportError:
    PRAKRIYA_AVAILABLE = False

# ─── Prakriya verb-form generator import ──────────────────
# Prakriya renamed `Generate` to `VerbFormGenerator` in newer versions.
# Try both names so the code works on either.
GENERATOR_AVAILABLE = False
_GENERATOR_CLASS = None

try:
    from prakriya import VerbFormGenerator
    GENERATOR_AVAILABLE = True
    _GENERATOR_CLASS = VerbFormGenerator
except ImportError:
    try:
        from prakriya import Generate as _Generate
        GENERATOR_AVAILABLE = True
        _GENERATOR_CLASS = _Generate
    except ImportError:
        GENERATOR_AVAILABLE = False
        _GENERATOR_CLASS = None

# ─── Transliteration import ───────────────────────────────
try:
    from indic_transliteration import sanscript
    SANSCRIPT_AVAILABLE = True
except ImportError:
    SANSCRIPT_AVAILABLE = False


class PaninianAnalyzer:

    # Characters that can appear in Prakriya's `verb` field but are NOT
    # part of the SLP1 phonetic inventory. Safe to strip.
    _IT_MARKERS = ("x", "X", "~", "\\", "'", "^", "|", "#", "@", "!", "$", "%", "&", "*")

    # Map internal lakara codes to the generator's valid set.
    _LAKARA_TO_GENERATOR = {
        "law": "law",       # present
        "laG": "laN",       # past (laṅ)
        "laN": "laN",
        "lfw": "lfw",       # simple future (lṛṭ)
        "luw": "luw",       # periphrastic future (luṭ)
        "low": "low",       # imperative (loṭ)
        "loW": "low",
        "viDiliG": "viDiliN",
        "viDiliN": "viDiliN",
    }

    # Map our pipeline's person/number vocabulary to SLP1 for the generator.
    _PURUSHA_TO_GENERATOR = {
        "praTama": "praTama",
        "maDyama": "maDyama",
        "uttama": "uttama",
        "prathama": "praTama",
        "madhyama": "maDyama",
    }

    _VACHANA_TO_GENERATOR = {
        "eka": "eka",
        "dvi": "dvi",
        "bahu": "bahu",
    }

    # Roots for which the generator tends to produce causatives or other
    # wrong derivations. We refuse outputs containing these substrings.
    # Fallback to the paradigm table takes over in that case.
    _WEAK_FORMS = {
        "BU": ("भावय",),      # reject causative of भू
        "as": ("अस्या",),  # reject wrong derivation of अस् # reject wrong derivations of अस्
    }

    def __init__(self):
        self.prakriya: Optional[Any] = None
        self.generator: Optional[Any] = None
        self._init_error: Optional[str] = None

        # ── Initialize analyzer ───────────────────────────────
        if PRAKRIYA_AVAILABLE:
            try:
                self.prakriya = Prakriya()
                try:
                    self.prakriya.input_translit("slp1")
                    self.prakriya.output_translit("slp1")
                except Exception:
                    pass
                print("✅ Paninian Analyzer: Prakriya initialized")
            except Exception as exc:
                self._init_error = str(exc)
                print(f"⚠️ Prakriya init failed: {exc}")
        else:
            self._init_error = "prakriya not installed"
            print("⚠️ prakriya not installed")

        # ── Initialize generator ──────────────────────────────
        if GENERATOR_AVAILABLE and _GENERATOR_CLASS is not None:
            try:
                self.generator = _GENERATOR_CLASS()
                try:
                    self.generator.input_translit("slp1")
                    self.generator.output_translit("devanagari")
                except Exception:
                    pass
                print("✅ Paninian Analyzer: VerbFormGenerator initialized")
            except Exception as exc:
                print(f"⚠️ Paninian Analyzer: generator init failed: {exc}")
                self.generator = None
        else:
            print("⚠️ Paninian Analyzer: VerbFormGenerator not available")

        if not SANSCRIPT_AVAILABLE:
            print("⚠️ indic-transliteration not installed")

    # ─────────────────────────────────────────────────────────────
    # Normalization & transliteration
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFC", text)
        return (text.replace("\u200c", "")
                    .replace("\u200d", "")
                    .replace("\ufeff", "")
                    .strip())

    @staticmethod
    def _strip_punct(word: str) -> str:
        return word.strip("।॥|.,!?;:()[]{}\"'“”‘’").strip()

    def to_slp1(self, devanagari: str) -> str:
        text = self._normalize(devanagari)
        text = text.replace("।", "").replace("॥", "").replace("|", "").strip()
        if not text:
            return ""
        if not SANSCRIPT_AVAILABLE:
            raise RuntimeError("indic-transliteration is not installed")
        return sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.SLP1)

    def to_devanagari(self, slp1: str) -> str:
        if not slp1:
            return ""
        if not SANSCRIPT_AVAILABLE:
            raise RuntimeError("indic-transliteration is not installed")
        return sanscript.transliterate(slp1, sanscript.SLP1, sanscript.DEVANAGARI)

    # ─────────────────────────────────────────────────────────────
    # Prakriya field access (analyzer)
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _unwrap(value: Any) -> Any:
        if isinstance(value, list):
            if len(value) == 0:
                return None
            if len(value) == 1:
                return value[0]
            return value
        return value

    def _get_field(self, slp1_form: str, field: str) -> Any:
        if not self.prakriya:
            return None
        try:
            raw = self.prakriya.get_info(slp1_form, field)
            return self._unwrap(raw)
        except Exception:
            return None

    def _get_derivation(self, slp1_form: str) -> List[Dict[str, str]]:
        """Return flat list of {'sutra','sutra_num','form'} steps."""
        if not self.prakriya:
            return []
        try:
            raw = self.prakriya.get_info(slp1_form, "prakriya")
            if (isinstance(raw, list) and len(raw) == 1
                    and isinstance(raw[0], list)):
                raw = raw[0]
            if not isinstance(raw, list):
                return []
            steps = []
            for s in raw:
                if isinstance(s, dict):
                    steps.append({
                        "sutra":     str(s.get("sutra", "")),
                        "sutra_num": str(s.get("sutra_num", "")),
                        "form":      str(s.get("form", "")),
                    })
            return steps
        except Exception:
            return []

    # ─────────────────────────────────────────────────────────────
    # Root extraction
    # ─────────────────────────────────────────────────────────────
    @classmethod
    def _clean_root(cls, slp1_root: str) -> str:
        """
        Strip IT markers from a raw SLP1 root.
        The generator needs a clean root, not one with x/~ markers.
        """
        if not slp1_root:
            return ""
        s = str(slp1_root).strip()
        for marker in cls._IT_MARKERS:
            s = s.replace(marker, "")
        return s.strip()

    @classmethod
    def _extract_root(cls, derivation: List[Dict[str, str]], raw_verb: Any) -> str:
        """
        Extract the clean root.
        Take the form IMMEDIATELY BEFORE the first derivation step
        whose form contains '+' (before suffix attachment begins).
        """
        clean_root = ""
        for step in derivation:
            form = step.get("form", "")
            if "+" in form:
                break
            if form:
                clean_root = form

        if clean_root:
            return cls._clean_root(clean_root)

        # Fallback: strip IT markers from raw verb
        if raw_verb:
            return cls._clean_root(str(raw_verb))

        return ""

    # ─────────────────────────────────────────────────────────────
    # Verb analysis
    # ─────────────────────────────────────────────────────────────
    def analyze_verb_direct(self, slp1_form: str) -> Dict[str, Any]:
        slp1_form = self._normalize(slp1_form).strip()

        if not slp1_form:
            return {"is_verb": False, "error": "Empty input", "slp1_used": ""}

        if not self.prakriya:
            return {"is_verb": False,
                    "error": self._init_error or "Prakriya unavailable",
                    "slp1_used": slp1_form}

        raw_verb = self._get_field(slp1_form, "verb")
        derivation = self._get_derivation(slp1_form)

        # Gate 1: Prakriya must return a root
        if raw_verb is None:
            return {"is_verb": False,
                    "error": "Not a verb form (no root returned)",
                    "slp1_used": slp1_form}

        # Gate 2: derivation must end at the exact input form
        if derivation:
            final_form = derivation[-1].get("form", "")
            if final_form and final_form != slp1_form:
                return {"is_verb": False,
                        "error": f"Invalid verb form (derivation ended at '{final_form}')",
                        "slp1_used": slp1_form}

        root_slp1 = self._extract_root(derivation, raw_verb)
        root_deva = self.to_devanagari(root_slp1) if root_slp1 else ""

        rules_applied = [s["sutra_num"] for s in derivation if s.get("sutra_num")]

        return {
            "is_verb": True,
            "root": root_deva,
            "root_slp1": root_slp1,
            "raw_verb_with_markers": str(raw_verb),
            "meaning": self._get_field(slp1_form, "meaning"),
            "tense": self._get_field(slp1_form, "lakara"),
            "person": self._get_field(slp1_form, "purusha"),
            "number": self._get_field(slp1_form, "vachana"),
            "class": self._get_field(slp1_form, "gana"),
            "pada": self._get_field(slp1_form, "padadecider_id"),
            "suffix": self._get_field(slp1_form, "suffix"),
            "derivation": derivation,
            "rules_applied": rules_applied,
            "slp1_used": slp1_form,
        }

    def analyze_verb(self, dev_form: str) -> Dict[str, Any]:
        cleaned = self._strip_punct(self._normalize(dev_form))
        if not cleaned:
            return {"is_verb": False, "error": "Empty input"}

        try:
            slp1 = self.to_slp1(cleaned)
        except Exception as exc:
            return {"is_verb": False, "error": str(exc), "dev_input": cleaned}

        result = self.analyze_verb_direct(slp1)
        result["dev_input"] = cleaned
        return result

    # ─────────────────────────────────────────────────────────────
    # Sentence analysis
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def tokenize(text: str) -> List[str]:
        text = PaninianAnalyzer._normalize(text)
        return re.findall(r"[\u0900-\u097F]+", text)

    def analyze_sentence(self, text: str) -> Dict[str, Any]:
        tokens = self.tokenize(text)
        word_analyses = []
        has_verb = False
        verb_count = 0

        for token in tokens:
            result = self.analyze_verb(token)
            entry = {
                "surface": token,
                "is_verb": result.get("is_verb", False),
                "morphology": result if result.get("is_verb") else None,
            }
            if entry["is_verb"]:
                has_verb = True
                verb_count += 1
            word_analyses.append(entry)

        return {
            "text": text,
            "tokens": tokens,
            "word_analyses": word_analyses,
            "word_count": len(tokens),
            "verb_count": verb_count,
            "has_verb": has_verb,
            "prakriya_available": self.prakriya is not None,
        }

    # ─────────────────────────────────────────────────────────────
    # Verb-form generation (for correction)
    # ─────────────────────────────────────────────────────────────
    def generate_verb_form(
        self,
        root_slp1: str,
        lakara: str,
        purusha: str,
        vachana: str,
        raw_root_with_markers: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate the correct Devanagari form for a given root and features.

        Tries multiple root spellings, because Prakriya's generator expects
        the Dhatupatha canonical form (which may include IT markers).

        Resolution order of root candidates:
          1. raw_root_with_markers — Prakriya's own analyzer output, most authoritative
          2. root_slp1 — cleaned root from the caller
          3. variants — with/without trailing 'a'
        """
        if not self.generator:
            return None
        if not lakara or not purusha or not vachana:
            return None

        # ── Build ordered list of root candidates ──────────────
        candidates: List[str] = []

        # 1. Raw root with IT markers
        if raw_root_with_markers:
            raw = str(raw_root_with_markers).strip()
            if raw:
                candidates.append(raw)
                # also try with trailing marker characters stripped
                cleaned_step = raw.rstrip("~Xx")
                if cleaned_step and cleaned_step not in candidates:
                    candidates.append(cleaned_step)

        # 2. Clean root passed by the caller
        if root_slp1:
            cleaned = self._clean_root(str(root_slp1)).strip()
            if cleaned and cleaned not in candidates:
                candidates.append(cleaned)

            if cleaned:
                # 3. Variant: without trailing 'a'
                if cleaned.endswith("a") and len(cleaned) > 2:
                    variant = cleaned[:-1]
                    if variant not in candidates:
                        candidates.append(variant)
                # 4. Variant: with trailing 'a'
                variant = cleaned + "a"
                if variant not in candidates:
                    candidates.append(variant)

        if not candidates:
            return None

        # ── Feature mapping ─────────────────────────────────────
        lakara_gen = self._LAKARA_TO_GENERATOR.get(lakara, lakara)
        purusha_gen = self._PURUSHA_TO_GENERATOR.get(purusha, purusha)
        vachana_gen = self._VACHANA_TO_GENERATOR.get(vachana, vachana)

        # ── Try each candidate ──────────────────────────────────
        for root in candidates:
            try:
                raw = self.generator.getforms(
                    root, lakara_gen, purusha_gen, vachana_gen
                )
            except SystemExit:
                # Prakriya's generator calls sys.exit() on unknown verbs.
                continue
            except Exception:
                continue

            form = self._extract_form_from_generator_output(raw)
            if not form:
                continue

            # ── Sanity filter: reject known-wrong outputs ──────
            base_root = self._clean_root(str(root))
            weak_markers = self._WEAK_FORMS.get(base_root)
            if weak_markers and any(wm in form for wm in weak_markers):
                continue

            return form

        return None

    @staticmethod
    def _extract_form_from_generator_output(raw: Any) -> Optional[str]:
        """
        The generator returns nested dicts / lists. Flatten to a single
        Devanagari string, defensively walking whatever structure we get.
        """
        if raw is None:
            return None

        # Plain string
        if isinstance(raw, str):
            s = raw.strip()
            return s or None

        # List
        if isinstance(raw, list):
            for item in raw:
                found = PaninianAnalyzer._extract_form_from_generator_output(item)
                if found:
                    return found
            return None

        # Dict — walk values
        if isinstance(raw, dict):
            for value in raw.values():
                found = PaninianAnalyzer._extract_form_from_generator_output(value)
                if found:
                    return found
            return None

        return None

    # ─────────────────────────────────────────────────────────────
    # Derivation trace
    # ─────────────────────────────────────────────────────────────
    def get_derivation_trace(self, dev_form: str) -> str:
        result = self.analyze_verb(dev_form)

        if not result.get("is_verb"):
            return f"❌ {dev_form}: {result.get('error', 'unknown error')}"

        lines = [
            f"🔍 {result['dev_input']}  (SLP1: {result['slp1_used']})",
            "",
            "Morphology:",
            f"  Dhatu   : {result['root']}  ({result['root_slp1']})",
            f"  Lakara  : {result['tense']}",
            f"  Purusha : {result['person']}",
            f"  Vacana  : {result['number']}",
            f"  Gana    : {result['class']}",
            f"  Pada    : {result['pada']}",
            f"  Suffix  : {result['suffix']}",
            "",
            f"Derivation ({len(result['derivation'])} steps):",
        ]
        for i, step in enumerate(result["derivation"], 1):
            lines.append(
                f"  {i:2d}. [{step['sutra_num']:>6s}]  "
                f"{step['sutra']}  →  {step['form']}"
            )
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    analyzer = PaninianAnalyzer()

    print("\n--- SLP1 Conversion ---")
    for w in ["गच्छति", "पठति", "रामः", "भवति", "दृश्"]:
        try:
            print(f"  {w} -> {analyzer.to_slp1(w)}")
        except Exception as e:
            print(f"  {w} -> ERROR: {e}")

    print("\n--- Verb Analysis ---")
    for w in ["गच्छति", "पठति", "करोति", "भवति", "पिबति", "खादति",
              "रामः", "वनम्"]:
        r = analyzer.analyze_verb(w)
        if r.get("is_verb"):
            print(
                f"  {w:10s} → root={r['root']:8s} "
                f"lakara={str(r['tense']):6s} purusha={str(r['person']):8s} "
                f"vacana={str(r['number']):5s} gana={str(r['class']):8s}"
            )
        else:
            print(f"  {w:10s} → not verb  ({r.get('error')})")

    print("\n--- Generator Test ---")
    if analyzer.generator:
        tests = [
            # (root, lakara, purusha, vachana, expected, raw_root_hint)
            ("gam", "law", "praTama", "bahu",  "गच्छन्ति", "gamx~"),
            ("gam", "law", "uttama",  "eka",   "गच्छामि", "gamx~"),
            ("paW", "law", "praTama", "eka",   "पठति",   "paWa"),
            ("kR",  "law", "praTama", "bahu",  "कुर्वन्ति", "qukfY"),
            ("BU",  "law", "praTama", "eka",   "भवति",   "BU"),
            ("as",  "law", "uttama",  "eka",   "अस्मि",   "asa"),
        ]
        for root, lak, pur, vac, expected, raw in tests:
            got = analyzer.generate_verb_form(
                root, lak, pur, vac, raw_root_with_markers=raw
            )
            mark = "✅" if got == expected else "❌"
            print(f"  {mark} {root:5s} {lak:4s} {pur:8s} {vac:5s} "
                  f"→ {got}  (expected {expected})")
    else:
        print("  Generator not initialized")