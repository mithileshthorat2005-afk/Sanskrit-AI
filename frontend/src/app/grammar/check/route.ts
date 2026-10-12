/**
 * Grammar check route.
 *
 * Forwards the request to the Python FastAPI backend at /grammar/check,
 * then adapts the Python response into the shape the frontend UI expects
 * (WordAnalysis[], GrammarIssue[], score_details, etc.).
 *
 * This is an adapter — the frontend continues to call POST /grammar/check
 * as before. Only the backend behind the route has changed.
 */

import { NextResponse } from 'next/server';
import sanscript from '@indic-transliteration/sanscript';

// ─────────────────────────────────────────────────────────────
// Configuration
// ─────────────────────────────────────────────────────────────
// The Python backend default port is 8005.
// Override with PYTHON_BACKEND_URL in .env.local if different.
const PYTHON_BACKEND =
  process.env.PYTHON_BACKEND_URL || 'http://localhost:8005';

// ─────────────────────────────────────────────────────────────
// Helpers — Python → UI adapters
// ─────────────────────────────────────────────────────────────

/**
 * Transliterate Devanagari to IAST for the WordAnalysis table.
 */
function transliterate(dev: string): string {
  try {
    return sanscript.t(dev, 'devanagari', 'iast');
  } catch {
    return '';
  }
}

/**
 * Infer an issue category from the human-readable message.
 * The Python engine returns plain strings; the UI expects categories.
 */
function inferCategory(message: string): string {
  const m = message.toLowerCase();
  if (m.includes('purna virama') || m.includes('punctuation')) return 'punctuation';
  if (m.includes('no verb') || m.includes('missing verb')) return 'syntax';
  if (m.includes('agreement')) return 'subject_verb_agreement';
  if (
    m.includes('accusative') ||
    m.includes('vibhakti') ||
    m.includes('dvitiya')
  )
    return 'vibhakti_case';
  return 'syntax';
}

/**
 * Infer severity from the message text.
 * Missing Purna Virama is informational; everything else is an error.
 */
function inferSeverity(message: string): 'error' | 'warning' | 'info' {
  const m = message.toLowerCase();
  if (m.includes('purna virama') || m.includes('punctuation')) return 'info';
  return 'error';
}

/**
 * Convert Prakriya lakara codes to Devanagari labels.
 */
function mapLakara(lakara: string): string | null {
  if (!lakara) return null;
  const map: Record<string, string> = {
    law: 'लट्',
    laG: 'लङ्',
    laN: 'लङ्',
    lfw: 'लृट्',
    luw: 'लुट्',
    low: 'लोट्',
    loW: 'लोट्',
    viDiliG: 'विधिलिङ्',
    viDiliN: 'विधिलिङ्',
  };
  return map[lakara] || lakara;
}

/**
 * Convert the Python `breakdown` array into the UI's `WordAnalysis[]`.
 */
function adaptBreakdownToWords(breakdown: any[]): any[] {
  return (breakdown || []).map((b: any) => {
    const a = b.analysis || {};
    const pos = String(b.pos || 'unknown');
    const isVerb = pos === 'verb';
    const isKnown = b.source && b.source !== 'none';

    return {
      text: String(b.word || ''),
      transliteration: transliterate(String(b.word || '')),
      meaning: String(b.meaning || 'Meaning unavailable'),
      lemma: String(a.lemma || a.root || b.word || ''),
      part_of_speech: pos,
      gender: a.gender || null,
      number: a.number || a.vacana || null,
      case: a.case || null,
      person: a.person || a.purusha || null,
      lakara: isVerb ? mapLakara(String(a.lakara || '')) : null,
      pada: a.pada || null,
      grammar_status: isKnown ? 'valid' : 'uncertain',
      analysis_confidence: isKnown ? 1.0 : 0.3,
    };
  });
}

// ─────────────────────────────────────────────────────────────
// Route handler
// ─────────────────────────────────────────────────────────────
export async function POST(req: Request) {
  try {
    const body = await req.json();
    const username = body.username || 'demo';
    const text = body.text;
    const use_ai = Boolean(body.use_ai);

    if (!text || typeof text !== 'string') {
      return NextResponse.json(
        { detail: 'Valid Sanskrit text is required' },
        { status: 400 }
      );
    }

    // ── Call the Python backend ────────────────────────────────
    let pyResponse: Response;
    try {
      pyResponse = await fetch(`${PYTHON_BACKEND}/grammar/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, text, use_ai }),
      });
    } catch (netErr: any) {
      return NextResponse.json(
        {
          detail: `Cannot reach Python backend at ${PYTHON_BACKEND}. ` +
                  `Make sure it is running on port 8005. (${netErr.message})`,
        },
        { status: 502 }
      );
    }

    if (!pyResponse.ok) {
      const errorText = await pyResponse.text();
      return NextResponse.json(
        {
          detail: `Python backend returned ${pyResponse.status}: ${errorText.slice(0, 300)}`,
        },
        { status: 502 }
      );
    }

    const pyResult = await pyResponse.json();

    // ── If the backend signaled a hard error, wrap it ──────────
    if (pyResult.error) {
      return NextResponse.json({
        status: 'error',
        analysis_method: 'rule_based',
        score: {
          value: 0,
          label: 'Error',
          method: 'rule_based_deduction',
          reliable: false,
        },
        summary: {
          confirmed_errors: 0,
          warnings: 0,
          information_items: 0,
          clause_count: 0,
        },
        original_sentence: text,
        corrected_sentence: text,
        correction_status: 'uncertain',
        correction_summary: String(pyResult.error),
        issues: [],
        words: [],
        clauses: [],
        limitations: [String(pyResult.error)],
        ai_verified: false,
      });
    }

    // ── Adapt Python response to UI shape ──────────────────────
    const scoreValue =
      typeof pyResult.score === 'number' ? pyResult.score : 0;
    const rawIssues: string[] = Array.isArray(pyResult.issues)
      ? pyResult.issues
      : [];
    const words = adaptBreakdownToWords(pyResult.breakdown || []);

    // Convert string issues to GrammarIssue objects
    const issues = rawIssues.map((msg, idx) => ({
      rule_id: `issue_${idx + 1}`,
      category: inferCategory(msg),
      severity: inferSeverity(msg),
      text: '',
      message: msg,
      suggestion: '',
      rule_explanation: '',
      source: pyResult.ai_verified ? 'ai_assisted' : 'rule_engine',
      confidence: 0.9,
    }));

    const confirmedErrors = issues.filter(
      (i) => i.severity === 'error'
    ).length;
    const warnings = issues.filter((i) => i.severity === 'warning').length;
    const infos = issues.filter((i) => i.severity === 'info').length;

    // Score label
    let scoreLabel = 'High correctness';
    if (scoreValue >= 95) scoreLabel = 'High correctness';
    else if (scoreValue >= 75) scoreLabel = 'Moderate correctness';
    else if (scoreValue >= 45) scoreLabel = 'Needs improvement';
    else scoreLabel = 'Significant errors';

    // Correction status
    const originalStripped = text.trim();
    const correctedStripped = String(
      pyResult.corrected_sentence || text
    ).trim();
    let correctionStatus:
      | 'no_correction_needed'
      | 'suggested'
      | 'uncertain' = 'no_correction_needed';

    if (originalStripped !== correctedStripped) {
      correctionStatus = 'suggested';
    }

    const response = {
      status: 'success',
      analysis_method: pyResult.ai_verified ? 'ai_assisted' : 'rule_based',
      score: {
        value: scoreValue,
        label: scoreLabel,
        method: pyResult.ai_verified ? 'ai_normalized' : 'rule_based_deduction',
        reliable: true,
      },
      summary: {
        confirmed_errors: confirmedErrors,
        warnings,
        information_items: infos,
        clause_count: 1,
      },
      original_sentence: text,
      corrected_sentence: pyResult.corrected_sentence || text,
      correction_status: correctionStatus,
      correction_summary:
        pyResult.correction_summary || 'No errors found.',
      issues,
      words,
      clauses: [
        {
          clause_text: text,
          status: confirmedErrors > 0 ? 'error' : 'valid',
          notes: pyResult.correction_summary || '',
        },
      ],
      translation: pyResult.translation || '',
      limitations: [],
      ai_verified: Boolean(pyResult.ai_verified),
    };

    return NextResponse.json(response);
  } catch (err: any) {
    console.error('Grammar route error:', err);
    return NextResponse.json(
      { detail: err.message || 'Grammar check failed' },
      { status: 500 }
    );
  }
}