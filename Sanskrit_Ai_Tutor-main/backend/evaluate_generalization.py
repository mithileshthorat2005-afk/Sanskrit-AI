"""Held-out generalization evaluation for the Sanskrit grammar engine.

    python evaluate_generalization.py                  # improved engine
    python evaluate_generalization.py --baseline        # pre-change engine
    python evaluate_generalization.py --dataset data/generalization_dev.json

WHAT THIS IS FOR
----------------
The two shipped evaluators (evaluate_grammar.py, evaluate_agreement_benchmark.py)
are saturated at 100% and are narrow: the first is 51 curated sentences, the
second is a present-tense agreement benchmark over 15 subjects and 90 verbs.
Neither can tell a generalizing engine from a memorizing one. This runs a
dev/held-out split and reports the metrics the project spec asks for:
accuracy, precision/recall/F1 for invalid detection, FP and FN rates,
correction exact-match, uncertainty precision/coverage, and per-split and
per-dimension breakdowns.

BASELINE
--------
`--baseline` restores the pre-change behaviour so original and improved are
compared on the SAME examples. The original files are not recoverable from
git (HEAD predates unrelated earlier work), so the baseline is reconstructed
as an explicit shim and then VALIDATED: it must reproduce the recorded
pre-change results on generalization_dev.json — 7 of 30 misclassified, with
the specific scores noted below. `--validate-baseline` runs that check.

Labels are never adjusted to fit an output. A case that fails is reported
as a failure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from modules.nlp_processor import SanskritNLP  # noqa: E402
from modules.noun_analyzer import NounAnalyzer  # noqa: E402


# ───────────────────────────────────────────────────────────────────
# Baseline shim — restores pre-change behaviour, measurement only
# ───────────────────────────────────────────────────────────────────
# Every override below is annotated with what it is undoing. Nothing here
# ships: this is test scaffolding, and its fidelity is checked against the
# recorded pre-change dev results by --validate-baseline.

_ORIG_RUN_CHECKS = SanskritNLP._run_checks
_ORIG_FIX_DESTINATION = SanskritNLP._fix_destination_accusative
_NO_VERB = "Sentence has no verb."

# The two stems the destination rule used to know, verbatim from the
# original implementation.
_OLD_DEST_STEMS = ('विद्यालय', 'ग्राम')
_OLD_DEST_WORDS = ('विद्यालय', 'ग्राम')
_OLD_DEST_ACCUSATIVES = ('विद्यालयम्', 'विद्यालयं', 'ग्रामम्', 'ग्रामं')
_OLD_ACC_MAP = {
    'विद्यालय': 'विद्यालयं',
    'विद्यालयः': 'विद्यालयं',
    'ग्राम': 'ग्रामम्',
    'ग्रामः': 'ग्रामम्',
}


def _baseline_surface_variants(self, clean):
    """Undo: sandhi reversal. Layer 1 only ever tried the anusvāra/virāma
    alternation, and no layer ever saw a visarga-reversed spelling."""
    variants = [clean]
    if clean.endswith('ं'):
        variants.append(clean[:-1] + 'म्')
    elif clean.endswith('म्'):
        variants.append(clean[:-1] + 'ं')
    return variants


def _baseline_noun_surface_variants(word):
    """Undo: anusvāra matching in the declension table. The table only ever
    contained the explicit-virāma forms."""
    return [word]


def _baseline_disambiguate(self, word, readings):
    """Undo: attestation + ambiguity detection. Longest matching ending
    simply won, and the number was always asserted."""
    best = dict(readings[0])
    best.pop('word', None)
    return best


def _baseline_classify_word(self, word):
    """Undo: layer-1 precedence across spellings. Layer 1 tried the token and
    its anusvāra/virāma twin; layers 2-5 were then given ONLY the token as
    written, so a lower layer could never see an alternate spelling."""
    import re as _re
    clean = _re.sub(r'[.,!?;।|]$', '', word).strip()
    for surface in self._surface_variants(clean):
        entry = self.vocabulary.get(surface)
        if entry:
            return self._dictionary_result(word, clean, surface, entry)
    result = self._classify_analysers(word, clean, clean)
    if result is not None:
        return result
    return {
        'word': word, 'pos': 'unknown', 'source': 'none', 'meaning': 'unknown',
        'analysis': {'note': 'Not resolved by any layer'},
    }


def _baseline_destination_errors(self, breakdown):
    """Undo: the generalised destination rule — back to two hardcoded stems
    and a first-person check limited to अहं/अहम्. Returns at most one flag,
    because the original appended an issue and then `break`."""
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
    has_first_person = any(
        b['word'] in ('अहं', 'अहम्')
        or (b.get('analysis') or {}).get('stem') == 'अहम्'
        for b in breakdown
    )
    if not has_first_person:
        return []
    for b in breakdown:
        stem = (b.get('analysis') or {}).get('stem', '')
        w_text = b.get('word', '')
        if stem in _OLD_DEST_STEMS or w_text.startswith(_OLD_DEST_WORDS):
            if w_text in _OLD_DEST_ACCUSATIVES:
                continue
            case = str((b.get('analysis') or {}).get('case', '')).lower()
            if case and case != 'accusative':
                return [b]
    return []


def _baseline_run_checks(self, text, breakdown):
    """Undo: the nominal-sentence guard.

    The current guard withholds "Sentence has no verb." when a nominative is
    present (Sanskrit allows verbless nominal sentences). The original
    reported it for EVERY fully-resolved verbless sentence. Only that term is
    restored; agreement and punctuation pass through untouched."""
    issues, corrections = _ORIG_RUN_CHECKS(self, text, breakdown)
    has_verb = any(b['pos'] == 'verb' for b in breakdown)
    has_unknown = any(b['pos'] == 'unknown' for b in breakdown)
    if breakdown and not has_verb and not has_unknown:
        if _NO_VERB not in issues:
            issues.insert(1 if issues else 0, _NO_VERB)
    else:
        issues = [i for i in issues if i != _NO_VERB]
    return issues, corrections


def _baseline_fix_destination(self, sentence, flagged):
    """Undo: generated accusatives — back to the four-entry word map."""
    import re as _re
    tokens = sentence.split()
    fixed = []
    for tok in tokens:
        m = _re.match(r'^([ऀ-ॿ]+)([।॥.,!?;|]*)$', tok)
        if not m:
            fixed.append(tok)
            continue
        core, punct = m.group(1), m.group(2)
        if core in _OLD_ACC_MAP:
            fixed.append(_OLD_ACC_MAP[core] + punct)
        else:
            fixed.append(tok)
    return ' '.join(fixed)


def apply_baseline() -> None:
    SanskritNLP._surface_variants = _baseline_surface_variants
    NounAnalyzer._surface_variants = staticmethod(_baseline_noun_surface_variants)
    SanskritNLP._disambiguate = _baseline_disambiguate
    SanskritNLP._classify_word = _baseline_classify_word
    SanskritNLP._destination_errors = _baseline_destination_errors
    SanskritNLP._run_checks = _baseline_run_checks
    SanskritNLP._fix_destination_accusative = _baseline_fix_destination


# ───────────────────────────────────────────────────────────────────
# Evaluation
# ───────────────────────────────────────────────────────────────────
# Issue strings that assert a grammatical fault. A case marked as
# uncertain must never come back carrying one of these — inventing an
# error for a word we could not parse is exactly what the uncertainty
# contract forbids. Punctuation is excluded: it is about the input string,
# not about a form we failed to analyse.
_FABRICATED = (
    'agreement', 'Accusative', 'Dvitiya', 'does not agree',
    'no verb', 'should be',
)


def _load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _norm(s):
    return ' '.join((s or '').split())


def evaluate(ds, label):
    nlp = SanskritNLP()
    determinate = ds['cases']
    uncertainty = ds.get('uncertainty_cases', [])

    rows = []
    for c in determinate:
        res = nlp.analyze_text(c['sentence'], use_ai=False)
        score = res.get('score')
        engine_valid = (score == 100)
        issues = res.get('issues') or []
        unknown = res.get('unknown_words') or []
        rows.append({
            'case': c, 'score': score, 'issues': issues, 'unknown': unknown,
            'engine_valid': engine_valid,
            'expected': c['expected_valid'],
            'correct': engine_valid == c['expected_valid'],
            'corrected': res.get('corrected_sentence'),
        })

    urows = []
    for c in uncertainty:
        res = nlp.analyze_text(c['sentence'], use_ai=False)
        issues = res.get('issues') or []
        unknown = res.get('unknown_words') or []
        fabricated = [i for i in issues
                      if any(t in i for t in _FABRICATED)]
        urows.append({
            'case': c, 'score': res.get('score'), 'issues': issues,
            'unknown': unknown, 'fabricated': fabricated,
            'reported': bool(unknown) and not fabricated,
            'expected': c['expected_unknown'],
        })

    # ── confusion matrix (invalid is the positive class) ──
    tp = sum(1 for r in rows if not r['expected'] and not r['engine_valid'])
    fn = sum(1 for r in rows if not r['expected'] and r['engine_valid'])
    tn = sum(1 for r in rows if r['expected'] and r['engine_valid'])
    fp = sum(1 for r in rows if r['expected'] and not r['engine_valid'])
    n = len(rows)
    acc = (tp + tn) / n if n else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    fp_rate = fp / (fp + tn) if (fp + tn) else 0.0
    fn_rate = fn / (fn + tp) if (fn + tp) else 0.0

    # ── correction exact-match ──
    corr_cases = [r for r in rows if r['case'].get('expected_correction')]
    corr_ok = sum(1 for r in corr_cases
                  if _norm(r['corrected']) == _norm(r['case']['expected_correction']))
    corr_rate = corr_ok / len(corr_cases) if corr_cases else None

    # ── uncertainty ──
    reported = [r for r in rows if r['unknown']]
    reported += [{'case': u['case'], 'unknown': u['unknown']}
                 for u in urows if u['reported']]
    exp_u = [u for u in urows if u['expected']]
    u_detected = [u for u in exp_u if u['reported']]
    u_prec_n = len(reported)
    u_prec_hit = sum(1 for r in reported
                     if r['case'].get('expected_unknown'))
    uncertainty_precision = (u_prec_hit / u_prec_n) if u_prec_n else None
    uncertainty_recall = (len(u_detected) / len(exp_u)) if exp_u else None
    uncertainty_coverage = (len(reported) / (n + len(uncertainty))) if (n + len(uncertainty)) else None
    # uncertain verdicts landing on determinate input = false uncertainty
    false_uncertain = sum(1 for r in rows if r['unknown'])

    # ── accepted nonsense (known limitation, measured not scored) ──
    accepted_nonsense = []
    for c in ds.get('accepted_nonsense_cases', []):
        res = nlp.analyze_text(c['sentence'], use_ai=False)
        accepted_nonsense.append({
            'id': c['id'], 'sentence': c['sentence'],
            'score': res.get('score'),
            'reported_unknown': bool(res.get('unknown_words')),
            'issues': res.get('issues') or [],
        })

    # ── per-split / per-dimension ──
    def bucket(key):
        groups = defaultdict(list)
        for r in rows:
            groups[r['case'].get(key, '?')].append(r)
        return groups

    def table(groups, name):
        out = [f"    {name:6s} {'n':>4s} {'ok':>4s} {'acc':>7s} {'FP':>4s} {'FN':>4s}"]
        for k in sorted(groups):
            g = groups[k]
            ok = sum(1 for r in g if r['correct'])
            f = sum(1 for r in g if r['expected'] and not r['engine_valid'])
            m = sum(1 for r in g if not r['expected'] and r['engine_valid'])
            out.append(f"    {k:6s} {len(g):4d} {ok:4d} {ok/len(g)*100:6.1f}% {f:4d} {m:4d}")
        return out

    lines = []
    lines.append("=" * 78)
    lines.append(f"  {label}")
    lines.append("=" * 78)
    lines.append(f"  determinate cases : {n}   uncertainty cases: {len(uncertainty)}")
    lines.append(f"  class balance     : {sum(1 for r in rows if r['expected'])} valid / "
                 f"{sum(1 for r in rows if not r['expected'])} invalid")
    lines.append("")
    lines.append("  Overall (invalid-detection):")
    lines.append(f"    accuracy {acc*100:6.2f}%   precision {prec*100:6.2f}%   "
                 f"recall {rec*100:6.2f}%   F1 {f1*100:6.2f}%")
    lines.append(f"    TP {tp:3d}  FP {fp:3d}  TN {tn:3d}  FN {fn:3d}   "
                 f"FP rate {fp_rate*100:5.2f}%   FN rate {fn_rate*100:5.2f}%")
    lines.append("")
    lines.append("  By split:")
    lines.extend(table(bucket('split'), 'split'))
    lines.append("")
    lines.append("  By dimension:")
    lines.extend(table(bucket('dimension'), 'dim'))
    lines.append("")
    if corr_cases:
        lines.append(f"  Correction exact-match : {corr_ok}/{len(corr_cases)}"
                     + (f" = {corr_rate*100:.1f}%" if corr_rate is not None else ""))
        for r in corr_cases:
            if _norm(r['corrected']) != _norm(r['case']['expected_correction']):
                lines.append(f"      MISS {r['case']['id']}: got {r['corrected']!r} "
                             f"want {r['case']['expected_correction']!r}")
    else:
        lines.append("  Correction exact-match : no labelled corrections in this set")
    lines.append("")
    lines.append("  Uncertainty:")

    def _pct(v):
        """Right-aligned percentage, or a dash when the metric is undefined."""
        return '    -' if v is None else f'{v * 100:5.1f}%'

    lines.append(f"    precision {_pct(uncertainty_precision)}   "
                 f"recall {_pct(uncertainty_recall)}   "
                 f"coverage {_pct(uncertainty_coverage)}")
    lines.append(f"    uncertain verdicts on DETERMINATE input (false "
                 f"uncertainty): {false_uncertain}")
    for u in urows:
        mark = 'OK  ' if u['reported'] == u['expected'] else 'MISS'
        words = [x.get('word') for x in u['unknown']]
        lines.append(f"    {mark} {u['case']['id']:8s} score={u['score']} "
                     f"unknown={words} fabricated={u['fabricated']}")
    if accepted_nonsense:
        lines.append("")
        lines.append("  Accepted nonsense (known limitation, NOT scored):")
        for a in accepted_nonsense:
            lines.append(f"      {a['id']:8s} score={a['score']} "
                         f"reported_unknown={a['reported_unknown']} issues={a['issues']}")
    lines.append("")
    lines.append("  Failures:")
    fails = [r for r in rows if not r['correct']]
    if not fails:
        lines.append("    none")
    for r in fails:
        lines.append(f"    {r['case']['id']:8s} exp={'VALID  ' if r['expected'] else 'INVALID'} "
                     f"got={'VALID  ' if r['engine_valid'] else 'INVALID'} score={r['score']} "
                     f"issues={r['issues']}  | {r['case']['sentence']}")
    lines.append("")
    lines.append(f"  RESULT: {tp + tn}/{n} correct"
                 + ("" if not fails else f"   ({len(fails)} failure(s))"))
    lines.append("=" * 78)
    print("\n".join(lines))

    return {
        'label': label, 'n': n, 'accuracy': acc, 'precision': prec,
        'recall': rec, 'f1': f1, 'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
        'fp_rate': fp_rate, 'fn_rate': fn_rate, 'failures': len(fails),
        'correction_exact_match': corr_rate, 'correction_n': len(corr_cases),
        'uncertainty_precision': uncertainty_precision,
        'uncertainty_recall': uncertainty_recall,
        'uncertainty_coverage': uncertainty_coverage,
        'false_uncertain': false_uncertain,
        'accepted_nonsense': accepted_nonsense,
        'rows': rows, 'urows': urows,
    }


# ───────────────────────────────────────────────────────────────────
# Baseline validation against the recorded pre-change dev results
# ───────────────────────────────────────────────────────────────────
# Observed on the improved engine's development set BEFORE any fix was
# applied, and quoted here so the shim has something to be checked against.
RECORDED_BASELINE_DEV_MISSES = {
    'DEV-01': 95,   # सिंहो -> unknown, visarga sandhi unresolved
    'DEV-02': 95,   # बालको -> unknown, visarga sandhi unresolved
    'DEV-07': 95,   # गीतं  -> unknown, anusvāra not matched
    'DEV-11': 85,   # रामः राजा।     -> "Sentence has no verb."
    'DEV-12': 85,   # सीता सुन्दरी।  -> "Sentence has no verb."
    'DEV-29': 100,  # अहं नायकः गच्छामि। -> destination rule only knew two stems
    'DEV-30': 100,  # अहं सिंहः गच्छामि।  -> destination rule only knew two stems
}


def validate_baseline(ds):
    """Run the shim over dev and check it reproduces the recorded original."""
    res = evaluate(ds, 'BASELINE SHIM — validation against recorded pre-change results')
    got = {r['case']['id']: r['score'] for r in res['rows'] if not r['correct']}
    print('\n  RECORDED pre-change misses:')
    for k, v in RECORDED_BASELINE_DEV_MISSES.items():
        state = 'MATCH' if got.get(k) == v else f'expected score {v}, got {got.get(k)}'
        print(f"    {state:34s} {k}")
    extra = sorted(set(got) - set(RECORDED_BASELINE_DEV_MISSES))
    missing = sorted(set(RECORDED_BASELINE_DEV_MISSES) - set(got))
    ok = (got == RECORDED_BASELINE_DEV_MISSES)
    print(f"\n  shim reproduces the recorded original exactly: "
          f"{'YES' if ok else 'NO'}")
    if extra:
        print(f"    unexpected misses: {extra}")
    if missing:
        print(f"    expected misses absent: {missing}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', default=os.path.join('data', 'generalization_heldout.json'))
    ap.add_argument('--baseline', action='store_true',
                    help='evaluate the pre-change engine instead')
    ap.add_argument('--validate-baseline', action='store_true',
                    help='check the baseline shim against the recorded dev results')
    args = ap.parse_args()

    path = args.dataset
    if not os.path.isabs(path):
        path = os.path.join(BACKEND_DIR, path)
    ds = _load(path)

    if args.validate_baseline:
        dev = _load(os.path.join(BACKEND_DIR, 'data', 'generalization_dev.json'))
        apply_baseline()
        ok = validate_baseline(dev)
        return 0 if ok else 1

    if args.baseline:
        apply_baseline()

    label = ('BASELINE (pre-change)' if args.baseline else 'IMPROVED (current)')
    if 'heldout' in os.path.basename(path):
        label += ' — HELD-OUT'
    elif 'dev' in os.path.basename(path):
        label += ' — DEVELOPMENT (used for tuning; not evidence of generalization)'
    else:
        label += f' — {os.path.basename(path)}'

    res = evaluate(ds, label)
    print('\n'.join([
        '=' * 78,
    ]))
    # evaluate() already printed nothing; print now
    return 0 if res['failures'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
