"""
Test the Prakriya VerbFormGenerator integration.
"""

from modules.nlp_processor import SanskritNLP

nlp = SanskritNLP()

print("\n=== Direct generator test ===")
if nlp.paninian and getattr(nlp.paninian, "generator", None):
    pairs = [
        ("gam",  "law", "praTama", "bahu", "गच्छन्ति"),
        ("gam",  "law", "uttama",  "eka",  "गच्छामि"),
        ("paW",  "law", "praTama", "eka",  "पठति"),
        ("kR",   "law", "praTama", "bahu", "कुर्वन्ति"),
        ("BU",   "law", "praTama", "eka",  "भवति"),
        ("as",   "law", "uttama",  "eka",  "अस्मि"),
    ]
    for root, lak, pur, vac, expected in pairs:
        got = nlp.paninian.generate_verb_form(root, lak, pur, vac)
        mark = "✅" if got == expected else "❌"
        print(f"  {mark} {root:5s} {lak:4s} {pur:8s} {vac:5s} "
              f"→ {got}  (expected {expected})")
else:
    print("  Generator not initialized — check startup output")

print("\n=== End-to-end correction test ===")
cases = [
    ("बालकाः पुस्तकं पठति।",   "बालकाः पुस्तकं पठन्ति।"),
    ("सा पठन्ति।",              "सा पठति।"),
    ("अहं गच्छसि।",             "अहं गच्छामि।"),
    ("ते गच्छति।",              "ते गच्छन्ति।"),
    ("रामः वनं गच्छति।",       "रामः वनं गच्छति।"),
    ("अहं विद्यालय गच्छामि।",  "अहं विद्यालयं गच्छामि।"),
]
for original, expected in cases:
    result = nlp.analyze_text(original)
    corrected = result.get("corrected_sentence", "")
    mark = "✅" if corrected.strip() == expected.strip() else "❌"
    print(f"  {mark} {original}")
    print(f"      → {corrected}")
    if mark == "❌":
        print(f"      (expected: {expected})")