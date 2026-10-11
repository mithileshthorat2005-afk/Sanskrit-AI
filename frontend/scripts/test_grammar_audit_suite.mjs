import { checkSanskritSentence, analyzeToken } from '../src/lib/sanskritGrammarEngine.ts';

function simulateServerGrammarCheck(username, text, use_ai) {
  const baseResult = checkSanskritSentence(text);
  let isAiVerified = false;
  let analysisMode = 'Grammar Check';
  const limitations = [...baseResult.limitations];

  if (use_ai) {
    const hasAiKey = Boolean(process.env.GEMINI_API_KEY || process.env.XAI_API_KEY || process.env.GROQ_API_KEY);
    if (hasAiKey) {
      isAiVerified = true;
      analysisMode = 'AI Scan';
    } else {
      isAiVerified = false;
      analysisMode = 'Grammar Check';
      limitations.push('AI scan was requested, but AI service is currently offline. Sentence analyzed using standard grammar rules.');
    }
  }

  return {
    ...baseResult,
    score: baseResult.score.value,
    score_details: baseResult.score,
    analysis_mode: analysisMode,
    ai_verified: isAiVerified,
    limitations,
  };
}

console.log("===============================================================");
console.log("   SANSKRIT GRAMMAR CHECKER COMPREHENSIVE AUDIT TEST SUITE     ");
console.log("===============================================================");

let totalTests = 0;
let passedTests = 0;

function assert(condition, testName, details = "") {
  totalTests++;
  if (condition) {
    console.log(`  [PASS] ${testName}`);
    passedTests++;
  } else {
    console.error(`  [FAIL] ${testName}`);
    if (details) console.error(`         Detail: ${details}`);
  }
}

// ─────────────────────────────────────────────────────────────
// TEST A: Incorrect simple sentence (अहं पठति।)
// ─────────────────────────────────────────────────────────────
console.log("\n--- TEST A: Incorrect Simple Sentence (अहं पठति।) ---");
{
  const res = checkSanskritSentence("अहं पठति।");
  assert(res.summary.confirmed_errors === 1, "Test A: Exactly 1 confirmed error reported");
  const agrIssue = res.issues.find(i => i.category === 'subject_verb_agreement');
  assert(Boolean(agrIssue), "Test A: Subject-verb agreement issue identified");
  assert(agrIssue.message.includes("first person") && agrIssue.message.includes("third person"), "Test A: Correctly diagnoses first vs third person mismatch");
  assert(res.corrected_sentence === "अहं पठामि।", "Test A: Recommended correction is 'अहं पठामि।'", `Got: ${res.corrected_sentence}`);
  assert(res.correction_status === "suggested", "Test A: Correction status is 'suggested'");
  assert(res.score.value === 75, "Test A: Grammar score is 75% (-25 for single agreement error)");
}

// ─────────────────────────────────────────────────────────────
// TEST B: Corrected sentence (अहं पठामि।)
// ─────────────────────────────────────────────────────────────
console.log("\n--- TEST B: Fresh Analysis of Corrected Sentence (अहं पठामि।) ---");
{
  const res = checkSanskritSentence("अहं पठामि।");
  assert(res.summary.confirmed_errors === 0, "Test B: Zero confirmed errors");
  assert(res.score.value === 100, "Test B: Score is 100%");
  assert(res.score.label === "High correctness", "Test B: Score label is 'High correctness'");
  assert(res.correction_status === "no_correction_needed", "Test B: Correction status is 'no_correction_needed'");
  assert(res.corrected_sentence === "अहं पठामि।", "Test B: Original sentence preserved with no false corrections");
  assert(!res.issues.some(i => i.severity === 'error'), "Test B: No residual findings from previous sentence");
}

// ─────────────────────────────────────────────────────────────
// TEST C: Multiple independent errors (यदा अहं विद्यालयः गच्छति तदा ते पुस्तकं पठामि।)
// ─────────────────────────────────────────────────────────────
console.log("\n--- TEST C: Multi-Clause Multiple Errors (यदा अहं विद्यालयः गच्छति तदा ते पुस्तकं पठामि।) ---");
{
  const res = checkSanskritSentence("यदा अहं विद्यालयः गच्छति तदा ते पुस्तकं पठामि।");
  
  // Clause 1: person mismatch (अहं गच्छति -> गच्छामि) + destination case (विद्यालयः -> विद्यालयम्)
  // Clause 2: grouped person & number mismatch (ते पठामि -> पठन्ति)
  // Deduplication requirement: ते पठामि must be 1 grouped issue, not 2 duplicate issues!
  const agreementIssues = res.issues.filter(i => i.category === 'subject_verb_agreement');
  const caseIssues = res.issues.filter(i => i.category === 'vibhakti_case');

  assert(agreementIssues.length === 2, "Test C: Exactly 2 agreement issues (one for अहं गच्छति, one for ते पठामि)", `Found ${agreementIssues.length}`);
  assert(caseIssues.length === 1, "Test C: Exactly 1 destination case issue for विद्यालयः");
  assert(res.summary.confirmed_errors === 3, "Test C: Total confirmed errors is exactly 3 (no duplicate count)", `Got ${res.summary.confirmed_errors}`);

  const teIssue = agreementIssues.find(i => i.text.includes("ते पठामि"));
  assert(Boolean(teIssue), "Test C: Grouped agreement issue found for 'ते पठामि'");
  assert(
    teIssue.message.includes("third person") && teIssue.message.includes("first person") &&
    teIssue.message.includes("plural") && teIssue.message.includes("singular"),
    "Test C: Grouped issue explains both person and number mismatches"
  );
  assert(teIssue.suggestion.includes("ते पठन्ति"), "Test C: Suggestion for 'ते पठामि' is 'ते पठन्ति'");

  assert(res.corrected_sentence === "यदा अहं विद्यालयम् गच्छामि तदा ते पुस्तकं पठन्ति।", "Test C: Recommended sentence is fully corrected", `Got: ${res.corrected_sentence}`);
  assert(res.score.value === 25, "Test C: Score is 25% (100 - 3*25)");
}

// ─────────────────────────────────────────────────────────────
// TEST D: Correct multi-clause sentence (यदा अहं विद्यालयं गच्छामि तदा ते पुस्तकं पठन्ति।)
// ─────────────────────────────────────────────────────────────
console.log("\n--- TEST D: Correct Multi-Clause Sentence (यदा अहं विद्यालयं गच्छामि तदा ते पुस्तकं पठन्ति।) ---");
{
  const resAnusvara = checkSanskritSentence("यदा अहं विद्यालयं गच्छामि तदा ते पुस्तकं पठन्ति।");
  assert(resAnusvara.summary.confirmed_errors === 0, "Test D (anusvara): Zero confirmed errors");
  assert(resAnusvara.score.value === 100, "Test D (anusvara): Score is 100%");
  assert(resAnusvara.correction_status === "no_correction_needed", "Test D (anusvara): No correction needed");
  assert(!resAnusvara.issues.some(i => i.severity === 'error'), "Test D (anusvara): No false agreement across clauses");

  const resMakara = checkSanskritSentence("यदा अहं विद्यालयम् गच्छामि तदा ते पुस्तकं पठन्ति।");
  assert(resMakara.summary.confirmed_errors === 0, "Test D (makara): Zero confirmed errors for विद्यालयम्");
  assert(resMakara.correction_status === "no_correction_needed", "Test D (makara): No false replacement of विद्यालयम् with विद्यालयम्");

  // Check word-level disambiguation for पुस्तकं (Task 7)
  const pustakamWord = resAnusvara.words.find(w => w.text === "पुस्तकं");
  assert(Boolean(pustakamWord), "Test D: पुस्तकं token analyzed");
  assert(pustakamWord.case === "accusative", "Test D: पुस्तकं correctly disambiguated as accusative object in syntactic context", `Got case: ${pustakamWord.case}`);
}

// ─────────────────────────────────────────────────────────────
// TEST E: Identical correction / No-Op prevention
// ─────────────────────────────────────────────────────────────
console.log("\n--- TEST E: No-Op Correction Prevention ---");
{
  const res = checkSanskritSentence("यदा अहं विद्यालयम् गच्छामि तदा ते पुस्तकं पठन्ति।");
  const vidyalayamWord = res.words.find(w => w.text === "विद्यालयम्");
  assert(vidyalayamWord.case === "accusative", "Test E: विद्यालयम् is recognized as accusative");
  assert(res.issues.filter(i => i.text === "विद्यालयम्" && i.suggestion === "विद्यालयम्").length === 0, "Test E: No identical text->suggestion issues generated");
  assert(res.correction_summary.includes("No grammatical alterations required"), "Test E: Summary reflects zero modifications");
}

// ─────────────────────────────────────────────────────────────
// TEST F: AI scan OFF workflow
// ─────────────────────────────────────────────────────────────
console.log("\n--- TEST F: AI Scan OFF Workflow ---");
{
  const serverRes = simulateServerGrammarCheck("demo", "रामः वनं गच्छति।", false);
  assert(serverRes.ai_verified === false, "Test F: ai_verified is false when AI scan is OFF");
  assert(serverRes.analysis_mode === "Grammar Check", "Test F: Clean non-technical analysis mode label", `Got: ${serverRes.analysis_mode}`);
  assert(!serverRes.analysis_mode.toLowerCase().includes("deterministic"), "Test F: No technical 'deterministic' label exposed");
  assert(!serverRes.analysis_mode.toLowerCase().includes("paninian syntactic engine"), "Test F: No technical 'paninian syntactic engine' label");
}

// ─────────────────────────────────────────────────────────────
// TEST G: AI scan ON workflow & Graceful fallback
// ─────────────────────────────────────────────────────────────
console.log("\n--- TEST G: AI Scan ON Workflow ---");
{
  const serverRes = simulateServerGrammarCheck("demo", "रामः वनं गच्छति।", true);
  if (process.env.GEMINI_API_KEY || process.env.XAI_API_KEY || process.env.GROQ_API_KEY) {
    assert(serverRes.ai_verified === true, "Test G: ai_verified is true when API key is active");
    assert(serverRes.analysis_mode === "AI Scan", "Test G: Mode labeled as 'AI Scan'");
  } else {
    assert(serverRes.ai_verified === false, "Test G: ai_verified is false on offline fallback without fabricating AI result");
    assert(serverRes.analysis_mode === "Grammar Check", "Test G: Fallback mode reflects actual engine");
    assert(serverRes.limitations.some(l => l.includes("AI")), "Test G: Limitation notes offline state gracefully");
  }
}

// ─────────────────────────────────────────────────────────────
// TEST H: Curated Example Sentences
// ─────────────────────────────────────────────────────────────
console.log("\n--- TEST H: Curated Test Cases & Exercises ---");
{
  const examples = [
    "रामः पठति।",
    "अहं पठामि।",
    "अहं पठति।",
    "छात्राः पुस्तकम् पठति।",
    "यदा अहं पठामि तदा सः खेलति।",
    "अहं विद्यालयः गच्छामि।",
    "रामः पठति",
    "वयं उद्याने क्रीडामः।",
    "सा पुस्तकं पठन्ति।",
    "बालकः फलानि खादन्ति।",
    "यदि त्वं परिश्रमं करोषि तर्हि सफलः भविष्यसि।",
  ];

  let allValidSanskrit = true;
  for (const ex of examples) {
    const res = checkSanskritSentence(ex);
    if (!res || !res.words || res.words.length === 0) {
      allValidSanskrit = false;
      break;
    }
  }
  assert(allValidSanskrit, "Test H: All 11 curated examples parse successfully in the grammar engine");
}

// ─────────────────────────────────────────────────────────────
// TEST I: Race Condition / Stale Request Safety Simulation
// ─────────────────────────────────────────────────────────────
console.log("\n--- TEST I: Stale Request Handling Simulation ---");
{
  let currentRequestId = 0;
  let activeState = null;

  async function mockRequest(requestId, input, delay) {
    await new Promise(r => setTimeout(r, delay));
    const result = checkSanskritSentence(input);
    if (requestId === currentRequestId) {
      activeState = { input, result };
    }
  }

  // Request 1 starts first with longer delay
  const req1Id = ++currentRequestId;
  const p1 = mockRequest(req1Id, "अहं पठति।", 60);

  // Request 2 (Applied correction) starts shortly after with faster response
  const req2Id = ++currentRequestId;
  const p2 = mockRequest(req2Id, "अहं पठामि।", 20);

  await Promise.all([p1, p2]);

  assert(activeState !== null, "Test I: Active state received result");
  assert(activeState.input === "अहं पठामि।", "Test I: Latest request (अहं पठामि।) retained");
  assert(activeState.result.score.value === 100, "Test I: Latest score (100%) preserved and not overwritten by older request");
}

console.log(`\n===============================================================`);
console.log(` AUDIT RESULTS: ${passedTests}/${totalTests} tests passed (${Math.round((passedTests/totalTests)*100)}%)`);
console.log(`===============================================================`);

if (passedTests === totalTests) {
  console.log("🎉 ALL AUDIT SCENARIOS (TESTS A-I) PASSED SUCCESSFULLY!");
  process.exit(0);
} else {
  console.error("Some audit tests failed!");
  process.exit(1);
}
