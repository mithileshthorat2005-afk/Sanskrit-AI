
"""Pytest-style evaluation script for the Sanskrit Grammar Engine.

Evaluates the rule-based Sanskrit NLP engine against a JSON dataset.

Expected dataset format:
[
    {
        "sentence": "रामः वनं गच्छति।",
        "expected_valid": true,
        "error_type": "none"
    }
]

Important:
- Runs without making live AI API calls.
- Separates processing exceptions from grammar classification errors.
- Handles missing score/issues fields safely.
- Reports overall and per-category metrics.
- Returns a non-zero exit code when classification failures or
  processing exceptions are detected.
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
    "grammar_test_dataset.json",
)


def load_dataset(path=None):
    """Load and validate the JSON test dataset."""
    dataset_path = path or DEFAULT_DATASET_PATH

    if not os.path.isfile(dataset_path):
        raise FileNotFoundError(
            f"Test dataset not found: {dataset_path}"
        )

    with open(dataset_path, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list):
        raise ValueError("The test dataset must be a JSON array.")

    for index, case in enumerate(dataset):
        if not isinstance(case, dict):
            raise ValueError(
                f"Test case #{index} must be a JSON object."
            )

        if not isinstance(case.get("sentence"), str):
            raise ValueError(
                f"Test case #{index} must contain a string 'sentence'."
            )

        if not isinstance(case.get("expected_valid"), bool):
            raise ValueError(
                f"Test case #{index} must contain a Boolean "
                "'expected_valid' value."
            )

        if not isinstance(case.get("error_type"), str):
            raise ValueError(
                f"Test case #{index} must contain a string 'error_type'."
            )

    return dataset


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


def run_evaluation(dataset_path=None):
    """Evaluate the Sanskrit grammar engine and return its report."""
    dataset = load_dataset(dataset_path)

    if not dataset:
        print("The dataset contains no test cases.")
        return {
            "total": 0,
            "evaluated": 0,
            "processing_errors": 0,
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "failures": [],
            "category_metrics": {},
            "regression": True,
        }

    # Initialize the NLP engine once.
    nlp = SanskritNLP()

    total = len(dataset)
    valid_sentences = sum(
        1 for case in dataset if case["expected_valid"]
    )
    invalid_sentences = total - valid_sentences

    overall = new_counter()
    category_results = {}
    failures = []
    processing_errors = 0

    for index, case in enumerate(dataset):
        sentence = case["sentence"]
        expected_valid = case["expected_valid"]
        error_type = case["error_type"]

        category = category_results.setdefault(
            error_type,
            new_counter(),
        )

        try:
            # Rule-based mode: no live AI fallback should be requested.
            result = nlp.analyze_text(
                sentence,
                use_ai=False,
            )

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

            # Preserve the scoring contract used by the existing engine.
            # This assumes 100 means no issues and a lower score means
            # at least one issue was detected.
            engine_valid = score == 100

            record_classification(
                overall,
                expected_valid,
                engine_valid,
            )

            record_classification(
                category,
                expected_valid,
                engine_valid,
            )

            if engine_valid != expected_valid:
                failures.append({
                    "index": index,
                    "sentence": sentence,
                    "expected": (
                        "valid" if expected_valid else "invalid"
                    ),
                    "got": (
                        "valid" if engine_valid else "invalid"
                    ),
                    "error_type": error_type,
                    "score": score,
                    "issues": issues,
                    "exception": None,
                })

        except Exception as exc:
            # A processing exception is not a valid/invalid prediction.
            # Track it separately rather than corrupting the confusion
            # matrix or terminating the report.
            processing_errors += 1
            category["exceptions"] += 1

            failures.append({
                "index": index,
                "sentence": sentence,
                "expected": (
                    "valid" if expected_valid else "invalid"
                ),
                "got": "exception",
                "error_type": error_type,
                "score": None,
                "issues": [],
                "exception": f"{type(exc).__name__}: {exc}",
            })

    overall_metrics = calculate_metrics(overall)

    category_metrics = {
        category_name: calculate_metrics(counts)
        for category_name, counts in category_results.items()
    }

    # -------------------------
    # Print evaluation report
    # -------------------------
    print("=" * 64)
    print("SANSKRIT GRAMMAR ENGINE EVALUATION REPORT")
    print("=" * 64)

    print(f"\nDataset: {total} test cases")
    print(f"  Expected valid: {valid_sentences}")
    print(f"  Expected invalid: {invalid_sentences}")
    print(f"  Successfully evaluated: {overall['evaluated']}")
    print(f"  Processing exceptions: {processing_errors}")

    print("\nOverall Metrics (successfully evaluated cases):")
    print(
        f"  Accuracy:  "
        f"{format_percentage(overall_metrics['accuracy'])}"
    )
    print(
        f"  Precision (invalid detection): "
        f"{format_percentage(overall_metrics['precision'])}"
    )
    print(
        f"  Recall (invalid detection): "
        f"{format_percentage(overall_metrics['recall'])}"
    )
    print(
        f"  F1 Score: "
        f"{format_percentage(overall_metrics['f1'])}"
    )

    print(
        f"  True Positives: {overall['tp']}"
    )
    print(
        f"  False Positives: {overall['fp']}"
    )
    print(
        f"  True Negatives: {overall['tn']}"
    )
    print(
        f"  False Negatives: {overall['fn']}"
    )

    print("\nCategory-Level Metrics:")

    for category_name, metrics in category_metrics.items():
        print(f"\n  Category: {category_name}")
        print(
            f"    Evaluated: {metrics['evaluated']}"
        )
        print(
            f"    Processing exceptions: {metrics['exceptions']}"
        )
        print(
            f"    Precision: {format_percentage(metrics['precision'])}"
        )
        print(
            f"    Recall: {format_percentage(metrics['recall'])}"
        )
        print(
            f"    F1 Score: {format_percentage(metrics['f1'])}"
        )
        print(
            f"    Accuracy: {format_percentage(metrics['accuracy'])}"
        )
        print(
            f"    TP: {metrics['tp']}, "
            f"FP: {metrics['fp']}, "
            f"FN: {metrics['fn']}, "
            f"TN: {metrics['tn']}"
        )

    print(f"\nIndividual Failures ({len(failures)}):")

    for failure in failures:
        print(
            f"\n  #{failure['index']}: "
            f"{failure['sentence'][:60]!r}"
        )
        print(f"    Expected: {failure['expected']}")
        print(f"    Got: {failure['got']}")
        print(f"    Error Type: {failure['error_type']}")
        print(f"    Score: {failure['score']}")

        if failure["issues"]:
            print(f"    Issues: {failure['issues'][:3]}")

        if failure["exception"]:
            print(f"    Exception: {failure['exception']}")

    # Exceptions count as evaluation failures, but are reported separately
    # from false positives and false negatives.
    regression = (
        overall["fp"] > 0
        or overall["fn"] > 0
        or processing_errors > 0
    )

    print("\n" + "=" * 64)

    if regression:
        print("REGRESSION DETECTED")
        print(
            "Review classification failures, dataset labels, "
            "and processing exceptions."
        )
    else:
        print("No classification failures or processing exceptions detected.")

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
        report = run_evaluation()

        # Exit code 1 indicates test failures or processing errors.
        sys.exit(1 if report["regression"] else 0)

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"\nEvaluation could not run: {exc}", file=sys.stderr)
        sys.exit(2)
