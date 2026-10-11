"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import SanskritInput from "@/components/SanskritInput";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  Sparkles,
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle2,
  FileText,
  Loader2,
  Zap,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Layers,
  ArrowRight
} from "lucide-react";
import AudioPronounceButton from "@/components/AudioPronounceButton";
export default function Grammar() {
  const [user, setUser] = useState<any>(null);
  const [inputText, setInputText] = useState("");
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [useAi, setUseAi] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const requestIdRef = useRef(0);
  const router = useRouter();

  // Mount user safely
  useEffect(() => {
    let isMounted = true;
    let userData: any = null;
    try {
      const storedUser = localStorage.getItem("user");
      if (storedUser) userData = JSON.parse(storedUser);
    } catch (e) {
      console.error(e);
    }
    if (!userData) {
      userData = { username: "demo", level: "beginner", role: "student" };
      localStorage.setItem("user", JSON.stringify(userData));
    }
    if (isMounted) setUser(userData);
    return () => { isMounted = false; };
  }, []);

  const runCheck = async (textToCheck: string, aiMode: boolean) => {
    const trimmed = textToCheck.trim();
    if (!trimmed) return;

    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setAnalysis(null);

    try {
      const res = await api.tools.checkGrammar(user?.username || "demo", trimmed, aiMode);
      if (currentRequestId === requestIdRef.current) {
        setAnalysis(res);
      }
    } catch (err) {
      if (currentRequestId === requestIdRef.current) {
        console.error("Grammar analysis error:", err);
      }
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  };

  const handleCheck = () => {
    runCheck(inputText, useAi);
  };

  const handleApplyCorrection = (correctedText: string) => {
    if (!correctedText) return;
    setInputText(correctedText);
    runCheck(correctedText, useAi);
  };

  const handleSelectExample = (text: string) => {
    setInputText(text);
  };

  const copyToClipboard = (text: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!user) return null;

  // Resolve score values
  const scoreVal = analysis?.score_details?.value ?? analysis?.score ?? 0;
  const scoreLabel = analysis?.score_details?.label ?? (scoreVal >= 90 ? "High correctness" : scoreVal >= 75 ? "Moderate correctness" : "Needs improvement");
  const isReliable = analysis?.score_details?.reliable ?? true;
  const confirmedErrors = analysis?.summary?.confirmed_errors ?? (Array.isArray(analysis?.issues) ? analysis.issues.filter((i: any) => i.severity === 'error').length : 0);
  const warningCount = analysis?.summary?.warnings ?? (Array.isArray(analysis?.issues) ? analysis.issues.filter((i: any) => i.severity === 'warning').length : 0);
  const infoCount = analysis?.summary?.information_items ?? (Array.isArray(analysis?.issues) ? analysis.issues.filter((i: any) => i.severity === 'info').length : 0);

  // Score colors
  const getScoreColor = (val: number) => {
    if (val >= 90) return "#10B981"; // Emerald green
    if (val >= 75) return "#F59E0B"; // Amber
    if (val >= 50) return "var(--primary)"; // Saffron orange
    return "#EF4444"; // Red
  };

  return (
    <div className="page-layout">
      <Sidebar user={user} />

      <main className="main-content">
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ marginBottom: "32px" }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="logo-box" style={{ background: "linear-gradient(135deg, var(--primary), var(--secondary))" }}>
              <ShieldCheck size={24} />
            </div>
            <div>
              <span style={{ color: "var(--primary)", fontWeight: 800, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "1.5px" }}>
                Sanskrit AI Tutor
              </span>
              <h1 style={{ fontSize: "2.4rem", margin: 0, fontWeight: 700 }}>Sanskrit Grammar Checker</h1>
            </div>
          </div>
          <p style={{ color: "var(--text-dim)", fontSize: "1rem", maxWidth: "750px" }}>
            Check your Sanskrit sentence, understand grammatical errors, and discover corrections with explanations.
          </p>
        </motion.header>

        <section className="grid" style={{ gridTemplateColumns: "1fr 1.3fr", gap: "28px", alignItems: "start" }}>

          {/* LEFT PANEL: Input & Practice Sentences */}
          <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}>
            <div className="zen-card" style={{ padding: "28px", marginBottom: "24px" }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2" style={{ color: "var(--primary)" }}>
                  <FileText size={18} />
                  <h3 style={{ margin: 0, fontSize: "1.2rem" }}>Sentence Input</h3>
                </div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-light)" }}>Devanagari script</span>
              </div>

              <div style={{ position: "relative", width: "100%", minHeight: "180px", marginBottom: "20px" }}>
                <SanskritInput
                  value={inputText}
                  onChange={(val) => setInputText(val)}
                  placeholder="रामः वनं गच्छति..."
                  showLabel={false}
                  style={{
                    fontSize: "1.8rem",
                    lineHeight: "1.6",
                    background: "var(--bg-main)",
                    border: "1px solid var(--border-soft)",
                    borderRadius: "16px",
                    padding: "24px",
                    color: "var(--text-main)",
                    minHeight: "180px",
                    width: "100%"
                  }}
                  className="devanagari"
                />
              </div>

              {/* Mode Toggle & Submit Button */}
              <div className="flex justify-between items-center flex-wrap gap-4">
                <div
                  className="flex items-center gap-3 cursor-pointer group select-none"
                  onClick={() => setUseAi(!useAi)}
                  title="Toggle AI assistance"
                >
                  <div
                    style={{
                      width: "48px",
                      height: "26px",
                      borderRadius: "20px",
                      background: useAi ? "var(--primary)" : "var(--border-soft)",
                      display: "flex",
                      alignItems: "center",
                      padding: "2px",
                      transition: "background 0.3s ease"
                    }}
                  >
                    <motion.div
                      layout
                      animate={{ x: useAi ? 22 : 0 }}
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      style={{
                        width: "22px",
                        height: "22px",
                        borderRadius: "50%",
                        background: "white",
                        boxShadow: "0 2px 4px rgba(0,0,0,0.2)"
                      }}
                    />
                  </div>
                  <div className="flex flex-col">
                    <span style={{
                      fontSize: "0.75rem",
                      fontWeight: 800,
                      color: useAi ? "var(--primary)" : "var(--text-dim)",
                      textTransform: "uppercase",
                      letterSpacing: "0.8px"
                    }}>
                      AI Scan
                    </span>
                    <span style={{ fontSize: "0.68rem", color: "var(--text-light)" }}>
                      {useAi ? "AI-assisted scan" : "Standard grammar rules"}
                    </span>
                  </div>
                </div>

                <button
                  className="btn-primary"
                  onClick={handleCheck}
                  disabled={loading || !inputText.trim()}
                  style={{ padding: "12px 28px", display: "flex", alignItems: "center", gap: "8px" }}
                >
                  {loading ? (
                    <Loader2 className="animate-spin" size={18} />
                  ) : useAi ? (
                    <Zap size={18} fill="currentColor" />
                  ) : (
                    <ShieldCheck size={18} />
                  )}
                  <span>{loading ? "Analyzing Sentence..." : useAi ? "AI Grammar Check" : "Check Grammar"}</span>
                </button>
              </div>
            </div>

            {/* CURATED PRACTICE PRESETS WITHOUT ANSWER SPOILERS */}
            <div className="zen-card" style={{ padding: "24px" }}>
              <div className="flex items-center justify-between mb-3">
                <h4 style={{ fontSize: "0.8rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "1px", margin: 0 }}>
                  Example Sentences
                </h4>
                <span style={{ fontSize: "0.7rem", color: "var(--text-light)" }}>Click to load</span>
              </div>

              <div className="flex flex-col gap-2" style={{ maxHeight: "380px", overflowY: "auto", paddingRight: "6px" }}>
                {[
                  { text: "रामः पठति।", label: "Example 1" },
                  { text: "अहं पठामि।", label: "Example 2" },
                  { text: "अहं पठति।", label: "Example 3" },
                  { text: "छात्राः पुस्तकम् पठति।", label: "Example 4" },
                  { text: "यदा अहं पठामि तदा सः खेलति।", label: "Example 5" },
                  { text: "अहं विद्यालयः गच्छामि।", label: "Example 6" },
                  { text: "रामः पठति", label: "Example 7" },
                  { text: "वयं उद्याने क्रीडामः।", label: "Example 8" },
                  { text: "सा पुस्तकं पठन्ति।", label: "Example 9" },
                  { text: "बालकः फलानि खादन्ति।", label: "Example 10" },
                  { text: "यदि त्वं परिश्रमं करोषि तर्हि सफलः भविष्यसि।", label: "Example 11" },
                ].map((item) => (
                  <button
                    key={item.text}
                    className="btn-secondary"
                    style={{
                      fontSize: "0.85rem",
                      padding: "10px 14px",
                      border: "1px solid var(--border-soft)",
                      color: "var(--text-main)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      textAlign: "left",
                      background: inputText === item.text ? "rgba(var(--primary-rgb), 0.08)" : "var(--bg-main)"
                    }}
                    onClick={() => handleSelectExample(item.text)}
                  >
                    <span className="devanagari" style={{ fontSize: "1.05rem", fontWeight: 600 }}>{item.text}</span>
                    <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </motion.div>

          {/* RIGHT PANEL: Results Area */}
          <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}>
            <div className="zen-card" style={{ padding: "32px", minHeight: "600px" }}>
              <div className="flex items-center justify-between mb-6 pb-3 border-b border-[var(--border-soft)]">
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.4rem" }}>Grammar Analysis</h3>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-light)" }}>
                    Sentence analysis & word breakdown
                  </span>
                </div>
                {analysis?.ai_verified && (
                  <span style={{
                    padding: "4px 10px",
                    borderRadius: "12px",
                    fontSize: "0.7rem",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                    background: "rgba(var(--primary-rgb), 0.12)",
                    color: "var(--primary)"
                  }}>
                    AI Scan
                  </span>
                )}
              </div>

              <AnimatePresence mode="wait">
                {loading ? (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "420px", color: "var(--text-light)", textAlign: "center" }}>
                    <Loader2 className="animate-spin" size={36} style={{ color: "var(--primary)", marginBottom: "16px" }} />
                    <h4 style={{ color: "var(--text-dim)", marginBottom: "6px" }}>Analyzing Sentence...</h4>
                    <p style={{ maxWidth: "340px", fontSize: "0.88rem" }}>
                      Evaluating grammatical rules, word morphology, and syntactic concord.
                    </p>
                  </div>
                ) : !analysis ? (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "420px", color: "var(--text-light)", textAlign: "center" }}>
                    <motion.div animate={{ rotate: [0, 10, -10, 0] }} transition={{ repeat: Infinity, duration: 4 }}>
                      <Sparkles size={48} style={{ opacity: 0.2, marginBottom: "16px" }} />
                    </motion.div>
                    <h4 style={{ color: "var(--text-dim)", marginBottom: "6px" }}>Ready for Grammar Verification</h4>
                    <p style={{ maxWidth: "340px", fontSize: "0.88rem" }}>
                      Submit any Sanskrit sentence to inspect grammatical person, number, case, and syntactic agreement.
                    </p>
                  </div>
                ) : (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">

                    {/* SECTION 1: OVERALL SUMMARY & SCORE INDICATOR */}
                    <div className="grid" style={{ gridTemplateColumns: "1.3fr 1fr", gap: "16px" }}>
                      {/* Score Card */}
                      <div
                        className="p-5 flex items-center gap-5"
                        style={{
                          background: "var(--bg-main)",
                          borderRadius: "20px",
                          border: `1.5px solid ${getScoreColor(scoreVal)}33`
                        }}
                      >
                        {/* Circular Score Visualizer */}
                        <div style={{ position: "relative", width: "76px", height: "76px", flexShrink: 0 }}>
                          <svg viewBox="0 0 36 36" style={{ width: "100%", height: "100%", transform: "rotate(-90deg)" }}>
                            <path
                              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                              fill="none"
                              stroke="var(--border-soft)"
                              strokeWidth="3.2"
                            />
                            <motion.path
                              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                              fill="none"
                              stroke={getScoreColor(scoreVal)}
                              strokeWidth="3.2"
                              strokeDasharray={`${scoreVal}, 100`}
                              strokeLinecap="round"
                              initial={{ strokeDasharray: "0, 100" }}
                              animate={{ strokeDasharray: `${scoreVal}, 100` }}
                              transition={{ duration: 0.8, ease: "easeOut" }}
                            />
                          </svg>
                          <div style={{
                            position: "absolute",
                            inset: 0,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: "1.15rem",
                            fontWeight: 800,
                            color: getScoreColor(scoreVal)
                          }}>
                            {scoreVal}%
                          </div>
                        </div>

                        <div>
                          <span style={{ fontSize: "0.68rem", color: "var(--text-light)", textTransform: "uppercase", fontWeight: 800, letterSpacing: "1px" }}>
                            Grammar Score
                          </span>
                          <h4 style={{ margin: "2px 0 4px 0", fontSize: "1.15rem", color: getScoreColor(scoreVal) }}>
                            {scoreLabel}
                          </h4>
                          <span style={{ fontSize: "0.75rem", color: isReliable ? "var(--text-dim)" : "#E67E22" }}>
                            {isReliable ? "Based on evaluated grammatical rules" : "Notice: Limited lexicon confidence"}
                          </span>
                        </div>
                      </div>

                      {/* Stat Counters Card */}
                      <div className="p-4 grid" style={{ gridTemplateColumns: "1fr 1fr", gap: "10px", background: "var(--bg-main)", borderRadius: "20px" }}>
                        <div className="p-2 flex flex-col justify-center">
                          <span style={{ fontSize: "0.68rem", color: "var(--text-light)", textTransform: "uppercase", fontWeight: 800 }}>Confirmed Errors</span>
                          <span style={{ fontSize: "1.4rem", fontWeight: 800, color: confirmedErrors > 0 ? "#EF4444" : "#10B981" }}>
                            {confirmedErrors}
                          </span>
                        </div>
                        <div className="p-2 flex flex-col justify-center">
                          <span style={{ fontSize: "0.68rem", color: "var(--text-light)", textTransform: "uppercase", fontWeight: 800 }}>Advisories</span>
                          <span style={{ fontSize: "1.4rem", fontWeight: 800, color: warningCount + infoCount > 0 ? "var(--secondary)" : "var(--text-light)" }}>
                            {warningCount + infoCount}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* SECTION 2: ORIGINAL & RECOMMENDED CORRECTION */}
                    <div className="flex flex-col gap-3">
                      {/* Original Sentence */}
                      <div className="p-4 rounded-xl" style={{ background: "var(--bg-main)", border: "1px solid var(--border-soft)" }}>
                        <span style={{ fontSize: "0.68rem", color: "var(--text-light)", textTransform: "uppercase", fontWeight: 800, letterSpacing: "1px", display: "block", marginBottom: "4px" }}>
                          Original Sentence
                        </span>
                        <div className="flex items-center gap-3">
                          <div className="devanagari" style={{ fontSize: "1.35rem", color: "var(--text-main)" }}>
                            {analysis.original_sentence || inputText}
                          </div>
                          <AudioPronounceButton text={analysis.original_sentence || inputText} size={18} />
                        </div>
                      </div>

                      {/* Recommended Correction */}
                      <div
                        className="p-4 rounded-xl"
                        style={{
                          background: analysis.correction_status === "no_correction_needed" ? "rgba(16, 185, 129, 0.05)" : "rgba(var(--primary-rgb), 0.05)",
                          border: `1.5px solid ${analysis.correction_status === "no_correction_needed" ? "#10B98133" : "rgba(var(--primary-rgb), 0.2)"}`
                        }}
                      >
                        <div className="flex justify-between items-center mb-2">
                          <span style={{
                            fontSize: "0.68rem",
                            fontWeight: 800,
                            textTransform: "uppercase",
                            letterSpacing: "1px",
                            color: analysis.correction_status === "no_correction_needed" ? "#10B981" : "var(--primary)"
                          }}>
                            {analysis.correction_status === "no_correction_needed" ? "✨ Verified Formulation" : "Recommended Correction"}
                          </span>

                          <div className="flex items-center gap-2">
                            {analysis.corrected_sentence && analysis.corrected_sentence !== inputText && (
                              <button
                                onClick={() => handleApplyCorrection(analysis.corrected_sentence)}
                                style={{
                                  background: "var(--primary)",
                                  color: "white",
                                  border: "none",
                                  padding: "6px 12px",
                                  borderRadius: "8px",
                                  fontSize: "0.75rem",
                                  fontWeight: 700,
                                  cursor: "pointer",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "5px"
                                }}
                              >
                                <ArrowRight size={13} /> Apply to Input
                              </button>
                            )}

                            <button
                              onClick={() => copyToClipboard(analysis.corrected_sentence || inputText)}
                              title="Copy corrected sentence"
                              style={{
                                background: "none",
                                border: "1px solid var(--border-soft)",
                                borderRadius: "8px",
                                padding: "4px 8px",
                                color: "var(--text-dim)",
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                gap: "4px",
                                fontSize: "0.7rem"
                              }}
                            >
                              {copied ? <Check size={13} color="#10B981" /> : <Copy size={13} />}
                              <span>{copied ? "Copied" : "Copy"}</span>
                            </button>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <div className="devanagari" style={{ fontSize: "1.45rem", fontWeight: 600, color: "var(--text-main)", marginBottom: "6px" }}>
                            {analysis.corrected_sentence || inputText}
                          </div>
                          <AudioPronounceButton text={analysis.corrected_sentence || inputText} size={18} />
                        </div>

                        <p style={{ fontSize: "0.82rem", color: "var(--text-dim)", margin: 0, lineHeight: 1.5 }}>
                          {analysis.correction_summary || (analysis.correction_status === "no_correction_needed" ? "Sentence conforms to Sanskrit grammatical standards." : "Grammatical corrections applied.")}
                        </p>
                      </div>
                    </div>

                    {/* SECTION 3: DETECTED ISSUES */}
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <h4 style={{ fontSize: "0.8rem", color: "var(--text-light)", textTransform: "uppercase", letterSpacing: "1px", margin: 0 }}>
                          Detected Issues
                        </h4>
                        <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                          {analysis.issues?.length || 0} finding{analysis.issues?.length === 1 ? "" : "s"}
                        </span>
                      </div>

                      {analysis.issues && analysis.issues.length > 0 ? (
                        <div className="flex flex-col gap-2.5">
                          {analysis.issues.map((issue: any, idx: number) => {
                            const isErr = issue.severity === "error";
                            const isWarn = issue.severity === "warning";
                            return (
                              <div
                                key={idx}
                                className="p-4 rounded-xl flex flex-col gap-2"
                                style={{
                                  background: "var(--bg-main)",
                                  borderLeft: `4px solid ${isErr ? "#EF4444" : isWarn ? "var(--secondary)" : "#3B82F6"}`,
                                  borderTop: "1px solid var(--border-soft)",
                                  borderRight: "1px solid var(--border-soft)",
                                  borderBottom: "1px solid var(--border-soft)"
                                }}
                              >
                                <div className="flex items-center justify-between flex-wrap gap-2">
                                  <div className="flex items-center gap-2">
                                    {isErr ? (
                                      <AlertCircle size={16} color="#EF4444" />
                                    ) : isWarn ? (
                                      <AlertTriangle size={16} color="var(--secondary)" />
                                    ) : (
                                      <Info size={16} color="#3B82F6" />
                                    )}
                                    <span style={{ fontSize: "0.78rem", fontWeight: 800, textTransform: "uppercase", color: isErr ? "#EF4444" : isWarn ? "var(--secondary)" : "#3B82F6" }}>
                                      {issue.category?.replace(/_/g, " ") || "Grammar Rule"}
                                    </span>
                                  </div>

                                  {issue.text && (
                                    <span className="devanagari" style={{ fontSize: "0.9rem", padding: "2px 8px", background: "rgba(0,0,0,0.04)", borderRadius: "6px", fontWeight: 600 }}>
                                      {issue.text}
                                    </span>
                                  )}
                                </div>

                                <p style={{ fontSize: "0.88rem", color: "var(--text-main)", margin: 0, fontWeight: 500 }}>
                                  {issue.message}
                                </p>

                                {issue.rule_explanation && (
                                  <p style={{ fontSize: "0.78rem", color: "var(--text-dim)", margin: 0, fontStyle: "italic", borderTop: "1px solid var(--border-soft)", paddingTop: "6px" }}>
                                    <strong>Rule:</strong> {issue.rule_explanation}
                                  </p>
                                )}

                                {issue.suggestion && (
                                  <div className="flex items-center gap-2 mt-1">
                                    <span style={{ fontSize: "0.75rem", color: "var(--text-light)" }}>Suggestion:</span>
                                    <span className="devanagari" style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--primary)" }}>
                                      {issue.suggestion}
                                    </span>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="p-4 rounded-xl flex items-center gap-3" style={{ background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
                          <CheckCircle2 size={18} color="#10B981" />
                          <span style={{ fontSize: "0.88rem", fontWeight: 600, color: "#10B981" }}>
                            Linguistic concord and syntactic agreement are verified.
                          </span>
                        </div>
                      )}
                    </div>

                    {/* SECTION 4: WORD-BY-WORD ANALYSIS */}
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <h4 style={{ fontSize: "0.8rem", color: "var(--text-light)", textTransform: "uppercase", letterSpacing: "1px", margin: 0 }}>
                          Word-by-Word Analysis
                        </h4>
                        <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                          {analysis.words?.length || 0} token{analysis.words?.length === 1 ? "" : "s"}
                        </span>
                      </div>

                      <div style={{ overflowX: "auto", borderRadius: "16px", border: "1px solid var(--border-soft)" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", textAlign: "left" }}>
                          <thead>
                            <tr style={{ background: "var(--bg-main)", borderBottom: "1px solid var(--border-soft)" }}>
                              <th style={{ padding: "12px 14px", fontWeight: 700, color: "var(--text-dim)" }}>Word</th>
                              <th style={{ padding: "12px 14px", fontWeight: 700, color: "var(--text-dim)" }}>IAST</th>
                              <th style={{ padding: "12px 14px", fontWeight: 700, color: "var(--text-dim)" }}>English Meaning</th>
                              <th style={{ padding: "12px 14px", fontWeight: 700, color: "var(--text-dim)" }}>POS / Base</th>
                              <th style={{ padding: "12px 14px", fontWeight: 700, color: "var(--text-dim)" }}>Grammar Details</th>
                              <th style={{ padding: "12px 14px", fontWeight: 700, color: "var(--text-dim)" }}>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(analysis.words || []).map((w: any, idx: number) => {
                              const isValid = w.grammar_status === "valid";
                              const isUncertain = w.grammar_status === "uncertain";
                              return (
                                <tr key={idx} style={{ borderBottom: "1px solid var(--border-soft)", background: idx % 2 === 0 ? "transparent" : "rgba(0,0,0,0.01)" }}>
                                  <td style={{ padding: "12px 14px" }}>
                                    <div className="flex items-center gap-2">
                                      <span className="devanagari" style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--primary)" }}>
                                        {w.text}
                                      </span>
                                      <AudioPronounceButton text={w.text} size={14} />
                                    </div>
                                  </td>
                                  <td style={{ padding: "12px 14px", fontStyle: "italic", color: "var(--text-dim)" }}>
                                    {w.transliteration || "—"}
                                  </td>
                                  <td style={{ padding: "12px 14px", fontWeight: 600, color: "var(--text-main)" }}>
                                    {w.meaning || "Meaning unavailable"}
                                  </td>
                                  <td style={{ padding: "12px 14px" }}>
                                    <div className="flex flex-col">
                                      <span style={{ fontWeight: 700, textTransform: "capitalize", color: "var(--text-main)" }}>
                                        {w.part_of_speech}
                                      </span>
                                      {w.lemma && w.lemma !== w.text && (
                                        <span style={{ fontSize: "0.72rem", color: "var(--text-light)" }}>
                                          Base: {w.lemma}
                                        </span>
                                      )}
                                    </div>
                                  </td>
                                  <td style={{ padding: "12px 14px", color: "var(--text-dim)" }}>
                                    <div className="flex flex-wrap gap-1">
                                      {w.case && (
                                        <span style={{ padding: "2px 6px", background: "rgba(0,0,0,0.04)", borderRadius: "4px", fontSize: "0.7rem" }}>
                                          {w.case}
                                        </span>
                                      )}
                                      {w.number && (
                                        <span style={{ padding: "2px 6px", background: "rgba(0,0,0,0.04)", borderRadius: "4px", fontSize: "0.7rem" }}>
                                          {w.number}
                                        </span>
                                      )}
                                      {w.person && (
                                        <span style={{ padding: "2px 6px", background: "rgba(0,0,0,0.04)", borderRadius: "4px", fontSize: "0.7rem" }}>
                                          {w.person} p.
                                        </span>
                                      )}
                                      {w.lakara && (
                                        <span style={{ padding: "2px 6px", background: "rgba(var(--primary-rgb), 0.08)", color: "var(--primary)", borderRadius: "4px", fontSize: "0.7rem", fontWeight: 700 }}>
                                          {w.lakara}
                                        </span>
                                      )}
                                      {w.gender && (
                                        <span style={{ padding: "2px 6px", background: "rgba(0,0,0,0.04)", borderRadius: "4px", fontSize: "0.7rem" }}>
                                          {w.gender}
                                        </span>
                                      )}
                                    </div>
                                  </td>
                                  <td style={{ padding: "12px 14px" }}>
                                    <span style={{
                                      padding: "3px 8px",
                                      borderRadius: "6px",
                                      fontSize: "0.7rem",
                                      fontWeight: 800,
                                      textTransform: "uppercase",
                                      background: isValid ? "rgba(16, 185, 129, 0.1)" : isUncertain ? "rgba(245, 158, 11, 0.1)" : "rgba(239, 68, 68, 0.1)",
                                      color: isValid ? "#10B981" : isUncertain ? "#F59E0B" : "#EF4444"
                                    }}>
                                      {w.grammar_status || "analyzed"}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* SECTION 5: ADVANCED DETAILED GRAMMATICAL ANALYSIS */}
                    <div className="pt-2">
                      <button
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="flex items-center justify-between w-full p-3 rounded-xl border border-[var(--border-soft)]"
                        style={{ background: "var(--bg-main)", color: "var(--text-main)", cursor: "pointer", fontSize: "0.85rem", fontWeight: 700 }}
                      >
                        <div className="flex items-center gap-2">
                          <Layers size={16} color="var(--primary)" />
                          <span>Detailed Grammatical Analysis</span>
                        </div>
                        {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>

                      {showAdvanced && (
                        <div className="p-4 mt-2 rounded-xl flex flex-col gap-3" style={{ background: "var(--bg-main)", border: "1px solid var(--border-soft)" }}>
                          {analysis.clauses && analysis.clauses.length > 0 ? (
                            analysis.clauses.map((c: any, i: number) => (
                              <div key={i} className="p-3 rounded-lg border border-[var(--border-soft)]" style={{ background: "var(--bg-card)" }}>
                                <div className="flex justify-between items-center mb-1">
                                  <span style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--primary)" }}>Clause {i + 1}</span>
                                  <span style={{
                                    fontSize: "0.68rem",
                                    padding: "2px 6px",
                                    borderRadius: "4px",
                                    fontWeight: 700,
                                    background: c.status === "valid" ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                                    color: c.status === "valid" ? "#10B981" : "#EF4444"
                                  }}>
                                    {c.status.toUpperCase()}
                                  </span>
                                </div>
                                <div className="devanagari" style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "4px" }}>
                                  {c.clause_text}
                                </div>
                                <div className="flex gap-4 text-xs" style={{ color: "var(--text-dim)" }}>
                                  {c.subject && <span><strong>Subject:</strong> {c.subject}</span>}
                                  {c.verb && <span><strong>Verb:</strong> {c.verb}</span>}
                                </div>
                                {c.notes && <p style={{ fontSize: "0.75rem", color: "var(--text-light)", margin: "4px 0 0 0" }}>{c.notes}</p>}
                              </div>
                            ))
                          ) : (
                            <p style={{ fontSize: "0.82rem", color: "var(--text-dim)", margin: 0 }}>
                              Single independent clause structure analyzed.
                            </p>
                          )}

                          {analysis.limitations && analysis.limitations.length > 0 && (
                            <div className="mt-2 pt-2 border-t border-[var(--border-soft)]">
                              <span style={{ fontSize: "0.7rem", fontWeight: 800, color: "var(--text-light)", textTransform: "uppercase" }}>Analysis Notes & Limitations</span>
                              <ul style={{ paddingLeft: "16px", margin: "4px 0 0 0", fontSize: "0.75rem", color: "var(--text-dim)" }}>
                                {analysis.limitations.map((lim: string, idx: number) => (
                                  <li key={idx}>{lim}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>

        </section>
      </main>
    </div>
  );
}
