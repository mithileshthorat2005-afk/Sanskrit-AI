"""
Test corrections: Fix A (accusative) and Fix B (subject-verb agreement)
"""

from modules.nlp_processor import SanskritNLP

nlp = SanskritNLP()

TESTS = [
    # (input, expected_correction_or_None)
    ("अहं विद्यालय गच्छामि।",   "अहं विद्यालयं गच्छामि।"),         # destination fix
    ("अहं विद्यालयः गच्छामि।",  "अहं विद्यालयं गच्छामि।"),         # nominative → accusative
    ("अहं विद्यालयम् गच्छामि।", None),                              # already correct, no change
    ("अहं विद्यालयं गच्छामि।",  None),                              # already correct, no change

    ("बालकाः पुस्तकं पठति।",  "बालकाः पुस्तकं पठन्ति।"),           # plural subject, sg verb
    ("सा पठन्ति।",              "सा पठति।"),                        # sg subject, plural verb
    ("अहं गच्छसि।",             "अहं गच्छामि।"),                     # 1st person subj, 2nd person verb

    ("रामः वनं गच्छति।",      None),                                # correct, no change
    ("बालकः फलं खादति।",      None),                                # correct, no change
]

for original, expected in TESTS:
    result = nlp.analyze_text(original)
    corrected = result.get("corrected_sentence", "")
    issues = result.get("issues", [])

    if expected is None:
        # Expect no change (or only punctuation added if missing)
        ok = corrected.strip() == original.strip()
        status = "✅" if ok else "❌"
        print(f"{status} {original}")
        print(f"     → {corrected}")
        if not ok:
            print(f"     ISSUES: {issues}")
    else:
        ok = corrected.strip() == expected.strip()
        status = "✅" if ok else "❌"
        print(f"{status} {original}")
        print(f"     expected: {expected}")
        print(f"     got:      {corrected}")
        if not ok:
            print(f"     ISSUES: {issues}")