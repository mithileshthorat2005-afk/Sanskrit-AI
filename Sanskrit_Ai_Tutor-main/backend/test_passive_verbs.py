"""
Regression tests for passive-verb (यक् / कर्मणि प्रयोग) classification.

Background: the passive form गम्यते (root गम् + यक् + ते) ends in "े", which
the noun analyzer's bare-locative ending would otherwise steal as a fake
noun ("locative of गम्यत"). That made रामेण वनं गम्यते। look verbless and
trigger a false "Sentence has no verb." issue. These tests lock in:

  * passive forms are classified as verbs (root-gated, exact match),
  * genuine locative nouns (वने, रामे, ग्रामे) are NOT stolen,
  * correction generation preserves passive voice (never suggests the
    active form गच्छन्ति for a passive verb),
  * unrelated indeclinables/nouns that share an ending stay non-verbs.

Run:   cd backend && python test_passive_verbs.py
Exit:  0 if all pass, 1 otherwise.
"""

import re
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


def word_result(text):
    """Return the single-word breakdown entry for a bare word."""
    res = nlp.analyze_text(text, use_ai=False)
    return res["breakdown"][0]


# ─────────────────────────────────────────────────────────────
# 1. Bare passive words are verbs via the passive table
# ─────────────────────────────────────────────────────────────
print("\n[1] Bare passive classification")

b = word_result("गम्यते")
check("गम्यते pos",            b["pos"], "verb")
check("गम्यते source",         b["source"], "passive_table")
check("गम्यते voice",          b["analysis"].get("voice"), "passive")
check("गम्यते root_slp1",      b["analysis"].get("root_slp1"), "gam")
check("गम्यते person",         b["analysis"].get("person"), "third")
check("गम्यते number",         b["analysis"].get("number"), "singular")

b = word_result("पठ्यते")
check("पठ्यते pos",            b["pos"], "verb")
check("पठ्यते source",         b["source"], "passive_table")
check("पठ्यते root_slp1",      b["analysis"].get("root_slp1"), "paW")
check("पठ्यते voice",          b["analysis"].get("voice"), "passive")

b = word_result("गम्यन्ते")
check("गम्यन्ते pos",          b["pos"], "verb")
check("गम्यन्ते number",       b["analysis"].get("number"), "plural")

# ─────────────────────────────────────────────────────────────
# 2. Full sentences
# ─────────────────────────────────────────────────────────────
print("\n[2] Sentence-level checks")

# No nominative subject → agreement cannot fire → clean.
r = nlp.analyze_text("रामेण वनं गम्यते।", use_ai=False)
check("रामेण वनं गम्यते। issues",  r["issues"], [])
check("रामेण वनं गम्यते। score",   r["score"], 100)

r = nlp.analyze_text("रामाय गम्यते।", use_ai=False)
check("रामाय गम्यते। issues",      r["issues"], [])
check("रामाय गम्यते। score",       r["score"], 100)

# Nominative plural subject vs 3sg passive → number disagreement,
# corrected to the PLURAL PASSIVE (गम्यन्ते), never the active गच्छन्ति.
r = nlp.analyze_text("रामाः गम्यते।", use_ai=False)
check("रामाः गम्यते। has issue",   len(r["issues"]), 1)
check("रामाः गम्यते। corrected",   r["corrected_sentence"], "रामाः गम्यन्ते।")
check("रामाः गम्यते। voice kept",  "गच्छ" not in r["corrected_sentence"], True)

# Subject and passive verb agree → clean.
r = nlp.analyze_text("रामाः गम्यन्ते।", use_ai=False)
check("रामाः गम्यन्ते। issues",    r["issues"], [])
check("रामाः गम्यन्ते। score",     r["score"], 100)

# ─────────────────────────────────────────────────────────────
# 3. Noun-analysis regressions — locatives must survive
# ─────────────────────────────────────────────────────────────
print("\n[3] Locative nouns are not stolen by the passive layer")

for w in ("वने", "रामे", "ग्रामे"):
    b = word_result(w)
    check(f"{w} pos",       b["pos"], "noun")
    check(f"{w} source",    b["source"], "noun_rule")
    check(f"{w} case",      b["analysis"].get("case"), "locative")

# A genuine locative that happens to end in य+े must NOT be blocked by the
# passive-looking guard (bare "ये" is deliberately excluded from it).
b = word_result("भये")
check("भये pos",      b["pos"], "noun")
check("भये case",     b["analysis"].get("case"), "locative")

# ─────────────────────────────────────────────────────────────
# 4. Unrelated words sharing a verb-like ending stay non-verbs
# ─────────────────────────────────────────────────────────────
print("\n[4] Negative controls (not verbs)")

for w in ("इति", "प्रति", "शक्ति"):
    b = word_result(w)
    check(f"{w} not verb", b["pos"] != "verb", True)

# An unmatched passive-looking word (कृ is not in PASSIVE_ROOT_STEMS) must
# fall through to Unknown — NOT be parsed as a noun — so the engine never
# fabricates "Sentence has no verb." for input it could not resolve.
b = word_result("क्रियते")
check("क्रियते not noun", b["pos"], "unknown")
r = nlp.analyze_text("क्रियते।", use_ai=False)
check("क्रियते। no false 'no verb'", any("no verb" in i for i in r["issues"]), False)

# ─────────────────────────────────────────────────────────────
# 5. Correction generation preserves passive voice
# ─────────────────────────────────────────────────────────────
print("\n[5] Voice-preserving correction")

check("passive 3pl",
      nlp._get_correct_verb_form("गम्यते", {"root_slp1": "gam", "voice": "passive"},
                                 "third", "plural"), "गम्यन्ते")
check("passive 2sg",
      nlp._get_correct_verb_form("पठ्यते", {"root_slp1": "paW", "voice": "passive"},
                                 "second", "singular"), "पठ्यसे")
check("passive unknown root -> None",
      nlp._get_correct_verb_form("क्रियते", {"root_slp1": "kR", "voice": "passive"},
                                 "third", "plural"), None)
# Active correction still works for active analyses (regression guard).
check("active 3pl still active",
      nlp._get_correct_verb_form("गच्छति", {"root_slp1": "gam"},
                                 "third", "plural"), "गच्छन्ति")

# ─────────────────────────────────────────────────────────────
# 6. Existing active behavior unchanged (regression guard)
# ─────────────────────────────────────────────────────────────
print("\n[6] Active-voice behavior unchanged")

r = nlp.analyze_text("रामः वनं गच्छति।", use_ai=False)
check("रामः वनं गच्छति। issues", r["issues"], [])
check("रामः वनं गच्छति। score",  r["score"], 100)

# The requirement under test is VOICE PRESERVATION, not one exact string.
# The original assertion pinned "no correction generated", which is only
# true when the optional morphology packages (prakriya) are absent. With the
# project venv installed the engine resolves गच्छति and emits the agreement
# fix रामाः वनं गच्छन्ति। — still ACTIVE voice, which is what must hold.
# Accept either "unchanged" or the correct active fix; reject any PASSIVE
# rewrite in both environments.
r = nlp.analyze_text("रामाः वनं गच्छति।", use_ai=False)
check("रामाः वनं गच्छति। has issue", len(r["issues"]), 1)
check("रामाः वनं गच्छति। agreement msg", "agreement" in r["issues"][0], True)
corrected = r["corrected_sentence"]
check("रामाः वनं गच्छति। no passive rewrite",
      bool(re.search(r"(गम्यत|गच्छ्यत|पठ्यत|खाद्यत|हस्यत)", corrected)), False)
check("रामाः वनं गच्छति। correction is active or unchanged",
      corrected in ("रामाः वनं गच्छति।", "रामाः वनं गच्छन्ति।"), True)

# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
print(f"PASS: {PASS}   FAIL: {FAIL}")
if FAILURES:
    print("Failed checks:")
    for f in FAILURES:
        print(f"  - {f}")
sys.exit(1 if FAIL else 0)
