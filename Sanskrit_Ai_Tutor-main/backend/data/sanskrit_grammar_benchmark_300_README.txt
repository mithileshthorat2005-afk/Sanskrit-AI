Sanskrit Grammar Benchmark — Agreement v1
==========================================

Files
-----
sanskrit_grammar_benchmark_300.json : structured dataset with metadata and 300 cases
sanskrit_grammar_benchmark_300.csv  : spreadsheet-friendly copy of the same cases

Composition
-----------
300 total cases:
- 150 expected valid
- 150 expected invalid
- 10 present-tense parasmaipada verb paradigms
- Subjects span third-, second-, and first-person singular, dual, and plural forms.

Scope
-----
This is a focused subject–verb person/number agreement benchmark. It does not cover all
Sanskrit grammar categories and should not replace the existing 51-case regression dataset.

Important label-quality note
----------------------------
Labels are curated using standard person/number paradigm patterns, but have NOT been
independently reviewed by a Sanskrit specialist. Review before describing scores as
expert-validated accuracy. Unsupported morphology should not automatically be treated
as ungrammatical.

Integration
-----------
The JSON is a standalone format with fields:
id, sentence, expected_valid, category, issue, validation_basis, label_status, source_note.
Your existing evaluator may use a different schema. Map fields deliberately or add an
optional dataset-path/schema adapter without changing the current default dataset.

Do not overwrite backend/data/grammar_test_dataset.json. Keep this benchmark separate.
