"""
Focused tests for Sanskrit subject–verb person/number agreement.

Background: the agreement benchmark exposed two independent defects that
left the agreement rule silently disabled for whole classes of sentence:

  1. Prakriya returns one entry per matching dhātu, so a form such as
     धावसि (dhātu धावु / सृ) yields person=['maDyama','maDyama'] and
     number=['eka','eka']. The normaliser rejected any list whose length
     was not 1, so person/number came back empty and no comparison ever
     fired.
  2. The dual/plural personal pronouns आवाम्, युवाम् and यूयम् fell through
     to the noun rule, which reads their final -म् as accusative singular.
     They were therefore never eligible as nominative subjects.

These tests lock in:

  * person AND number agreement for ordinary nouns,
  * pronoun subjects including the dual/plural personal pronouns,
  * genitive possessives (मम, तव) are NOT verbs,
  * valid sentences stay at 100 with no phantom issues,
  * corrections preserve active/passive voice.

Run:   cd backend && python test_agreement.py
Exit:  0 if all pass, 1 otherwise.
"""

import sys
from modules.nlp_processor import SanskritNLP

nlp = SanskritNLP()

PASS = 0
FAIL = 0
FAILURES = []


def check(label, got, expected):
    global PASS, FAIL
    if got == expected:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        FAILURES.append(label)
        print(f"  FAIL  {label}")
        print(f"        expected: {expected!r}")
        print(f"        got:      {got!r}")


def analyse(text):
    return nlp.analyze_text(text, use_ai=False)


def is_valid(text):
    """Engine contract: score == 100 means the sentence was accepted."""
    return analyse(text)["score"] == 100


def has_issue(text):
    return len(analyse(text)["issues"]) > 0


# ─────────────────────────────────────────────────────────────
# 1. Valid sentences must remain untouched (no false positives)
# ─────────────────────────────────────────────────────────────
print("\n[1] Valid sentences accepted (score 100, no issues)")
VALID = [
    "रामः वनं गच्छति।",
    "सीता फलं खादति।",
    "बालकाः पठन्ति।",
    "अहं विद्यालयं गच्छामि।",
    "त्वं पुस्तकं पठसि।",
    "वयं उद्याने क्रीडामः।",
    "मम मित्रः विद्यालये गच्छति।",
    "रामेण वनं गम्यते।",          # instrumental subject + passive
]
for s in VALID:
    r = analyse(s)
    check(f"valid {s}", (r["score"], r["issues"]), (100, []))

# ─────────────────────────────────────────────────────────────
# 2. Number agreement — ordinary nouns
# ─────────────────────────────────────────────────────────────
print("\n[2] Number agreement (ordinary nouns)")
NUMBER_CASES = [
    ("रामाः गच्छति।", "plural subject / singular verb"),
    ("सीता गच्छन्ति।", "singular subject / plural verb"),
    ("रामौ पठसि।", "dual subject / singular verb"),
    ("बालकौ धावसि।", "dual subject / singular verb"),
]
for s, why in NUMBER_CASES:
    check(f"number mismatch flagged: {why}", has_issue(s), True)
    check(f"number mismatch scores <100: {why}", is_valid(s), False)

# ─────────────────────────────────────────────────────────────
# 3. Person agreement
# ─────────────────────────────────────────────────────────────
print("\n[3] Person agreement")
PERSON_CASES = [
    ("अहम् गच्छसि।", "first person subject / second person verb"),
    ("अहम् धावन्ति।", "first person singular / third person plural"),
    ("बालकः पठामः।", "third person subject / first person verb"),
    ("रामः धावथ।", "third person subject / second person verb"),
    ("त्वम् धावामः।", "second person subject / first person verb"),
]
for s, why in PERSON_CASES:
    check(f"person mismatch flagged: {why}", has_issue(s), True)
    check(f"person mismatch scores <100: {why}", is_valid(s), False)

# ─────────────────────────────────────────────────────────────
# 4. Combined person + number (dual/plural pronouns)
# ─────────────────────────────────────────────────────────────
print("\n[4] Pronoun subjects (dual / plural personal pronouns)")
PRONOUN_CASES = [
    ("यूयम् गच्छति।", "यूयम् 2nd plural / 3rd singular verb"),
    ("यूयम् गच्छावः।", "यूयम् 2nd plural / 1st dual verb"),
    ("आवाम् पठति।", "आवाम् 1st dual / 3rd singular verb"),
    ("आवाम् गच्छामि।", "आवाम् 1st dual / 1st singular verb"),
    ("युवाम् हसामि।", "युवाम् 2nd dual / 1st singular verb"),
    ("युवाम् नयति।", "युवाम् 2nd dual / 3rd singular verb"),
    ("वयम् धावतः।", "वयम् 1st plural / 3rd dual verb"),
]
for s, why in PRONOUN_CASES:
    check(f"pronoun mismatch flagged: {why}", has_issue(s), True)

print("\n[4b] Pronouns recognised as nominative subjects")
for form, number, person in [
    ("आवाम्", "dual", "first"),
    ("युवाम्", "dual", "second"),
    ("यूयम्", "plural", "second"),
]:
    e = nlp._classify_word(form)
    a = e.get("analysis") or {}
    check(
        f"{form} -> pronoun/nominative/{number}/{person}",
        (e.get("pos"), a.get("case"), a.get("number"), a.get("person")),
        ("pronoun", "nominative", number, person),
    )

# ─────────────────────────────────────────────────────────────
# 5. Genitive possessives must not be verbs
# ─────────────────────────────────────────────────────────────
print("\n[5] Genitive possessives are not verbs")
for form in ("मम", "तव"):
    e = nlp._classify_word(form)
    check(f"{form} not classified as verb", e.get("pos") == "verb", False)
    check(f"{form} classified as pronoun", e.get("pos"), "pronoun")
check(
    "genitive sentence has no phantom agreement issue",
    analyse("मम मित्रः विद्यालये गच्छति।")["issues"],
    [],
)

# ─────────────────────────────────────────────────────────────
# 6. Corrections keep their voice
# ─────────────────────────────────────────────────────────────
print("\n[6] Correction generation preserves voice")
r = analyse("रामाः गच्छति।")
check("रामाः गच्छति। issue text mentions agreement",
      "agreement" in r["issues"][0], True)
check("रामाः गच्छति। corrected form is the active plural",
      r["corrected_sentence"], "रामाः गच्छन्ति।")
check("रामाः गच्छति। correction is not passive",
      r["corrected_sentence"].endswith("गम्यते।"), False)

r = analyse("रामाः गम्यते।")
check("passive agreement correction keeps passive voice",
      r["corrected_sentence"], "रामाः गम्यन्ते।")

r = analyse("रामेण वनं गम्यते।")
check("valid passive sentence is untouched",
      (r["score"], r["corrected_sentence"]), (100, "रामेण वनं गम्यते।"))

# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
print(f"PASS: {PASS}   FAIL: {FAIL}")
if FAILURES:
    print("Failed checks:")
    for f in FAILURES:
        print(f"  - {f}")
sys.exit(1 if FAIL else 0)
