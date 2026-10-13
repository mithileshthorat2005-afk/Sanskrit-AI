"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Sidebar from "@/components/Sidebar";
import SanskritInput from "@/components/SanskritInput";
import AudioPronounceButton from "@/components/AudioPronounceButton";
import { motion, AnimatePresence } from "framer-motion";
import sanscript from "@indic-transliteration/sanscript";
import {
  ShieldCheck,
  Sparkles,
  AlertCircle,
  FileText,
  Loader2,
  Zap
} from "lucide-react";

// ── Table helpers (Layout A) ──────────────────────────────────
// IAST rendering reuses the project's existing transliteration dependency.
const toIAST = (word: string): string => {
  try {
    const clean = String(word || "").replace(/[।॥.,!?;|]+$/, "");
    if (!clean) return "—";
    return sanscript.t(clean, "devanagari", "iast");
  } catch {
    return "—";
  }
};

// Stacked detail chips (values only) for the Grammar Details column.
const grammarDetailChips = (item: any): string[] => {
  const skip = new Set(["pos", "meaning", "note", "root", "root_slp1", "stem", "raw_verb_with_markers", "derivation_steps", "rules_applied"]);
  const chips: string[] = [];
  for (const [key, value] of Object.entries(item?.analysis || {})) {
    if (skip.has(key)) continue;
    const text = Array.isArray(value) ? value.join(", ") : String(value);
    if (text) chips.push(text);
  }
  return chips.length ? chips : ["—"];
};

// Words the backend could not resolve (source "none" / unknown POS).
const isUnresolved = (item: any): boolean =>
  item?.source === "none" || item?.pos === "unknown";

// Score ring for the GRAMMAR SCORE card.
const ScoreRing = ({ value }: { value: number }) => {
  const r = 34;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div style={{ position: "relative", width: "84px", height: "84px", flexShrink: 0 }}>
      <svg width="84" height="84" viewBox="0 0 84 84">
        <circle cx="42" cy="42" r={r} fill="none" stroke="var(--border-soft)" strokeWidth="9" />
        <circle
          cx="42" cy="42" r={r} fill="none" stroke="#27ae60" strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c}
          transform="rotate(-90 42 42)"
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: "800", fontSize: "1.15rem", color: "#27ae60" }}>
        {value}%
      </div>
    </div>
  );
};

export default function Grammar() {
  const { user, loading: authLoading } = useAuth();
  const [inputText, setInputText] = useState("");
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [useAi, setUseAi] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const router = useRouter();

  const fetchHistory = async () => {
    if (!user) return;
    setHistoryLoading(true);
    try {
      const res = await api.user.getGrammarHistory(10);
      setHistory(Array.isArray(res) ? res : []);
    } catch (err) {
      console.error("Failed to load grammar history", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (user) fetchHistory();
  }, [user]);

  const handleCheck = async () => {
    if (!inputText) return;
    setLoading(true);
    setAnalysis(null);
    try {
      const res = await api.tools.checkGrammar(inputText, useAi);
      setAnalysis(res);
      if (user) fetchHistory();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard API unavailable (e.g. non-secure context): fallback.
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!user) return null;

  return (
    <div className="page-layout">
      <Sidebar user={user} />

      <main className="main-content">
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ marginBottom: '40px' }}
        >
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Vyakaraņa Check</h1>
          <p style={{ color: 'var(--text-dim)' }}>Precision analysis of your Sanskrit construction and syntax.</p>
        </motion.header>

        <section className="grid" style={{ gridTemplateColumns: '1fr 1.2fr', gap: '30px' }}>

          <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}>
            <div className="zen-card" style={{ padding: '30px', marginBottom: '30px' }}>
              <div className="flex items-center gap-2 mb-6" style={{ color: 'var(--primary)' }}>
                <FileText size={20} />
                <h3 style={{ margin: 0 }}>Input Sentence</h3>
              </div>
              <div style={{ position: 'relative', width: '100%', minHeight: '200px', marginBottom: '24px' }}>
                <SanskritInput
                  value={inputText}
                  onChange={(val) => setInputText(val)}
                  placeholder="रामः वनं गच्छति..."
                  showLabel={false}
                  style={{
                    fontSize: '2rem',
                    lineHeight: '1.5',
                    background: 'var(--bg-main)',
                    border: 'none',
                    padding: '30px',
                    color: 'var(--text-main)',
                    minHeight: '200px'
                  }}
                  className="devanagari"
                />
              </div>

              <div className="flex justify-between items-center">
                {/* Custom Framer Motion Toggle Switch */}
                <div
                  className="flex items-center gap-3 cursor-pointer group"
                  onClick={() => setUseAi(!useAi)}
                >
                  <div
                    style={{
                      width: '46px',
                      height: '24px',
                      borderRadius: '24px',
                      background: useAi ? 'var(--primary)' : 'var(--border-soft)',
                      display: 'flex',
                      alignItems: 'center',
                      padding: '2px',
                      transition: 'background 0.3s ease'
                    }}
                  >
                    <motion.div
                      layout
                      animate={{ x: useAi ? 22 : 0 }}
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      style={{
                        width: '20px',
                        height: '20px',
                        borderRadius: '50%',
                        background: 'white',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                      }}
                    />
                  </div>
                  <div>
                    <div style={{
                      fontSize: '0.75rem',
                      fontWeight: '800',
                      color: useAi ? 'var(--primary)' : 'var(--text-dim)',
                      textTransform: 'uppercase',
                      letterSpacing: '1px',
                      transition: 'color 0.3s ease'
                    }}>
                      AI Scan
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-light)', marginTop: '2px' }}>
                      {useAi ? "Grok verification" : "Standard grammar rules"}
                    </div>
                  </div>
                </div>

                <button
                  className="btn-primary"
                  onClick={handleCheck}
                  disabled={loading || !inputText}
                  style={{ padding: '12px 30px', display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  {loading ? <Loader2 className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
                  <span>{loading ? "Checking..." : "Check Grammar"}</span>
                </button>
              </div>
            </div>

            <div className="zen-card" style={{ padding: '24px' }}>
              <div className="flex justify-between items-center mb-4">
                <h4 style={{ fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', margin: 0 }}>Example Sentences</h4>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-light)' }}>Click to load</span>
              </div>
              <div className="flex flex-col gap-3" style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: '10px' }}>
                {[
                  "रामः वनं गच्छति।",
                  "सीता फलं खादति।",
                  "बालकाः पठन्ति।",
                  "अहं विद्यालयं गच्छामि।",
                  "सः पुस्तकं पठति।",
                  "वयं उद्याने क्रीडामः।",
                  "माता भोजनं पचति।",
                  "बालकाः कक्षायां उपविशन्ति।",
                  "यदा अहं विद्यालयं गच्छामि तदा मित्राणि मिलन्ति।",
                  "यदि त्वं परिश्रमं करोषि तर्हि सफलः भविष्यसि।",
                  "शिक्षकः विद्यार्थिभ्यः ज्ञानं ददाति।",
                  "अहं गृहकार्यं समाप्त्वा विश्रामं करोमि।",
                  "यः सत्यम् वदति सः सर्वेषां विश्वासं लभते।",
                  "अहं विद्यालयः गच्छामि।",
                  "सा पुस्तकं पठन्ति।",
                  "वयं उद्यानं क्रीडामि।",
                  "बालकः फलानि खादन्ति।",
                  "शिक्षकाः पाठं पठति।",
                  "मम मित्रः विद्यालये गच्छन्ति।",
                  "अहं जलं पिबसि।",
                  "ते गृहं गच्छामि।",
                  "छात्राः पुस्तकम् पठति।",
                  "यदा अहं पठामि तदा सः खेलति अस्ति。"
                ].map((t, idx) => (
                  <div
                    key={t}
                    className="flex items-center justify-between gap-2"
                    style={{ border: '1px solid var(--border-soft)', borderRadius: '12px', padding: '8px 12px' }}
                  >
                    <button
                      className="devanagari"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.9rem', color: 'var(--primary)', fontWeight: '600', textAlign: 'left', flex: 1 }}
                      onClick={() => setInputText(t)}
                      title="Load into checker"
                    >
                      {t}
                    </button>
                    <AudioPronounceButton text={t} size={16} title={`Listen to example ${idx + 1}`} />
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-light)', whiteSpace: 'nowrap' }}>Example {idx + 1}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Result Area */}
          <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}>
            <div className="zen-card" style={{ padding: '40px', minHeight: '100%' }}>
              <AnimatePresence mode="wait">
                {!analysis ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-light)', textAlign: 'center' }}>
                    <Sparkles size={40} style={{ opacity: 0.1, marginBottom: '20px' }} />
                    <p>Enter a sentence and verify to see the analysis table.</p>
                  </div>
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    {/* ── Score row: ring + counts ── */}
                    <div className="grid" style={{ gridTemplateColumns: '1.5fr 1fr', gap: '16px', marginBottom: '24px' }}>
                      <div className="flex items-center gap-4 p-5" style={{ background: 'var(--bg-main)', borderRadius: '20px', border: '1px solid var(--border-soft)' }}>
                        <ScoreRing value={analysis.score} />
                        <div>
                          <div style={{ fontSize: '0.7rem', fontWeight: '800', color: 'var(--text-light)', letterSpacing: '1px' }}>GRAMMAR SCORE</div>
                          <div style={{ fontSize: '1.05rem', color: '#27ae60', fontWeight: '600', lineHeight: '1.3' }}>
                            {analysis.breakdown.some((b: any) => isUnresolved(b)) ? 'Unable to determine reliably' : (analysis.correction_summary || 'Analysis complete')}
                          </div>
                          {analysis.breakdown.some((b: any) => isUnresolved(b)) && (
                            <div style={{ fontSize: '0.8rem', color: 'var(--primary)', marginTop: '2px' }}>Notice: Limited lexicon confidence</div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center justify-around p-5" style={{ background: 'var(--bg-main)', borderRadius: '20px', border: '1px solid var(--border-soft)' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '0.65rem', fontWeight: '800', color: 'var(--text-light)', letterSpacing: '1px' }}>CONFIRMED ERRORS</div>
                          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#27ae60' }}>{analysis.issues.length}</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '0.65rem', fontWeight: '800', color: 'var(--text-light)', letterSpacing: '1px' }}>ADVISORIES</div>
                          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: 'var(--text-light)' }}>
                            {(analysis.corrected_sentence && analysis.corrected_sentence !== inputText ? 1 : 0) +
                              (analysis.recommendation && analysis.recommendation.title ? 1 : 0) +
                              (analysis.skipped_issues ? analysis.skipped_issues.length : 0)}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* ── Original sentence ── */}
                    <div style={{ fontSize: '0.7rem', fontWeight: '800', color: 'var(--text-light)', letterSpacing: '1px', marginBottom: '8px' }}>ORIGINAL SENTENCE</div>
                    <div className="flex items-center gap-3 p-5 mb-6" style={{ border: '1px solid var(--border-soft)', borderRadius: '16px' }}>
                      <span className="devanagari" style={{ fontSize: '1.5rem', color: 'var(--text-main)' }}>{inputText}</span>
                      <AudioPronounceButton text={inputText} size={18} title="Listen to original sentence" />
                    </div>

                    {/* ── Verified formulation ── */}
                    <div className="p-5 mb-6" style={{ background: 'rgba(39, 174, 96, 0.05)', border: '1px solid rgba(39, 174, 96, 0.2)', borderRadius: '16px' }}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2" style={{ fontSize: '0.75rem', fontWeight: '800', color: '#27ae60', letterSpacing: '1px' }}>
                          <Sparkles size={14} /> VERIFIED FORMULATION
                        </div>
                        <button
                          onClick={() => handleCopy(analysis.corrected_sentence || inputText)}
                          style={{ background: 'none', border: '1px solid var(--border-soft)', borderRadius: '8px', padding: '4px 10px', fontSize: '0.7rem', fontWeight: '700', color: 'var(--text-dim)', cursor: 'pointer' }}
                          title="Copy verified formulation"
                        >
                          {copied ? 'Copied ✓' : '⧉ Copy'}
                        </button>
                      </div>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="devanagari" style={{ fontSize: '1.8rem', fontWeight: '700', color: 'var(--text-main)' }}>
                          {analysis.corrected_sentence || inputText}
                        </span>
                        <AudioPronounceButton text={analysis.corrected_sentence || inputText} size={18} title="Listen to verified formulation" />
                        <button
                          onClick={() => setInputText(analysis.corrected_sentence || inputText)}
                          style={{ padding: '6px 14px', background: 'var(--primary)', color: 'white', border: 'none', borderRadius: '10px', cursor: 'pointer', fontWeight: '700', fontSize: '0.7rem' }}
                        >
                          USE THIS
                        </button>
                      </div>
                      {analysis.correction_summary && (
                        <p style={{ fontSize: '0.9rem', color: 'var(--text-dim)', margin: 0 }}>{analysis.correction_summary}</p>
                      )}
                    </div>

                    {/* ── Detected issues ── */}
                    <div className="mb-8">
                      <div className="flex justify-between items-center mb-4">
                        <h4 style={{ fontSize: '0.9rem', color: 'var(--text-light)', textTransform: 'uppercase', letterSpacing: '1px', margin: 0 }}>Detected Issues</h4>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{analysis.issues.length} finding{analysis.issues.length === 1 ? '' : 's'}</span>
                      </div>
                      {analysis.issues.length > 0 ? (
                        <div className="flex flex-col gap-3">
                          {analysis.issues.map((issue: string, i: number) => (
                            <div key={i} className="flex items-center gap-3 p-4 rounded-xl" style={{ border: '1.5px solid rgba(192, 90, 43, 0.1)', color: 'var(--primary)', background: 'rgba(192, 90, 43, 0.02)' }}>
                              <AlertCircle size={18} />
                              <span style={{ fontSize: '0.95rem' }}>{issue}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex items-center gap-3 p-4 rounded-xl" style={{ background: 'rgba(39, 174, 96, 0.07)', color: '#27ae60', fontWeight: '600' }}>
                          <span style={{ width: '22px', height: '22px', borderRadius: '50%', border: '2px solid #27ae60', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', flexShrink: 0 }}>✓</span>
                          Linguistic concord and syntactic agreement are verified.
                        </div>
                      )}
                    </div>

                    {/* ── Word-by-word analysis ── */}
                    <div className="flex justify-between items-center mb-4">
                      <h4 style={{ fontSize: '0.9rem', color: 'var(--text-light)', textTransform: 'uppercase', letterSpacing: '1px', margin: 0 }}>Word-by-word Analysis</h4>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{analysis.word_count} tokens</span>
                    </div>
                    <div style={{ overflowX: 'auto', marginBottom: '40px' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                        <thead>
                          <tr style={{ background: 'var(--bg-main)' }}>
                            {['Word', 'IAST', 'English Meaning', 'POS/Base', 'Grammar Details', 'Status'].map((h) => (
                              <th key={h} style={{ textAlign: 'left', padding: '12px 14px', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-light)', borderBottom: '1px solid var(--border-soft)', whiteSpace: 'nowrap' }}>
                                {h}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {analysis.breakdown.map((item: any, i: number) => {
                            return (
                              <tr key={i} style={{ borderBottom: '1px solid var(--border-soft)' }}>
                                <td className="devanagari" style={{ padding: '12px 14px', fontSize: '1.25rem', color: 'var(--primary)', whiteSpace: 'nowrap' }}>
                                  {item.word}
                                  <AudioPronounceButton text={item.word || ''} size={14} title={`Pronounce ${item.word || 'Sanskrit word'}`} />
                                </td>
                                <td style={{ padding: '12px 14px', fontStyle: 'italic', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>{toIAST(item.word)}</td>
                                <td style={{ padding: '12px 14px', fontWeight: '600' }}>{item.meaning}</td>
                                <td style={{ padding: '12px 14px', minWidth: '110px' }}>
                                  <div style={{ fontWeight: '700', textTransform: 'capitalize' }}>{item.pos}</div>
                                  {(item.analysis?.root || item.analysis?.stem) && (
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>Base: {item.analysis.root || item.analysis.stem}</div>
                                  )}
                                </td>
                                <td style={{ padding: '12px 14px', minWidth: '150px' }}>
                                  <div className="flex flex-col gap-1 items-start">
                                    {grammarDetailChips(item).map((chip, ci) => (
                                      <span key={ci} style={{ padding: '2px 8px', background: 'var(--bg-main)', border: '1px solid var(--border-soft)', borderRadius: '6px', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                                        {chip}
                                      </span>
                                    ))}
                                  </div>
                                </td>
                                <td style={{ padding: '12px 14px' }}>
                                  {isUnresolved(item) ? (
                                    <span style={{ padding: '4px 10px', borderRadius: '8px', fontSize: '0.7rem', fontWeight: '900', textTransform: 'uppercase', whiteSpace: 'nowrap', background: 'rgba(245, 158, 11, 0.12)', color: '#d97706' }}>
                                      Uncertain
                                    </span>
                                  ) : (
                                    <span style={{ padding: '4px 10px', borderRadius: '8px', fontSize: '0.7rem', fontWeight: '900', textTransform: 'uppercase', whiteSpace: 'nowrap', background: 'rgba(39, 174, 96, 0.1)', color: '#27ae60' }}>
                                      Valid
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    {/* ── Advisory details (recommendation + unmapped notes) ── */}
                    {((analysis.recommendation && analysis.recommendation.title) ||
                      (analysis.skipped_issues && analysis.skipped_issues.length > 0)) && (
                      <div className="mb-10">
                        <div className="flex flex-col gap-3">
                          {analysis.recommendation && analysis.recommendation.title && (
                            <div className="p-4 rounded-xl" style={{ background: 'rgba(var(--primary-rgb), 0.04)', border: '1px solid var(--border-soft)', fontSize: '0.9rem', color: 'var(--text-dim)' }}>
                              Recommended next step: <strong style={{ color: 'var(--text-main)' }}>{analysis.recommendation.title}</strong>
                              {analysis.recommendation.description ? ` — ${analysis.recommendation.description}` : ''}
                            </div>
                          )}
                          {(analysis.skipped_issues || []).map((s: any, i: number) => (
                            <div key={i} className="p-4 rounded-xl" style={{ background: 'var(--bg-main)', border: '1px solid var(--border-soft)', fontSize: '0.9rem', color: 'var(--text-dim)' }}>
                              Note: {s.reason || s.raw_error_type}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* ── Analysis meta (extra response fields) ── */}
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>
                      {analysis.analysis_mode}
                      {typeof analysis.word_count === 'number' ? ` • ${analysis.word_count} words` : ''}
                      {analysis.source_counts ? ` • sources: ${Object.entries(analysis.source_counts).map(([k, v]) => `${k} ${v}`).join(' • ')}` : ''}
                      {analysis.ai_verified ? ' • AI verified' : ''}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Previous Analyses (per-user history from the backend) */}
            <div className="zen-card" style={{ padding: '30px', marginTop: '30px' }}>
              <h4 className="mb-4" style={{ fontSize: '0.9rem', color: 'var(--text-light)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                Previous Analyses
              </h4>
              {historyLoading ? (
                <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>Loading history...</p>
              ) : history.length === 0 ? (
                <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>No previous analyses yet. Your checks will appear here.</p>
              ) : (
                <div className="flex flex-col gap-3" style={{ maxHeight: '320px', overflowY: 'auto', paddingRight: '6px' }}>
                  {history.map((h: any) => (
                    <div
                      key={h.id}
                      className="flex items-center gap-2"
                      style={{ border: '1px solid var(--border-soft)', borderRadius: '12px', padding: '12px 16px' }}
                    >
                      <button
                        className="btn-secondary"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', padding: 0, flex: 1 }}
                        onClick={() => setInputText(h.input_text)}
                        title="Load this sentence into the checker"
                      >
                        <div className="devanagari" style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>{h.input_text}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                          Score {Math.round(h.score_percent)}% • {h.issue_count} issue{h.issue_count === 1 ? '' : 's'}
                          {h.created_at ? ` • ${new Date(h.created_at).toLocaleString()}` : ''}
                        </div>
                      </button>
                      <AudioPronounceButton text={h.input_text} size={16} title="Listen to this sentence" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </section>
      </main>
    </div>
  );
}
