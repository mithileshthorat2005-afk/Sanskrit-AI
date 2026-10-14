"""Evaluation script for the Sanskrit Agreement Benchmark (v1).

Evaluates the rule-based Sanskrit NLP engine against
`sanskrit_grammar_benchmark_300.json` — a focused subject–verb
person/number agreement benchmark (300 cases, 150 valid / 150 invalid).

This is a SEPARATE evaluator from `evaluate_grammar.py`. The benchmark's
README explicitly asks that it not replace the existing 51-case
multi-category regression dataset, so:
  * `data/grammar_test_dataset.json` is untouched; run
    `evaluate_grammar.py` for that regression suite.
  * This script reads the benchmark's own schema (metadata + `cases`)
    and reports agreement-specific metrics plus parse-coverage
    diagnostics.

Benchmark schema (nested):
{
  "dataset_name": ..., "version": ..., "case_count": ...,
  "scope": ..., "limitations": [...],
  "cases": [
    { "id", "sentence", "expected_valid", "category",
      "issue", "validation_basis", "label_status", "source_note" }
  ]
}

Expected output contract (identical to evaluate_grammar.py):
  - engine_valid = (score == 100), i.e. no issues detected.
  - Positive class = invalid sentence; negative class = valid sentence.
  - Non-zero exit code when there are false positives, false negatives,
    or processing exceptions.

Important:
- Runs WITHOUT live AI API calls (use_ai=False).
- Separates processing exceptions from classification errors.
- Reports per-subject and per-verb PARSE COVERAGE, because the dominant
  failure mode here is vocabulary/paradigm coverage, not rule logic.
- Label caveat (from the benchmark README): labels are rule-based
  curated and NOT independently expert-validated. Treat scores as
  agreement-pattern accuracy, not expert-validated accuracy.

Usage:
    cd backend
    python evaluate_agreement_benchmark.py [optional/path/to/benchmark.json]
"""

import json
import os
import sys
from collections import Counter


# Resolve the backend directory regardless of the current working directory.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from modules.nlp_processor import SanskritNLP


DEFAULT_DATASET_PATH = os.path.join(
    BACKEND_DIR,
    "data",
    "sanskrit_grammar_benchmark_300.json",
)


def load_dataset(path=None):
    """Load and validate the nested benchmark dataset.

    Returns the raw top-level object (with metadata and `cases`).
    Raises on structural problems rather than silently mis-mapping.
    """
    dataset_path = path or DEFAULT_DATASET_PATH

    if not os.path.isfile(dataset_path):
        raise FileNotFoundError(
            f"Benchmark dataset not found: {dataset_path}"
        )

    with open(dataset_path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(
            "The benchmark must be a JSON object with a 'cases' array."
        )

    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("The benchmark is missing a 'cases' array.")

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case #{index} must be a JSON object.")
        if not isinstance(case.get("sentence"), str):
            raise ValueError(
                f"Case #{index} must contain a string 'sentence'."
            )
        if not isinstance(case.get("expected_valid"), bool):
            raise ValueError(
                f"Case #{index} must contain a Boolean 'expected_valid'."
            )
        if not isinstance(case.get("category"), str):
            raise ValueError(
                f"Case #{index} must contain a string 'category'."
            )

    return payload


def new_counter():
    """Create counters for binary classification."""
    return {
        "tp": 0,
        "fp": 0,
        "tn": 0,
        "fn": 0,
        "evaluated": 0,
        "exceptions": 0,
    }


def record_classification(counts, expected_valid, engine_valid):
    """Update binary classification counts.

    Positive class: invalid sentence.
    Negative class: valid sentence.
    """
    counts["evaluated"] += 1

    expected_invalid = not expected_valid
    engine_invalid = not engine_valid

    if expected_invalid and engine_invalid:
        counts["tp"] += 1
    elif expected_valid and engine_valid:
        counts["tn"] += 1
    elif expected_valid and engine_invalid:
        counts["fp"] += 1
    else:
        counts["fn"] += 1


def calculate_metrics(counts):
    """Calculate metrics, returning None when undefined."""
    tp = counts["tp"]
    fp = counts["fp"]
    tn = counts["tn"]
    fn = counts["fn"]

    evaluated = counts["evaluated"]

    precision_denominator = tp + fp
    recall_denominator = tp + fn
    f1_denominator = 2 * tp + fp + fn

    return {
        "accuracy": (
            (tp + tn) / evaluated if evaluated else None
        ),
        "precision": (
            tp / precision_denominator
            if precision_denominator
            else None
        ),
        "recall": (
            tp / recall_denominator
            if recall_denominator
            else None
        ),
        "f1": (
            2 * tp / f1_denominator
            if f1_denominator
            else None
        ),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "evaluated": evaluated,
        "exceptions": counts["exceptions"],
    }


def format_percentage(value):
    """Format a metric without confusing zero with an undefined value."""
    if value is None:
        return "N/A"
    return f"{value:.2%}"


def _first_last_tokens(sentence):
    """Return (subject, verb) = (first, last) Devanagari tokens.

    The benchmark uses minimal `SUBJECT VERB।` sentences, so first/last
    token is a reliable subject/verb split.
    """
    tokens = sentence.replace("।", "").replace("|", "").split()
    if not tokens:
        return "", ""
    return tokens[0], tokens[-1]


def collect_coverage(nlp, cases):
    """Probe parse coverage for the benchmark's subjects and verbs.

    This is diagnostic only — it does not affect classification. It
    answers "did the engine even resolve this word?" so coverage gaps
    (missing roots / mis-parsed pronouns) are visible separately from
    agreement-rule logic.
    """
    subject_status = {}
    verb_status = {}

    for case in cases:
        subject, verb = _first_last_tokens(case["sentence"])

        if subject and subject not in subject_status:
            entry = nlp._classify_word(subject)
            analysis = entry.get("analysis", {})
            subject_status[subject] = {
                "pos": entry.get("pos"),
                "source": entry.get("source"),
                "case": analysis.get("case"),
                "number": analysis.get("number"),
                "person": analysis.get("person"),
            }

        if verb and verb not in verb_status:
            entry = nlp._classify_word(verb)
            analysis = entry.get("analysis", {})
            verb_status[verb] = {
                "pos": entry.get("pos"),
                "source": entry.get("source"),
                "person": analysis.get("person"),
                "number": analysis.get("number"),
            }

    return subject_status, verb_status


def print_coverage_report(subject_status, verb_status):
    """Print which benchmark words the engine could and could not parse."""
    subjects_resolved = [
        w for w, s in subject_status.items() if s["pos"] != "unknown"
    ]
    subjects_unknown = [
        w for w, s in subject_status.items() if s["pos"] == "unknown"
    ]
    # For this agreement benchmark a subject must resolve to a
    # nominative form for the agreement rule to see it.
    subjects_not_nominative = [
        w for w, s in subject_status.items()
        if s["pos"] != "unknown" and s.get("case") != "nominative"
    ]

    verbs_resolved = [
        w for w, s in verb_status.items() if s["pos"] == "verb"
    ]
    verbs_not_verb = [
        w for w, s in verb_status.items() if s["pos"] != "verb"
    ]

    print("\nParse-coverage diagnostics (does the engine resolve the word?)")
    print("-" * 64)
    print(
        f"  Subjects: {len(subject_status)} distinct — "
        f"{len(subjects_resolved)} parsed, {len(subjects_unknown)} unknown"
    )
    if subjects_unknown:
        print(f"    Unknown subjects: {', '.join(sorted(subjects_unknown))}")
    if subjects_not_nominative:
        print(
            "    Parsed but NOT nominative "
            "(agreement rule cannot use them):"
        )
        for word in sorted(subjects_not_nominative):
            info = subject_status[word]
            print(
                f"      {word}: case={info.get('case')} "
                f"number={info.get('number')} "
                f"(source={info.get('source')})"
            )

    print(
        f"  Verbs: {len(verb_status)} distinct — "
        f"{len(verbs_resolved)} parsed as verb, "
        f"{len(verbs_not_verb)} NOT verb"
    )
    if verbs_not_verb:
        print("    Verbs not recognized:")
        for word in sorted(verbs_not_verb):
            info = verb_status[word]
            print(
                f"      {word}: pos={info.get('pos')} "
                f"(source={info.get('source')})"
            )


def run_evaluation(dataset_path=None):
    """Evaluate the engine on the agreement benchmark and return a report."""
    payload = load_dataset(dataset_path)
    cases = payload["cases"]

    dataset_name = payload.get("dataset_name", "unknown")
    version = payload.get("version", "unknown")
    limitations = payload.get("limitations", [])

    if not cases:
        print("The benchmark contains no cases.")
        return {
            "total": 0,
            "evaluated": 0,
            "processing_errors": 0,
            "accuracy": None,
            "failures": [],
            "category_metrics": {},
            "regression": True,
        }

    nlp = SanskritNLP()

    total = len(cases)
    valid_sentences = sum(1 for c in cases if c["expected_valid"])
    invalid_sentences = total - valid_sentences

    overall = new_counter()
    category_results = {}
    failures = []
    processing_errors = 0

    for index, case in enumerate(cases):
        sentence = case["sentence"]
        expected_valid = case["expected_valid"]
        category_name = case.get("category", "uncategorized")

        category = category_results.setdefault(
            category_name,
            new_counter(),
        )

        try:
            result = nlp.analyze_text(sentence, use_ai=False)

            if not isinstance(result, dict):
                raise TypeError(
                    "analyze_text() did not return a dictionary."
                )

            if result.get("error"):
                raise ValueError(str(result["error"]))

            score = result.get("score")

            if not isinstance(score, (int, float)):
                raise ValueError(
                    f"Missing or invalid score in engine result: {score!r}"
                )

            issues = result.get("issues", [])
            if issues is None:
                issues = []
            if not isinstance(issues, list):
                issues = [issues]

            # Same scoring contract as evaluate_grammar.py.
            engine_valid = score == 100

            record_classification(overall, expected_valid, engine_valid)
            record_classification(category, expected_valid, engine_valid)

            if engine_valid != expected_valid:
                failures.append({
                    "index": index,
                    "id": case.get("id", ""),
                    "sentence": sentence,
                    "expected": (
                        "valid" if expected_valid else "invalid"
                    ),
                    "got": (
                        "valid" if engine_valid else "invalid"
                    ),
                    "issue": case.get("issue"),
                    "score": score,
                    "issues": issues,
                    "exception": None,
                })

        except Exception as exc:
            processing_errors += 1
            category["exceptions"] += 1
            failures.append({
                "index": index,
                "id": case.get("id", ""),
                "sentence": sentence,
                "expected": (
                    "valid" if expected_valid else "invalid"
                ),
                "got": "exception",
                "issue": case.get("issue"),
                "score": None,
                "issues": [],
                "exception": f"{type(exc).__name__}: {exc}",
            })

    overall_metrics = calculate_metrics(overall)
    category_metrics = {
        name: calculate_metrics(counts)
        for name, counts in category_results.items()
    }

    # Coverage diagnostics (read-only probing; does not affect metrics).
    subject_status, verb_status = collect_coverage(nlp, cases)

    # -------------------------
    # Print evaluation report
    # -------------------------
    print("=" * 64)
    print("SANSKRIT AGREEMENT BENCHMARK EVALUATION REPORT")
    print("=" * 64)
    print(f"\nDataset:  {dataset_name} (v{version})")
    print(f"  Cases:            {total}")
    print(f"  Expected valid:   {valid_sentences}")
    print(f"  Expected invalid: {invalid_sentences}")
    print(f"  Evaluated:        {overall['evaluated']}")
    print(f"  Exceptions:       {processing_errors}")

    print("\nOverall Metrics (successfully evaluated cases):")
    print(f"  Accuracy:  {format_percentage(overall_metrics['accuracy'])}")
    print(
        "  Precision (invalid detection): "
        f"{format_percentage(overall_metrics['precision'])}"
    )
    print(
        "  Recall (invalid detection): "
        f"{format_percentage(overall_metrics['recall'])}"
    )
    print(f"  F1 Score:  {format_percentage(overall_metrics['f1'])}")
    print(f"  TP: {overall['tp']}  FP: {overall['fp']}  "
          f"TN: {overall['tn']}  FN: {overall['fn']}")

    print("\nCategory-Level Metrics:")
    for name, metrics in category_metrics.items():
        print(f"\n  Category: {name}")
        print(f"    Evaluated: {metrics['evaluated']}  "
              f"Exceptions: {metrics['exceptions']}")
        print(f"    Accuracy:  {format_percentage(metrics['accuracy'])}")
        print(
            "    Precision: "
            f"{format_percentage(metrics['precision'])}"
        )
        print(
            "    Recall:    "
            f"{format_percentage(metrics['recall'])}"
        )
        print(f"    F1 Score:  {format_percentage(metrics['f1'])}")
        print(f"    TP: {metrics['tp']}, FP: {metrics['fp']}, "
              f"FN: {metrics['fn']}, TN: {metrics['tn']}")

    print_coverage_report(subject_status, verb_status)

    print(f"\nIndividual Failures ({len(failures)}):")
    for failure in failures:
        print(f"\n  #{failure['index']} [{failure.get('id', '')}]: "
              f"{failure['sentence'][:60]!r}")
        print(f"    Expected: {failure['expected']}")
        print(f"    Got:      {failure['got']}")
        print(f"    Score:    {failure['score']}")
        if failure["issues"]:
            print(f"    Issues:   {failure['issues'][:2]}")
        if failure["exception"]:
            print(f"    Exception: {failure['exception']}")

    regression = (
        overall["fp"] > 0
        or overall["fn"] > 0
        or processing_errors > 0
    )

    print("\n" + "=" * 64)
    if regression:
        print("CLASSIFICATION FAILURES PRESENT")
        print(
            "FP = valid sentence flagged as invalid; "
            "FN = invalid sentence accepted as valid."
        )
        print(
            "See parse-coverage diagnostics above: un-resolved subjects "
            "or verbs are a likely cause of FN."
        )
    else:
        print("No classification failures or processing exceptions detected.")
    print("=" * 64)

    if limitations:
        print("\nBenchmark label caveats (from its README):")
        for line in limitations:
            print(f"  - {line}")
        print("=" * 64)

    return {
        "total": total,
        "evaluated": overall["evaluated"],
        "processing_errors": processing_errors,
        "accuracy": overall_metrics["accuracy"],
        "precision": overall_metrics["precision"],
        "recall": overall_metrics["recall"],
        "f1": overall_metrics["f1"],
        "true_positives": overall["tp"],
        "false_positives": overall["fp"],
        "true_negatives": overall["tn"],
        "false_negatives": overall["fn"],
        "failures": failures,
        "category_metrics": category_metrics,
        "regression": regression,
    }


if __name__ == "__main__":
    try:
        # Optional first CLI arg: an alternate benchmark JSON path.
        alt_path = sys.argv[1] if len(sys.argv) > 1 else None
        report = run_evaluation(alt_path)

        # Exit code 1 indicates classification failures or exceptions.
        sys.exit(1 if report["regression"] else 0)

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"\nEvaluation could not run: {exc}", file=sys.stderr)
        sys.exit(2)
