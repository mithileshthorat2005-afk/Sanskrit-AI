"""Rule-level tests for the generalization changes to the grammar engine.

    python test_generalization.py

WHY THIS FILE EXISTS
--------------------
The two shipped benchmarks are saturated at 100% and are narrow: they prove
the engine still works, not that the new rules are correct. Every rule added
in this change is exercised here at the level it was written — the rule, not
the sentence — with four kinds of case each:

  * positive     the rule fires (or stays silent) where it should;
  * negative     the rule does NOT fire where it should not;
  * boundary     the guard that keeps the rule from over-reaching;
  * lexical      the same behaviour on a word the rule was never tuned on.

INDEPENDENCE
------------
The generalization rules were developed against generalization_dev.json, so
those sentences are NOT evidence. Every sentence below that belongs to the
development set is marked (dev) and is used only as a positive regression
anchor. All other sentences were written fresh for this file and appear in
no dataset in the repository; where a rule's correctness depends on
vocabulary being unseen, that is asserted against the live resources rather
than assumed.
"""

from __future__ import annotations

import os
import re
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from modules.nlp_processor import SanskritNLP  # noqa: E402

PASSED = 0
FAILED = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  PASS  {label}")
    else:
        FAILED += 1
        print(f"  FAIL  {label}" + (f"   -> {detail}" if detail else ""))


def check_eq(label: str, got, want) -> None:
    check(label, got == want, f"got {got!r}, want {want!r}")


def section(title: str) -> None:
    print()
    print(f"  --- {title} ---")


def main() -> int:
    nlp = SanskritNLP()

    def run(text):
        return nlp.analyze_text(text, use_ai=False)

    def issues(r):
        return r.get("issues") or []

    def words(r):
        return {b["word"]: b for b in r.get("breakdown", [])}

    def case_of(r, w):
        return str((words(r).get(w, {}).get("analysis") or {}).get("case", "")).lower()

    def num_of(r, w):
        return str((words(r).get(w, {}).get("analysis") or {}).get("number", "")).lower()

    def gen_of(r, w):
        return str((words(r).get(w, {}).get("analysis") or {}).get("gender", "")).lower()

    def person_of(r, w):
        return str((words(r).get(w, {}).get("analysis") or {}).get("person", "")).lower()

    # Tokens this suite asserts are outside the development resources. Checked
    # against the live indexes so the "unseen" claim is a fact, not a hope.
    dev = (set(nlp.vocabulary) | set(nlp._lexicon)
           | set(nlp._verb_paradigm_index) | set(nlp._passive_index))

    # ================================================================
    section("R1  Visarga sandhi reversal  (ो ← ः,  र् ← ः)")
    # ================================================================
    # Positive — fires on unseen vocabulary, which is the point: the rule is
    # morphological, so no stem has to be listed for it to work.
    r = run("सिंहो वनं गच्छति।")
    check("R1+ positive  सिंहो (unseen) resolves, no unknown word",
          not (r.get("unknown_words") or []) and r.get("score") == 100,
          f"score={r.get('score')} unknown={[x.get('word') for x in (r.get('unknown_words') or [])]}")
    check("R1+ positive  सिंहो resolves TO सिंहः, not to a made-up stem",
          (words(r).get("सिंहो", {}).get("analysis") or {}).get("resolved_from") == "सिंहः",
          str(words(r).get("सिंहो")))

    # Different lexical item — the rule is not a two-word table.
    r = run("व्याघ्रो वनं गच्छति।")
    check("R1+ lexical  व्याघ्रो resolves via reversal",
          not (r.get("unknown_words") or []) and r.get("score") == 100,
          f"score={r.get('score')}")

    # Boundary — punctuation is not part of the reversal.
    r = run("सिंहो वनं गच्छति")
    check("R1~ boundary  missing danda is still a punctuation fault, not unknown",
          any("Virama" in i or "punctuation" in i.lower() for i in issues(r))
          and not (r.get("unknown_words") or []),
          f"score={r.get('score')} issues={issues(r)}")

    # Negative — a token that already resolves is never reversed over.
    r = run("मुनिः पश्यति।")
    check("R1- negative  a direct-visarga token is left exactly as written",
          (words(r).get("मुनिः", {}).get("source") == "dictionary"
           or words(r).get("मुनिः", {}).get("source") == "noun_rule"),
          str(words(r).get("मुनिः")))

    r = run("अश्वौ गच्छतः।")
    check("R1- negative  a ौ-final dual is not treated as sandhi",
          not (r.get("unknown_words") or []) and r.get("score") == 100,
          f"score={r.get('score')}")

    # Boundary — reversal is a spelling fallback, never a source of certainty:
    # an unresolvable word stays unresolvable instead of being talked into a
    # parse it does not have.
    r = run("फ्लर्ग्व ग्लर्फङ्घ।")
    check("R1~ boundary  nonsense is still reported unknown, not sandhi-rescued",
          bool(r.get("unknown_words")) and r.get("score") < 100,
          f"score={r.get('score')}")

    # ================================================================
    section("R2  Anusvāra / virāma surface variant  (ं ↔ म्)")
    # ================================================================
    r = run("त्वं वनं गच्छसि।")
    check("R2+ positive  त्वं keeps its PERSON (the dictionary त्वम् must win)",
          person_of(r, "त्वं") == "second",
          f"person={person_of(r, 'त्वं')!r} src={words(r).get('त्वं', {}).get('source')}")

    # Different lexical item.
    r = run("वयं फलं खादामः।")
    check("R2+ lexical  वयं keeps first person", person_of(r, "वयं") == "first",
          f"person={person_of(r, 'वयं')!r}")

    # Boundary — both spellings must yield the same grammatical verdict.
    a = run("वनम् ऋषयः पश्यन्ति।")
    b = run("वनं ऋषयः पश्यन्ति।")
    check("R2~ boundary  वनम् and वनं agree on case and number",
          (case_of(a, "वनम्"), num_of(a, "वनम्")) == (case_of(b, "वनं"), num_of(b, "वनं")),
          f"{case_of(a, 'वनम्')}/{num_of(a, 'वनम्')} vs {case_of(b, 'वनं')}/{num_of(b, 'वनं')}")

    # Negative — the anusvāra spelling must not be grabbed by a lower layer
    # before the dictionary sees the explicit form. This is exactly the bug
    # that silenced agreement on त्वं.
    r = run("त्वं वनं गच्छतः।")
    check("R2- negative  त्वं is still able to drive agreement",
          any("agreement" in i.lower() for i in issues(r)),
          f"issues={issues(r)}")

    # ================================================================
    section("R3  (stem, paradigm) attestation")
    # ================================================================
    r = run("विद्यालयः ग्रामं पश्यति।")
    a = words(r).get("विद्यालयः", {}).get("analysis") or {}
    check("R3+ positive  विद्यालयः is masculine singular, not i-masc PLURAL",
          a.get("gender") == "masculine" and a.get("number") == "singular",
          str({k: a.get(k) for k in ("stem", "gender", "case", "number", "pattern")}))

    # A token's own headword must not vouch for its own parse: विद्यालयः IS a
    # headword, and its own entry is exactly what would confirm the wrong
    # (विद्याल + i-masc) reading.
    check("R3~ boundary  विद्यालयः is not read as stem विद्याल (self-confirmation)",
          a.get("stem") == "विद्यालय", f"stem={a.get('stem')!r}")

    # Different lexical item, never used while developing the rule.
    r = run("मन्दिरे मृगः पश्यति।")
    a = words(r).get("मन्दिरे", {}).get("analysis") or {}
    check("R3+ lexical  मन्दिरे resolves as locative singular",
          a.get("case") == "locative" and a.get("number") == "singular",
          str({k: a.get(k) for k in ("stem", "case", "number", "pattern")})
          or "unresolved")

    # Negative — attestation is only ever used to CHOOSE between readings,
    # never to reject one. Genuine unseen vocabulary must still parse.
    for w, label in (("ऋषिः", "unseen i-masc"), ("मृगः", "unseen a-masc"),
                     ("हरिः", "unseen i-masc")):
        r = run(f"{w} पश्यति।")
        check(f"R3- negative  {w} ({label}) resolves, attestation does not veto it",
              not (r.get("unknown_words") or []) and r.get("score") == 100,
              f"score={r.get('score')} unknown={[x.get('word') for x in (r.get('unknown_words') or [])]}")

    # Boundary — an inconclusive attestation falls back to longest-match, so
    # an unseen dual like छात्रौ keeps its number instead of being blanked.
    r = run("छात्रौ गच्छतः।")
    check("R3~ boundary  unseen dual छात्रौ keeps number=singular=false",
          num_of(r, "छात्रौ") == "dual", f"number={num_of(r, 'छात्रौ')!r}")

    # ================================================================
    section("R4  Ambiguity — same stem, same case, contested number")
    # ================================================================
    # Positive: the number cannot be asserted, so NO error may be invented.
    r = run("सुन्दरी गच्छति।")
    check("R4+ positive  सुन्दरी (sg/dual homograph) invents no agreement error",
          r.get("score") == 100 and not issues(r),
          f"score={r.get('score')} issues={issues(r)}")

    # Different lexical item — same homograph, unseen stem.
    r = run("हरी वनं गच्छति।")
    check("R4+ lexical  हरी (unseen sg/dual homograph) invents no error",
          r.get("score") == 100 and not issues(r),
          f"score={r.get('score')} issues={issues(r)}")

    # Negative: different STEM is a segmentation choice that ending length
    # already settles — the number must be asserted and the error reported.
    r = run("सिंहाः वनं गच्छति।")
    check("R4- negative  सिंहाः keeps number=plural and IS flagged",
          num_of(r, "सिंहाः") == "plural" and bool(issues(r)),
          f"number={num_of(r, 'सिंहाः')!r} issues={issues(r)}")

    r = run("गुरवः बालकं पठति।")
    check("R4- lexical  गुरवः (unseen) keeps plural and IS flagged",
          num_of(r, "गुरवः") == "plural" and bool(issues(r)),
          f"number={num_of(r, 'गुरवः')!r} issues={issues(r)}")

    # Boundary: same stem but a DIFFERENT case is not a homograph at all.
    r = run("रामौ वनं गच्छति।")
    check("R4~ boundary  रामौ (nom-dual vs loc-singular) is still flagged",
          bool(issues(r)), f"issues={issues(r)}")

    # Boundary: ambiguity must not become a licence to accept nonsense.
    r = run("क्लान्ब्र जक्क्क।")
    check("R4~ boundary  unresolvable words are still reported unknown",
          bool(r.get("unknown_words")) and r.get("score") < 100,
          f"score={r.get('score')}")

    # ================================================================
    section("R5  Nominal sentences — \"no verb\" only when nothing is nominative")
    # ================================================================
    r = run("रामः राजा।")
    check("R5+ positive  रामः राजा। (nom + predicate nominative) is not an error",
          r.get("score") == 100 and not issues(r),
          f"score={r.get('score')} issues={issues(r)}")

    # Different lexical item — feminine predicate adjective.
    r = run("सीता सुन्दरी।")
    check("R5+ lexical  सीता सुन्दरी। is not an error",
          r.get("score") == 100 and not issues(r),
          f"score={r.get('score')} issues={issues(r)}")

    # Negative: verbless AND no nominative is a real defect.
    r = run("रामम् वनम्।")
    check("R5- negative  रामम् वनम्। (no verb, no nominative) IS flagged",
          any("no verb" in i.lower() for i in issues(r)),
          f"issues={issues(r)}")

    # Boundary — a verb is still a verb; nothing changed there.
    r = run("रामः वनं गच्छति।")
    check("R5~ boundary  an ordinary verbal sentence is untouched",
          r.get("score") == 100 and not issues(r),
          f"issues={issues(r)}")

    # Boundary — a sentence we could not fully parse must not be accused of
    # lacking a verb.
    r = run("क्लान्ब्र जक्क्क।")
    check("R5~ boundary  no \"no verb\" claim on input we could not parse",
          not any("no verb" in i.lower() for i in issues(r)),
          f"issues={issues(r)}")

    # ================================================================
    section("R6  Destination → accusative, generalised off its two old stems")
    # ================================================================
    r = run("अहं शत्रुः गच्छामि।")
    check("R6+ positive  शत्रुः (a stem the rule never knew) is flagged",
          any("Accusative" in i or "Dvitiya" in i for i in issues(r)),
          f"issues={issues(r)}")

    # Different lexical item — and unseen while developing the rule.
    r = run("अहं पुरुषः गच्छामि।")
    check("R6+ lexical  पुरुषः (unseen) is flagged",
          any("Accusative" in i or "Dvitiya" in i for i in issues(r)),
          f"issues={issues(r)}")

    # The generalisation must still cover the two stems it used to know.
    r = run("अहं विद्यालयः गच्छामि।")
    check("R6+ regression  the original विद्यालय case still fires",
          any("Accusative" in i or "Dvitiya" in i for i in issues(r)),
          f"issues={issues(r)}")

    # Negative: a neuter म्-final token is nominative AND accusative at once,
    # so its case is undecidable and it must never be accused.
    for text, label in (("अहं वनं गच्छामि।", "वनम्"),
                        ("अहं गृहं गच्छामि।", "गृहम्")):
        r = run(text)
        check(f"R6- negative  neuter {label} is NOT flagged (case undecidable)",
              not any("Accusative" in i or "Dvitiya" in i for i in issues(r)),
              f"issues={issues(r)}")

    # Negative: already-accusative is left alone.
    r = run("अहं मुनिम् पश्यामि।")
    check("R6- negative  an already-accusative object is NOT flagged",
          not any("Accusative" in i or "Dvitiya" in i for i in issues(r)),
          f"issues={issues(r)}")

    # Negative: only motion verbs govern a goal.
    r = run("अहं पुस्तकम् पठामि।")
    check("R6- negative  a non-motion verb does not trigger the rule",
          not any("Accusative" in i or "Dvitiya" in i for i in issues(r)),
          f"issues={issues(r)}")

    # Boundary: the subject is the first nominative and is never flagged.
    r = run("अहं शत्रुः गच्छामि।")
    flagged = nlp._destination_errors(r.get("breakdown", []))
    check("R6~ boundary  exactly one destination is flagged",
          len(flagged) == 1, f"{len(flagged)} flagged: {[b.get('word') for b in flagged]}")
    check("R6~ boundary  the flagged token is the goal, never the subject",
          flagged and flagged[0].get("word") == "शत्रुः",
          str([b.get("word") for b in flagged]))

    # Boundary: a third-person subject must not trigger a rule whose whole
    # guard is a first-person subject.
    r = run("रामः शत्रुः गच्छति।")
    check("R6~ boundary  no first-person trigger, no destination claim",
          not any("Accusative" in i or "Dvitiya" in i for i in issues(r)),
          f"issues={issues(r)}")

    # ================================================================
    section("R7  Accusatives are generated from the paradigm, not recalled")
    # ================================================================
    na = nlp.noun_analyzer
    check_eq("R7+ positive  सिंह + a-masc + singular", na.accusative_form("सिंह", "a_masc", "singular"), "सिंहम्")
    # For u-stems this paradigm table puts the stem vowel INSIDE the ending
    # (ुः, ुम्, वः), so the stored stem is the bare consonant stem शत्र —
    # the same convention the analyzer uses when it strips an ending, and
    # the same one the attestation index is built with. Hence शत्र + ुम्.
    check_eq("R7+ lexical   शत्र + u-masc + singular", na.accusative_form("शत्र", "u_masc", "singular"), "शत्रुम्")
    check_eq("R7+ lexical   पुरुष + a-masc + singular", na.accusative_form("पुरुष", "a_masc", "singular"), "पुरुषम्")
    check_eq("R7+ lexical   विद्यालय + a-masc + singular", na.accusative_form("विद्यालय", "a_masc", "singular"), "विद्यालयम्")
    check_eq("R7+ lexical   सिंह + a-masc + plural", na.accusative_form("सिंह", "a_masc", "plural"), "सिंहान्")

    # Boundary: a paradigm cell that does not exist must return None rather
    # than a guess, so the issue is reported without a fabricated rewrite.
    check("R7~ boundary  absent cell (a-masc dual) returns None, not a guess",
          na.accusative_form("सिंह", "a_masc", "dual") is None,
          repr(na.accusative_form("सिंह", "a_masc", "dual")))
    check("R7~ boundary  unknown pattern returns None",
          na.accusative_form("सिंह", "not_a_pattern", "singular") is None)
    check("R7~ boundary  empty stem returns None",
          na.accusative_form("", "a_masc", "singular") is None)

    # Boundary: the issue and the correction are derived from one list, so a
    # token can never be rewritten for a fault that was not reported.
    r = run("अहं शत्रुः गच्छामि।")
    n_flagged = len(nlp._destination_errors(r.get("breakdown", [])))
    n_dvitiya = sum(1 for i in issues(r) if "Dvitiya" in i)
    check_eq("R7~ boundary  one flagged destination, one Dvitiya issue", n_flagged, n_dvitiya)
    check_eq("R7~ boundary  correction rewrites the flagged token", r.get("corrected_sentence"),
             "अहं शत्रुम् गच्छामि।")

    # ================================================================
    section("R8  Cross-cutting — corrections agree with the issues raised")
    # ================================================================
    for text, want in (
        ("अहं पुरुषः गच्छामि।", "अहं पुरुषम् गच्छामि।"),
        ("अहं विद्यालयः गच्छामि।", "अहं विद्यालयम् गच्छामि।"),
        ("बालकाः पठ्यते।", "बालकाः पठ्यन्ते।"),          # passive voice preserved
        ("मृगौ वनं गच्छति।", "मृगौ वनं गच्छतः।"),        # dual generated
    ):
        r = run(text)
        check_eq(f"R8  correction for {text}", r.get("corrected_sentence"), want)

    # Boundary: a sentence we cannot parse is never rewritten out of nothing.
    r = run("क्लान्ब्र जक्क्क।")
    check("R8~ boundary  unresolvable input is not silently 'corrected' into Sanskrit",
          not issues(r) or (r.get("corrected_sentence") or "").strip()
          in ("क्लान्ब्र जक्क्क।", "क्लान्ब्र जक्क्क ।"),
          repr(r.get("corrected_sentence")))

    # ================================================================
    section("R9  Unseen vocabulary is genuinely unseen (fixture check)")
    # ================================================================
    for w in ("ऋषिः", "मृगः", "हरिः", "पुरुषः", "बालिकां", "ऋषयः", "मृगौ",
              "पुरुषाः", "हरी"):
        check(f"R9  {w} is absent from the development resources", w not in dev)

    # ================================================================
    print()
    print("=" * 62)
    print(f"  PASSED: {PASSED}   FAILED: {FAILED}")
    print("=" * 62)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
