"""
SkillMapper — translates normalized Sanskrit error_type strings into skill metadata.

Responsibilities (this module only):
  - Load skill_mapping.json
  - Map an error_type string → {skill_id, lesson_id, skill_name, difficulty}
  - Return None for unmapped or unknown types (caller decides what to do)

This module does NOT update BKT.
This module does NOT call NLP.
BKT updates are the caller's responsibility (main.py → sqlite_repository).
"""

import json
import os
from typing import Dict, List, Optional, Any


# ---------------------------------------------------------------------------
# Controlled error vocabulary
# ---------------------------------------------------------------------------
# These are the only error_type strings the system recognises.
# Any string not in this set is treated as "unknown_error".
RECOGNIZED_ERROR_TYPES = {
    "vibhakti_error",
    "sandhi_error",
    "tense_error",
    "pronoun_error",
    "upasarga_error",
    "verb_conjugation_error",
    "gender_error",
    "samasa_error",
    "voice_error",
    "participle_error",
    "mood_error",
    "punctuation_error",
    "agreement_error",   # recognized but intentionally unmapped
    "unknown_error",     # recognized but intentionally unmapped
}

# These are recognized but must NOT produce a BKT observation.
INTENTIONALLY_UNMAPPED = {"agreement_error", "unknown_error"}


class SkillMapper:
    """
    Maps Sanskrit grammar error_type strings to skill/lesson IDs for BKT.

    Usage:
        mapper = SkillMapper()
        result = mapper.map_error_to_skill("vibhakti_error")
        # {"skill_id": 11, "lesson_id": 11, "skill_name": "Vibhakti – The 7 Cases", "difficulty": 6}
        # or None if the error type has no valid mapping
    """

    def __init__(self, mapping_path: Optional[str] = None):
        if mapping_path is None:
            mapping_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "skill_mapping.json",
            )
        self._mapping: Dict[str, Dict[str, Any]] = {}
        self._load(mapping_path)

    def _load(self, path: str) -> None:
        """Load the skill mapping JSON. Fails loudly so misconfiguration is caught early."""
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"SkillMapper: skill_mapping.json not found at {path}. "
                "Create backend/data/skill_mapping.json before starting the server."
            )
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        # Extract only the mappable entries (skip _comment and intentionally_unmapped)
        for key, value in raw.items():
            if key.startswith("_") or key == "intentionally_unmapped":
                continue
            if isinstance(value, dict) and "skill_id" in value:
                self._mapping[key] = value

        print(f"SkillMapper: loaded {len(self._mapping)} error→skill mappings.")

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def normalize_error_type(self, raw_label: str) -> str:
        """
        Normalize an error type label to a controlled vocabulary string.

        Handles labels that the AI might return with different casing or spacing:
            "Vibhakti Error"  →  "vibhakti_error"
            "SANDHI_ERROR"    →  "sandhi_error"
            "tense error"     →  "tense_error"
            "pronoun_error"   →  "pronoun_error"  (already normalized)
            "garbage"         →  "unknown_error"
        """
        if not raw_label or not isinstance(raw_label, str):
            return "unknown_error"

        # Lowercase, replace spaces and hyphens with underscores, strip extras
        normalized = raw_label.strip().lower().replace(" ", "_").replace("-", "_")

        # Remove common AI suffixes like "case_error" → try "vibhakti_error" etc.
        if normalized in RECOGNIZED_ERROR_TYPES:
            return normalized

        # Try stripping trailing "_error" and re-checking with "_error" suffix
        # e.g. "vibhakti" → "vibhakti_error"
        if not normalized.endswith("_error"):
            candidate = normalized + "_error"
            if candidate in RECOGNIZED_ERROR_TYPES:
                return candidate

        # Substring matching for common AI variations
        # e.g. "case selection error" → "vibhakti_error"
        substring_map = {
            "vibhakti": "vibhakti_error",
            "case": "vibhakti_error",
            "sandhi": "sandhi_error",
            "euphon": "sandhi_error",
            "tense": "tense_error",
            "lakara": "tense_error",
            "pronoun": "pronoun_error",
            "sarvanama": "pronoun_error",
            "upasarga": "upasarga_error",
            "prefix": "upasarga_error",
            "conjugat": "verb_conjugation_error",
            "verb form": "verb_conjugation_error",
            "gender": "gender_error",
            "linga": "gender_error",
            "samasa": "samasa_error",
            "compound": "samasa_error",
            "voice": "voice_error",
            "passive": "voice_error",
            "participle": "participle_error",
            "krit": "participle_error",
            "mood": "mood_error",
            "imperative": "mood_error",
            "optative": "mood_error",
            "punctuat": "punctuation_error",
            "virama": "punctuation_error",
            "purna": "punctuation_error",
            "agreement": "agreement_error",
            "concord": "agreement_error",
        }
        for substring, mapped in substring_map.items():
            if substring in normalized:
                return mapped

        return "unknown_error"

    def map_error_to_skill(self, error_type: str) -> Optional[Dict[str, Any]]:
        """
        Map a normalized error_type to skill metadata.

        Returns:
            dict with keys {skill_id, lesson_id, skill_name, difficulty}
            OR None if the error type is unmapped (intentionally or unknown).

        The caller must treat None as "no BKT update for this error."
        """
        normalized = self.normalize_error_type(error_type)

        if normalized in INTENTIONALLY_UNMAPPED:
            return None

        return self._mapping.get(normalized, None)

    def get_skills_for_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of issue dicts (each must have an 'error_type' field)
        and return a deduplicated list of skill metadata dicts ready for BKT.

        Deduplication policy:
            If the same skill_id appears more than once in a single submission
            (e.g. two separate vibhakti errors), produce ONLY ONE BKT observation
            for that skill. One submission = one competency failure signal.

        Args:
            issues: List of dicts like {"error_type": "vibhakti_error", "rule": ..., "description": ...}

        Returns:
            List of unique skill dicts [{skill_id, lesson_id, skill_name, difficulty}, ...]
            Only includes mappable error types.
        """
        seen_skill_ids: set = set()
        result: List[Dict[str, Any]] = []

        for issue in issues:
            if not isinstance(issue, dict):
                continue
            error_type = issue.get("error_type", "unknown_error")
            skill_meta = self.map_error_to_skill(error_type)
            if skill_meta is None:
                continue
            skill_id = skill_meta["skill_id"]
            if skill_id in seen_skill_ids:
                continue
            seen_skill_ids.add(skill_id)
            result.append(skill_meta)

        return result

    def describe_unmapped_error(self, error_type: str) -> str:
        """
        For error types that are recognized but unmapped (agreement_error, unknown_error),
        return a human-readable explanation so the learner understands what went wrong
        even though no specific skill is targeted.
        """
        normalized = self.normalize_error_type(error_type)
        descriptions = {
            "agreement_error": (
                "Subject-verb or noun-adjective agreement error detected. "
                "This means a word in your sentence does not match another word in number, "
                "gender, or person. For example: a plural subject used with a singular verb, "
                "or a feminine noun with a masculine adjective. "
                "Review Vibhakti (Lesson 11) and Verb Conjugation (Lesson 6) for the relevant rules."
            ),
            "unknown_error": (
                "The system detected a potential issue but could not classify it into a "
                "known Sanskrit grammar category. Possible causes: unfamiliar word form, "
                "mixed script, unconventional sandhi, or a sentence structure outside the "
                "current rule set. Please verify each word's case ending, verb conjugation, "
                "and ensure the sentence ends with a Pūrṇa Virāma (।)."
            ),
        }
        return descriptions.get(normalized, "Unrecognized grammar issue.")
