'use client';
import React, { useState, useEffect } from 'react';
import { ArrowLeft, CheckCircle2, Sparkles, HelpCircle, RotateCcw, Award } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface CaseData {
  id: string;
  sanskrit_name: string;
  english_name: string;
  meaning: string;
  endings: {
    masculine: string;
    feminine: string;
    neuter: string;
  };
  examples: {
    sanskrit: string;
    translation: string;
    highlighted_word: string;
    case_used: string;
  }[];
}

export default function VibhaktiLesson({ onBack }: { onBack: () => void }) {
  const [cases, setCases] = useState<CaseData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState<CaseData | null>(null);
  const [quizMode, setQuizMode] = useState(false);
  const [quizQuestion, setQuizQuestion] = useState<any>(null);
  const [quizOptions, setQuizOptions] = useState<string[]>([]);
  const [quizFeedback, setQuizFeedback] = useState<{ correct: boolean; message: string } | null>(null);
  const [score, setScore] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [quizComplete, setQuizComplete] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.lessons.getVibhakti();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setCases(data);
        if (data.length > 0) setSelectedCase(data[0]);
      } catch (error) {
        console.error('Failed to fetch vibhakti data', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Quiz logic: pick a random example, ask to identify the case
  const startQuiz = () => {
    setQuizMode(true);
    setScore(0);
    setTotalQuestions(0);
    setQuizComplete(false);
    setQuizFeedback(null);
    generateQuizQuestion();
  };

  const generateQuizQuestion = () => {
    const allExamples = cases.flatMap(c => c.examples.map(ex => ({ ...ex, caseName: c.english_name, caseId: c.id })));
    if (allExamples.length === 0) return;

    const randomIndex = Math.floor(Math.random() * allExamples.length);
    const question = allExamples[randomIndex];

    // Get all case names except the correct one for distractors
    const allCaseNames = cases.map(c => c.english_name);
    const distractors = allCaseNames.filter(name => name !== question.caseName);
    // Pick 2 distractors
    const shuffledDistractors = distractors.sort(() => Math.random() - 0.5).slice(0, 2);
    const options = [question.caseName, ...shuffledDistractors].sort(() => Math.random() - 0.5);

    setQuizQuestion({
      ...question,
      options,
    });
  };

  const handleQuizAnswer = (selected: string) => {
    if (!quizQuestion) return;
    const correct = selected === quizQuestion.caseName;
    setQuizFeedback({
      correct,
      message: correct
        ? `✅ Correct! The case is "${quizQuestion.caseName}".`
        : `❌ The correct case is "${quizQuestion.caseName}".`,
    });
    setTotalQuestions(t => t + 1);
    if (correct) setScore(s => s + 1);

    // Move to next question after delay
    setTimeout(() => {
      if (totalQuestions + 1 >= 8) {
        setQuizComplete(true);
        setQuizMode(false);
      } else {
        setQuizFeedback(null);
        generateQuizQuestion();
      }
    }, 2000);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}>
          <Sparkles size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Case Declensions...</h3>
      </div>
    );
  }

  if (quizComplete) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="zen-card text-center"
        style={{ padding: '60px', borderRadius: '32px' }}
      >
        <div className="flex justify-center mb-6">
          <div style={{ background: '#FFC107', color: 'white', padding: '24px', borderRadius: '50%' }}>
            <Award size={56} />
          </div>
        </div>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Case Master!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You identified <b>{score}</b> out of {totalQuestions} cases correctly.
        </p>
        <div className="flex justify-center gap-4">
          <button onClick={startQuiz} className="btn-secondary" style={{ padding: '14px 32px' }}>
            <RotateCcw size={18} /> Retry Quiz
          </button>
          <button onClick={onBack} className="btn-primary" style={{ padding: '14px 32px' }}>
            Finish Lesson <CheckCircle2 size={18} />
          </button>
        </div>
      </motion.div>
    );
  }

  return (
    <div style={{ padding: '10px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          padding: '24px 32px',
          marginBottom: '24px',
          borderRadius: '24px',
          background: 'rgba(var(--bg-card-rgb), 0.8)',
          backdropFilter: 'blur(10px)',
          border: '1px solid var(--border-soft)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px'
        }}
      >
        <div className="flex items-center gap-4">
          <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
            <ArrowLeft size={22} />
          </button>
          <div>
            <h1 style={{ fontSize: '1.8rem', fontWeight: 900, margin: 0, color: 'var(--text-main)' }}>
              विभक्ति – The 7 Cases
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              {quizMode ? 'Identify the case of the highlighted word!' : 'Click a case to see its declension patterns.'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {!quizMode && (
            <button
              onClick={startQuiz}
              className="btn-primary"
              style={{ padding: '10px 24px', borderRadius: '100px' }}
            >
              <Sparkles size={16} /> Start Quiz
            </button>
          )}
        </div>
      </motion.div>

      {quizMode ? (
        // Quiz interface
        <div className="zen-card" style={{ padding: '40px', maxWidth: '700px', margin: '0 auto' }}>
          <div className="flex justify-between items-center mb-6">
            <span style={{ fontWeight: 800, color: 'var(--primary)' }}>
              Question {totalQuestions + 1} / 8
            </span>
            <span style={{ fontWeight: 800, color: 'var(--text-dim)' }}>Score: {score}</span>
          </div>

          {quizQuestion && (
            <motion.div
              key={quizQuestion.sanskrit}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div style={{ fontSize: '1.2rem', marginBottom: '12px', fontWeight: 600, color: 'var(--text-dim)' }}>
                What is the case of the highlighted word?
              </div>
              <div className="devanagari" style={{ fontSize: '2.8rem', fontWeight: 900, color: 'var(--text-main)', marginBottom: '8px' }}>
                {quizQuestion.sanskrit}
              </div>
              <div style={{ fontSize: '1rem', color: 'var(--text-light)', marginBottom: '24px' }}>
                {quizQuestion.translation}
                <span style={{ display: 'block', marginTop: '4px', fontStyle: 'italic' }}>
                  (Highlighted: "{quizQuestion.highlighted_word}")
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4" style={{ marginBottom: '24px' }}>
                {quizQuestion.options.map((opt: string) => (
                  <motion.button
                    key={opt}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleQuizAnswer(opt)}
                    disabled={!!quizFeedback}
                    style={{
                      padding: '16px',
                      borderRadius: '16px',
                      border: '2px solid var(--border-soft)',
                      background: 'var(--bg-main)',
                      fontWeight: 700,
                      cursor: quizFeedback ? 'default' : 'pointer',
                      transition: 'all 0.2s',
                    }}
                    className={quizFeedback && opt === quizQuestion.caseName ? 'border-green-500 bg-green-50' : ''}
                  >
                    {opt}
                  </motion.button>
                ))}
              </div>

              {quizFeedback && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{
                    padding: '16px',
                    borderRadius: '16px',
                    background: quizFeedback.correct ? 'rgba(76, 175, 80, 0.1)' : 'rgba(255, 82, 82, 0.1)',
                    border: `1px solid ${quizFeedback.correct ? '#4CAF50' : '#FF5252'}`,
                    color: quizFeedback.correct ? '#4CAF50' : '#FF5252',
                    fontWeight: 700,
                  }}
                >
                  {quizFeedback.message}
                </motion.div>
              )}
            </motion.div>
          )}
        </div>
      ) : (
        // Main content: Case table and details
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar: Case list */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
                Cases
              </h3>
              <div className="flex flex-col gap-2">
                {cases.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setSelectedCase(c)}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '12px',
                      background: selectedCase?.id === c.id ? 'var(--primary)' : 'var(--bg-main)',
                      color: selectedCase?.id === c.id ? '#fff' : 'var(--text-main)',
                      border: '1px solid var(--border-soft)',
                      textAlign: 'left',
                      fontWeight: 700,
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    <div className="devanagari" style={{ fontSize: '1.1rem' }}>{c.sanskrit_name}</div>
                    <div style={{ fontSize: '0.8rem', opacity: 0.7 }}>{c.english_name}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="lg:col-span-2">
            {selectedCase && (
              <motion.div
                key={selectedCase.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="zen-card"
                style={{ padding: '32px' }}
              >
                <h2 className="devanagari" style={{ fontSize: '2rem', fontWeight: 900, color: 'var(--primary)' }}>
                  {selectedCase.sanskrit_name}
                </h2>
                <p style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  {selectedCase.english_name}
                </p>
                <p style={{ color: 'var(--text-dim)', marginBottom: '24px' }}>
                  {selectedCase.meaning}
                </p>

                <h4 style={{ fontWeight: 800, marginBottom: '12px' }}>Declension Endings</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '24px' }}>
                  <div style={{ padding: '12px', background: 'var(--bg-main)', borderRadius: '12px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Masculine</div>
                    <div className="devanagari" style={{ fontSize: '1.8rem' }}>{selectedCase.endings.masculine}</div>
                  </div>
                  <div style={{ padding: '12px', background: 'var(--bg-main)', borderRadius: '12px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Feminine</div>
                    <div className="devanagari" style={{ fontSize: '1.8rem' }}>{selectedCase.endings.feminine}</div>
                  </div>
                  <div style={{ padding: '12px', background: 'var(--bg-main)', borderRadius: '12px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Neuter</div>
                    <div className="devanagari" style={{ fontSize: '1.8rem' }}>{selectedCase.endings.neuter}</div>
                  </div>
                </div>

                <h4 style={{ fontWeight: 800, marginBottom: '12px' }}>Example Sentences</h4>
                <div className="flex flex-col gap-4">
                  {selectedCase.examples.map((ex, i) => (
                    <div key={i} style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)' }}>
                      <div className="devanagari" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)' }}>
                        {ex.sanskrit.split(ex.highlighted_word).map((part, idx, arr) => (
                          <span key={idx}>
                            {part}
                            {idx < arr.length - 1 && (
                              <span style={{ color: 'var(--primary)', fontWeight: 900, borderBottom: '2px solid var(--primary)' }}>
                                {ex.highlighted_word}
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                      <div style={{ fontSize: '1rem', color: 'var(--text-dim)', marginTop: '4px' }}>{ex.translation}</div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
