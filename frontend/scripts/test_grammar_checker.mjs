import { checkSanskritSentence } from '../src/lib/sanskritGrammarEngine.ts';

console.log("=== RUNNING SANSKRIT GRAMMAR ENGINE TEST SUITE ===");

let passed = 0;
let total = 0;

function assert(condition, message) {
  total++;
  if (condition) {
    console.log(`✅ [PASS] ${message}`);
    passed++;
  } else {
    console.error(`❌ [FAIL] ${message}`);
  }
}

// ── TEST 1: Correct simple sentence: रामः पठति। ──
{
  const res = checkSanskritSentence("रामः पठति।");
  assert(res.status === 'success', "Test 1: Status is success");
  assert(res.summary.confirmed_errors === 0, "Test 1: Zero confirmed grammatical errors");
  assert(res.score.value === 100, "Test 1: Score is 100%");
  assert(res.score.label === "High correctness", "Test 1: Score label is 'High correctness'");
  assert(res.correction_status === "no_correction_needed", "Test 1: No correction needed");
  assert(res.words.length === 2, "Test 1: Decomposes into 2 words");
  assert(res.words[0].meaning.includes("Rama"), "Test 1: Word 1 meaning includes Rama");
  assert(res.words[1].meaning.includes("read"), "Test 1: Word 2 meaning includes read");
}

// ── TEST 2: Subject–verb disagreement: अहं पठति। ──
{
  const res = checkSanskritSentence("अहं पठति।");
  assert(res.summary.confirmed_errors > 0, "Test 2: Confirmed error detected");
  const agrIssue = res.issues.find(i => i.category === 'subject_verb_agreement');
  assert(Boolean(agrIssue), "Test 2: Subject-verb agreement issue found");
  assert(agrIssue.message.includes("first person") && agrIssue.message.includes("third person"), "Test 2: Explains first vs third person mismatch");
  assert(res.corrected_sentence.includes("पठामि"), "Test 2: Suggested correction uses पठामि");
  assert(res.score.value < 100, "Test 2: Score deducted appropriately");
}

// ── TEST 3: Multiple clauses: यदा अहं पठामि तदा सः खेलति। ──
{
  const res = checkSanskritSentence("यदा अहं पठामि तदा सः खेलति।");
  assert(res.summary.confirmed_errors === 0, "Test 3: Zero false-positive agreement errors across multiple clauses");
  assert(res.clauses.length >= 2, "Test 3: Segmented into at least 2 distinct clauses");
  assert(res.score.value === 100, "Test 3: Score is 100%");
  assert(res.correction_status === "no_correction_needed", "Test 3: No false correction applied");
}

// ── TEST 4: Missing punctuation: रामः पठति ──
{
  const res = checkSanskritSentence("रामः पठति");
  assert(res.summary.confirmed_errors === 0, "Test 4: Missing punctuation is not counted as a grammatical error");
  const punctIssue = res.issues.find(i => i.category === 'punctuation');
  assert(Boolean(punctIssue), "Test 4: Punctuation advisory reported");
  assert(punctIssue.severity === 'info', "Test 4: Punctuation is advisory (severity: info)");
  assert(res.score.value === 95, "Test 4: Only advisory deduction (-5) applied (score 95%)");
}

// ── TEST 5: Unknown word ──
{
  const res = checkSanskritSentence("रामः खग्गपठति।");
  const unknownWord = res.words.find(w => w.text === "खग्गपठति");
  assert(Boolean(unknownWord), "Test 5: Token analyzed");
  assert(unknownWord.grammar_status === 'uncertain', "Test 5: Unindexed word marked as uncertain without crashing");
  assert(res.limitations.length > 0, "Test 5: System logs token limitation gracefully");
}

// ── TEST 6: Already correct sentence: अहं पठामि। ──
{
  const res = checkSanskritSentence("अहं पठामि।");
  assert(res.summary.confirmed_errors === 0, "Test 6: Zero errors for अहं पठामि।");
  assert(res.correction_status === "no_correction_needed", "Test 6: Correction status is no_correction_needed");
  assert(res.corrected_sentence === "अहं पठामि।", "Test 6: Original sentence strictly preserved");
}

// ── TEST 7: Multi-clause conditional with future: यदि त्वं परिश्रमं करोषि तर्हि सफलः भविष्यसि। ──
{
  const res = checkSanskritSentence("यदि त्वं परिश्रमं करोषि तर्हि सफलः भविष्यसि।");
  assert(res.clauses.length >= 2, "Test 7: Multi-clause conditional parsed into clauses");
  assert(res.summary.confirmed_errors === 0, "Test 7: No false agreement errors in conditional sentence");
}

// ── TEST 8: Vibhakti destination error: अहं विद्यालयः गच्छामि। ──
{
  const res = checkSanskritSentence("अहं विद्यालयः गच्छामि।");
  const vibIssue = res.issues.find(i => i.category === 'vibhakti_case');
  assert(Boolean(vibIssue), "Test 8: Accusative motion destination error caught");
  assert(res.corrected_sentence.includes("विद्यालयम्"), "Test 8: Destination corrected to accusative विद्यालयम्");
}

console.log(`\n=== RESULTS: ${passed}/${total} assertions passed ===`);
if (passed === total) {
  console.log("🎉 ALL SANSKRIT GRAMMAR ENGINE TESTS PASSED!");
  process.exit(0);
} else {
  console.error("Some tests failed!");
  process.exit(1);
}
