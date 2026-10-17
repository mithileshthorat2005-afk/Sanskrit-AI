"""
Rule-based Sanskrit Noun Declension Analyzer
Detects gender, case, number from word endings — no dictionary needed

Matching notes
-------------
* Every token is tried against the table as written AND against its
  anusvāra spelling. Sanskrit writes the a-stem accusative/nominative
  ending both ways — बालकम् and बालकं are the same word — but the table
  only ever contained the explicit-virāma form, so the far more common
  anusvāra spelling fell through every layer and came out "unknown".
* `analyze()` deliberately returns ALL readings rather than one. A single
  surface ending can belong to several paradigms (ी is an ī-stem
  nominative singular AND an i-stem nominative dual), so the caller needs
  the competing readings to tell a decided parse from an ambiguous one.
"""

import re
from typing import Dict, List, Any, Optional


# (ending, gender, case, number, pattern_name)
# Sorted at runtime by ending length (longest first)
DECLENSION_ENDINGS = [
    # ───── a-stem masculine (राम) ─────
    ('ेभ्यः',   'masculine', 'dative',       'plural',   'a_masc'),
    ('ानाम्',   'masculine', 'genitive',     'plural',   'a_masc'),
    ('ाभ्याम्', 'masculine', 'instrumental', 'dual',     'a_masc'),
    ('ेषु',     'masculine', 'locative',     'plural',   'a_masc'),
    ('ान्',     'masculine', 'accusative',   'plural',   'a_masc'),
    ('ैः',      'masculine', 'instrumental', 'plural',   'a_masc'),
    ('योः',     'masculine', 'genitive',     'dual',     'a_masc'),
    ('ेण',      'masculine', 'instrumental', 'singular', 'a_masc'),
    ('ाय',      'masculine', 'dative',       'singular', 'a_masc'),
    ('ात्',     'masculine', 'ablative',     'singular', 'a_masc'),
    ('स्य',     'masculine', 'genitive',     'singular', 'a_masc'),
    ('ाः',      'masculine', 'nominative',   'plural',   'a_masc'),
    ('ौ',       'masculine', 'nominative',   'dual',     'a_masc'),
    ('म्',      'masculine', 'accusative',   'singular', 'a_masc'),
    ('ः',       'masculine', 'nominative',   'singular', 'a_masc'),
    ('े',       'masculine', 'locative',     'singular', 'a_masc'),

    # ───── a-stem neuter (फल) ─────
    ('ेभ्यः',   'neuter',    'dative',       'plural',   'a_neut'),
    ('ानाम्',   'neuter',    'genitive',     'plural',   'a_neut'),
    ('ाभ्याम्', 'neuter',    'instrumental', 'dual',     'a_neut'),
    ('ेषु',     'neuter',    'locative',     'plural',   'a_neut'),
    ('ानि',     'neuter',    'nominative',   'plural',   'a_neut'),
    ('ानि',     'neuter',    'accusative',   'plural',   'a_neut'),
    ('ैः',      'neuter',    'instrumental', 'plural',   'a_neut'),
    ('योः',     'neuter',    'genitive',     'dual',     'a_neut'),
    ('ेण',      'neuter',    'instrumental', 'singular', 'a_neut'),
    ('ाय',      'neuter',    'dative',       'singular', 'a_neut'),
    ('ात्',     'neuter',    'ablative',     'singular', 'a_neut'),
    ('स्य',     'neuter',    'genitive',     'singular', 'a_neut'),
    ('ी',       'neuter',    'nominative',   'dual',     'a_neut'),
    ('ी',       'neuter',    'accusative',   'dual',     'a_neut'),
    ('म्',      'neuter',    'nominative',   'singular', 'a_neut'),
    ('म्',      'neuter',    'accusative',   'singular', 'a_neut'),
    ('े',       'neuter',    'locative',     'singular', 'a_neut'),

    # ───── ā-stem feminine (सीता) ─────
    ('ाभ्यः',   'feminine',  'dative',       'plural',   'aa_fem'),
    ('ानाम्',   'feminine',  'genitive',     'plural',   'aa_fem'),
    ('ाभ्याम्', 'feminine',  'instrumental', 'dual',     'aa_fem'),
    ('ासु',     'feminine',  'locative',     'plural',   'aa_fem'),
    ('ायै',     'feminine',  'dative',       'singular', 'aa_fem'),
    ('ायाः',    'feminine',  'ablative',     'singular', 'aa_fem'),
    ('ायाः',    'feminine',  'genitive',     'singular', 'aa_fem'),
    ('ायाम्',   'feminine',  'locative',     'singular', 'aa_fem'),
    ('ाभिः',    'feminine',  'instrumental', 'plural',   'aa_fem'),
    ('योः',     'feminine',  'genitive',     'dual',     'aa_fem'),
    ('ाम्',     'feminine',  'accusative',   'singular', 'aa_fem'),
    ('या',      'feminine',  'instrumental', 'singular', 'aa_fem'),
    ('ाः',      'feminine',  'nominative',   'plural',   'aa_fem'),
    ('ाः',      'feminine',  'accusative',   'plural',   'aa_fem'),
    ('ा',       'feminine',  'nominative',   'singular', 'aa_fem'),

    # ───── i-stem masculine (मुनि) ─────
    ('िभ्यः',   'masculine', 'dative',       'plural',   'i_masc'),
    ('ीनाम्',   'masculine', 'genitive',     'plural',   'i_masc'),
    ('िभ्याम्', 'masculine', 'instrumental', 'dual',     'i_masc'),
    ('िषु',     'masculine', 'locative',     'plural',   'i_masc'),
    ('ीन्',     'masculine', 'accusative',   'plural',   'i_masc'),
    ('िभिः',    'masculine', 'instrumental', 'plural',   'i_masc'),
    ('िनोः',    'masculine', 'genitive',     'dual',     'i_masc'),
    ('िना',     'masculine', 'instrumental', 'singular', 'i_masc'),
    ('िने',     'masculine', 'dative',       'singular', 'i_masc'),
    ('िनः',     'masculine', 'ablative',     'singular', 'i_masc'),
    ('िनः',     'masculine', 'genitive',     'singular', 'i_masc'),
    ('यः',      'masculine', 'nominative',   'plural',   'i_masc'),
    ('िम्',     'masculine', 'accusative',   'singular', 'i_masc'),
    ('िनि',     'masculine', 'locative',     'singular', 'i_masc'),
    ('िः',      'masculine', 'nominative',   'singular', 'i_masc'),
    ('ी',       'masculine', 'nominative',   'dual',     'i_masc'),

    # ───── ī-stem feminine (नदी) ─────
    ('ीभ्यः',   'feminine',  'dative',       'plural',   'ii_fem'),
    ('ीनाम्',   'feminine',  'genitive',     'plural',   'ii_fem'),
    ('ीभ्याम्', 'feminine',  'instrumental', 'dual',     'ii_fem'),
    ('ीषु',     'feminine',  'locative',     'plural',   'ii_fem'),
    ('ीः',      'feminine',  'accusative',   'plural',   'ii_fem'),
    ('ीभिः',    'feminine',  'instrumental', 'plural',   'ii_fem'),
    ('्योः',    'feminine',  'genitive',     'dual',     'ii_fem'),
    ('्यै',     'feminine',  'dative',       'singular', 'ii_fem'),
    ('्याः',    'feminine',  'ablative',     'singular', 'ii_fem'),
    ('्याः',    'feminine',  'genitive',     'singular', 'ii_fem'),
    ('्याम्',   'feminine',  'locative',     'singular', 'ii_fem'),
    ('्यः',     'feminine',  'nominative',   'plural',   'ii_fem'),
    ('ीम्',     'feminine',  'accusative',   'singular', 'ii_fem'),
    ('्या',     'feminine',  'instrumental', 'singular', 'ii_fem'),
    ('्यौ',     'feminine',  'nominative',   'dual',     'ii_fem'),
    ('ी',       'feminine',  'nominative',   'singular', 'ii_fem'),

    # ───── u-stem masculine (गुरु) ─────
    ('ुभ्यः',   'masculine', 'dative',       'plural',   'u_masc'),
    ('ूनाम्',   'masculine', 'genitive',     'plural',   'u_masc'),
    ('ुभ्याम्', 'masculine', 'instrumental', 'dual',     'u_masc'),
    ('ुषु',     'masculine', 'locative',     'plural',   'u_masc'),
    ('ून्',     'masculine', 'accusative',   'plural',   'u_masc'),
    ('ुभिः',    'masculine', 'instrumental', 'plural',   'u_masc'),
    ('वोः',     'masculine', 'genitive',     'dual',     'u_masc'),
    ('ुना',     'masculine', 'instrumental', 'singular', 'u_masc'),
    ('वे',      'masculine', 'dative',       'singular', 'u_masc'),
    ('ोः',      'masculine', 'ablative',     'singular', 'u_masc'),
    ('ोः',      'masculine', 'genitive',     'singular', 'u_masc'),
    ('वः',      'masculine', 'nominative',   'plural',   'u_masc'),
    ('ुम्',     'masculine', 'accusative',   'singular', 'u_masc'),
    ('ौ',       'masculine', 'locative',     'singular', 'u_masc'),
    ('ुः',      'masculine', 'nominative',   'singular', 'u_masc'),
    ('ू',       'masculine', 'nominative',   'dual',     'u_masc'),

    # ───── u-stem neuter (मधु) ─────
    ('ुभ्यः',   'neuter',    'dative',       'plural',   'u_neut'),
    ('ूनाम्',   'neuter',    'genitive',     'plural',   'u_neut'),
    ('ुभ्याम्', 'neuter',    'instrumental', 'dual',     'u_neut'),
    ('ुषु',     'neuter',    'locative',     'plural',   'u_neut'),
    ('ूनि',     'neuter',    'nominative',   'plural',   'u_neut'),
    ('ूनि',     'neuter',    'accusative',   'plural',   'u_neut'),
    ('ुभिः',    'neuter',    'instrumental', 'plural',   'u_neut'),
    ('ुनोः',    'neuter',    'genitive',     'dual',     'u_neut'),
    ('ुना',     'neuter',    'instrumental', 'singular', 'u_neut'),
    ('वे',      'neuter',    'dative',       'singular', 'u_neut'),
    ('ोः',      'neuter',    'ablative',     'singular', 'u_neut'),
    ('ोः',      'neuter',    'genitive',     'singular', 'u_neut'),
    ('ुनि',     'neuter',    'locative',     'singular', 'u_neut'),
    ('ुनी',     'neuter',    'nominative',   'dual',     'u_neut'),
    ('ुनी',     'neuter',    'accusative',   'dual',     'u_neut'),
    ('ु',       'neuter',    'nominative',   'singular', 'u_neut'),
    ('ु',       'neuter',    'accusative',   'singular', 'u_neut'),
]


class NounAnalyzer:
    """Rule-based Sanskrit noun analyzer"""

    def __init__(self):
        # Sort by ending length (longest first) so we match most specific endings first
        self.endings = sorted(DECLENSION_ENDINGS, key=lambda x: -len(x[0]))

        # Reverse index: pattern -> {number -> accusative ending}.
        # Lets a caller turn a parsed stem back into its accusative form
        # (सिंह + masculine singular -> सिंहम्) without hardcoding a table of
        # individual words, which is what the destination-accusative
        # correction used to do.
        self.accusative_endings: Dict[str, Dict[str, str]] = {}
        for _ending, _gender, _case, _number, _pattern in DECLENSION_ENDINGS:
            if _case == "accusative":
                self.accusative_endings.setdefault(_pattern, {}).setdefault(
                    _number, _ending
                )

    @staticmethod
    def _surface_variants(word: str) -> List[str]:
        """Spelling variants of `word` that stand for the same ending.

        The anusvāra form (बालकं) and the explicit-virāma form (बालकम्) are
        the same accusative; matching only one of them made every unseen
        anusvāra spelling unresolvable. The original spelling is always
        first so an exact match still wins.
        """
        variants = [word]
        if word.endswith("ं"):
            variants.append(word[:-1] + "म्")
        return variants

    def analyze(self, word: str) -> List[Dict[str, Any]]:
        """Return ALL possible morphological interpretations."""
        if not word:
            return []

        word = word.replace('।', '').replace('|', '').replace('.', '').strip()
        if len(word) < 2:
            return []

        analyses = []
        seen = set()

        for surface in self._surface_variants(word):
            for ending, gender, case, number, pattern in self.endings:
                if not surface.endswith(ending):
                    continue
                stem = surface[:-len(ending)]
                if len(stem) < 2:  # avoid over-stripping
                    continue

                key = (stem, gender, case, number, pattern)
                if key in seen:
                    continue
                seen.add(key)

                analysis = {
                    'word': word,
                    'stem': stem,
                    'gender': gender,
                    'case': case,
                    'number': number,
                    'pattern': pattern,
                    'method': 'declension_rule',
                    'confidence': round(0.5 + 0.05 * len(ending), 2),
                }
                # Record when the match was made on the anusvāra spelling so
                # the caller can report which surface form was actually parsed.
                if surface != word:
                    analysis['matched_surface'] = surface
                analyses.append(analysis)

        if not analyses:
            analyses.append({
                'word': word,
                'stem': word,
                'gender': 'unknown',
                'case': 'stem',
                'number': 'unknown',
                'pattern': 'unknown',
                'method': 'fallback',
                'confidence': 0.2,
                'note': 'No declension ending matched'
            })

        return analyses

    def accusative_form(self, stem: str, pattern: str, number: str) -> Optional[str]:
        """Regenerate the accusative of `stem` for the given paradigm/number.

        Returns None when the paradigm table does not carry that cell
        (e.g. a-stem accusative dual is not in DECLENSION_ENDINGS), so the
        caller must handle a missing answer rather than invent one.
        """
        if not stem or not pattern or not number:
            return None
        ending = self.accusative_endings.get(pattern, {}).get(number)
        if ending is None:
            return None
        return stem + ending

    def analyze_best(self, word: str) -> Dict[str, Any]:
        """Return the single most likely analysis."""
        analyses = self.analyze(word)
        if not analyses:
            return {'word': word, 'pos': 'unknown'}

        best = dict(analyses[0])
        best['pos'] = 'noun'
        best['alternatives'] = analyses[1:5]
        return best

    def is_noun(self, word: str) -> bool:
        """Quick check: does the word look like a noun?"""
        analyses = self.analyze(word)
        return bool(analyses) and analyses[0].get('method') == 'declension_rule'


# ─────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────
if __name__ == "__main__":
    analyzer = NounAnalyzer()

    tests = [
        'रामः', 'रामम्', 'रामेण', 'रामस्य', 'रामाय',
        'फलम्', 'फलेन', 'फलानि',
        'सीता', 'सीताम्', 'सीतायाः',
        'मुनिः', 'मुनिम्',
        'नदी', 'नदीम्',
        'गुरुः', 'गुरुम्',
    ]

    for w in tests:
        print(f"\n{w}")
        for a in analyzer.analyze(w)[:2]:
            print(f"  → stem={a['stem']}, {a['gender']}, {a['case']}, {a['number']} [{a['pattern']}]")
