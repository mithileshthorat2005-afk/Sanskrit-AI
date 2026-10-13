'use client';
import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  Sparkles, 
  RotateCcw, 
  Award,
  GitMerge,
  Zap,
  BookOpen
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface Example {
  components: string;
  compound: string;
  meaning: string;
  sentence?: string;
  translation?: string;
}

interface SamasaType {
  id: string;
  type: string;
  description: string;
  formation: string;
  example?: Example;
  examples?: Example[];
  common_prefixes?: string[];
  subtypes?: string[];
  additional_examples?: Example[];
}

export default function Samasa1Lesson({ onBack }: { onBack: () => void }) {
  const [samasaData, setSamasaData] = useState<SamasaType[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeType, setActiveType] = useState<SamasaType | null>(null);
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
        const res = await api.lessons.getSamasa1();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setSamasaData(data);
        if (data.length > 0) setActiveType(data[0]);
      } catch (error) {
        console.error('Failed to fetch Samāsa data', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const startQuiz = () => {
    setQuizMode(true);
    setScore(0);
    setTotalQuestions(0);
    setQuizComplete(false);
    setQuizFeedback(null);
    generateQuizQuestion();
  };

  const generateQuizQuestion = () => {
    // Collect all examples from all types
    const allExamples: any[] = [];
    samasaData.forEach(type => {
      if (type.example) {
        allExamples.push({ ...type.example, samasaType: type.type, samasaId: type.id });
      }
      if (type.examples) {
        type.examples.forEach(ex => {
          allExamples.push({ ...ex, samasaType: type.type, samasaId: type.id });
        });
      }
      if (type.additional_examples) {
        type.additional_examples.forEach(ex => {
          allExamples.push({ ...ex, samasaType: type.type, samasaId: type.id });
        });
      }
    });
    if (allExamples.length === 0) return;

    const randomIndex = Math.floor(Math.random() * allExamples.length);
    const question = allExamples[randomIndex];

    // Options: given a compound, identify its type
    const allTypes = samasaData.map(t => t.type);
    const distractors = allTypes.filter(name => name !== question.samasaType);
    const shuffledDistractors = distractors.sort(() => Math.random() - 0.5).slice(0, 3);
    const options = [question.samasaType, ...shuffledDistractors].sort(() => Math.random() - 0.5);

    setQuizQuestion({
      ...question,
      options,
      correctAnswer: question.samasaType,
    });
  };

  const handleQuizAnswer = (selected: string) => {
    if (!quizQuestion) return;
    const correct = selected === quizQuestion.correctAnswer;
    setQuizFeedback({
      correct,
      message: correct
        ? `✅ Correct! "${quizQuestion.compound}" is a ${quizQuestion.samasaType} compound.`
        : `❌ Incorrect. "${quizQuestion.compound}" is a ${quizQuestion.samasaType} compound.`,
    });
    setTotalQuestions(t => t + 1);
    if (correct) setScore(s => s + 1);

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
          <GitMerge size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Compound Types...</h3>
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
          <div style={{ background: 'linear-gradient(135deg, #8B5CF6, #6D28D9)', color: 'white', padding: '24px', borderRadius: '50%' }}>
            <Award size={56} />
          </div>
        </div>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Samāsa Expert!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You identified <b>{score}</b> out of {totalQuestions} compound types correctly.
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
              Samāsa – Compounds (Part 1)
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              Learn the four main types of Sanskrit compounds.
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
              <Zap size={16} /> Start Quiz
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
              key={quizQuestion.compound}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div style={{ fontSize: '1.2rem', marginBottom: '12px', fontWeight: 600, color: 'var(--text-dim)' }}>
                What type of compound is this?
              </div>
              <div className="devanagari" style={{ fontSize: '2.8rem', fontWeight: 900, color: 'var(--primary)', marginBottom: '8px' }}>
                {quizQuestion.compound}
              </div>
              <div style={{ fontSize: '1rem', color: 'var(--text-light)', marginBottom: '24px' }}>
                {quizQuestion.meaning}
                {quizQuestion.components && <div style={{ fontSize: '0.85rem' }}>Components: {quizQuestion.components}</div>}
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
                      background: quizFeedback && opt === quizQuestion.correctAnswer ? 'rgba(76, 175, 80, 0.1)' : 'var(--bg-main)',
                      fontWeight: 700,
                      cursor: quizFeedback ? 'default' : 'pointer',
                      transition: 'all 0.2s',
                      color: quizFeedback && opt === quizQuestion.correctAnswer ? '#4CAF50' : 'var(--text-main)',
                      borderColor: quizFeedback && opt === quizQuestion.correctAnswer ? '#4CAF50' : 'var(--border-soft)',
                    }}
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
        // Main content: Compound types with details
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar: Type list */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
                Compound Types
              </h3>
              <div className="flex flex-col gap-2">
                {samasaData.map((t) => {
                  const isActive = activeType?.id === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setActiveType(t)}
                      style={{
                        padding: '12px 16px',
                        borderRadius: '12px',
                        background: isActive ? 'var(--primary)' : 'var(--bg-main)',
                        color: isActive ? '#fff' : 'var(--text-main)',
                        border: '1px solid var(--border-soft)',
                        textAlign: 'left',
                        fontWeight: 700,
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                      }}
                    >
                      <div style={{ fontSize: '0.9rem' }}>{t.type}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="lg:col-span-2">
            {activeType && (
              <motion.div
                key={activeType.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="zen-card"
                style={{ padding: '32px' }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <BookOpen size={24} color="var(--primary)" />
                  <div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--text-main)' }}>
                      {activeType.type}
                    </h2>
                    <p style={{ color: 'var(--text-dim)' }}>{activeType.description}</p>
                  </div>
                </div>

                <div style={{ marginBottom: '24px', padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>
                    Formation
                  </div>
                  <div style={{ fontSize: '1rem', color: 'var(--text-main)' }}>{activeType.formation}</div>
                </div>

                {/* Display examples */}
                <h4 style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>
                  Examples
                </h4>

                {/* Single example */}
                {activeType.example && (
                  <div style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)', marginBottom: '16px' }}>
                    <div className="devanagari" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)' }}>
                      {activeType.example.compound}
                    </div>
                    <div style={{ fontSize: '0.95rem', color: 'var(--text-dim)' }}>
                      {activeType.example.components && <span>Components: {activeType.example.components}</span>}
                      <span style={{ marginLeft: '12px' }}>Meaning: {activeType.example.meaning}</span>
                    </div>
                    {activeType.example.sentence && (
                      <div style={{ marginTop: '8px' }}>
                        <div className="devanagari" style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)' }}>
                          {activeType.example.sentence}
                        </div>
                        <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)' }}>{activeType.example.translation}</div>
                      </div>
                    )}
                  </div>
                )}

                {/* Multiple examples */}
                {activeType.examples && activeType.examples.map((ex, i) => (
                  <div key={i} style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)', marginBottom: '12px' }}>
                    <div className="devanagari" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)' }}>
                      {ex.compound}
                    </div>
                    <div style={{ fontSize: '0.95rem', color: 'var(--text-dim)' }}>
                      {ex.components && <span>Components: {ex.components}</span>}
                      <span style={{ marginLeft: '12px' }}>Meaning: {ex.meaning}</span>
                    </div>
                    {ex.sentence && (
                      <div style={{ marginTop: '8px' }}>
                        <div className="devanagari" style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)' }}>
                          {ex.sentence}
                        </div>
                        <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)' }}>{ex.translation}</div>
                      </div>
                    )}
                  </div>
                ))}

                {/* Additional info */}
                {activeType.common_prefixes && (
                  <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(var(--primary-rgb), 0.06)', borderRadius: '12px' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
                      Common Prefixes
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {activeType.common_prefixes.map(p => (
                        <span key={p} className="devanagari" style={{ padding: '4px 12px', background: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--border-soft)', fontSize: '1.1rem' }}>
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {activeType.subtypes && (
                  <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(var(--primary-rgb), 0.06)', borderRadius: '12px' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
                      Subtypes
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {activeType.subtypes.map(s => (
                        <span key={s} style={{ padding: '4px 12px', background: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--border-soft)' }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {activeType.additional_examples && (
                  <>
                    <h4 style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginTop: '16px', marginBottom: '12px' }}>
                      More Examples
                    </h4>
                    {activeType.additional_examples.map((ex, i) => (
                      <div key={i} style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)', marginBottom: '12px' }}>
                        <div className="devanagari" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)' }}>
                          {ex.compound}
                        </div>
                        <div style={{ fontSize: '0.95rem', color: 'var(--text-dim)' }}>
                          {ex.components && <span>Components: {ex.components}</span>}
                          <span style={{ marginLeft: '12px' }}>Meaning: {ex.meaning}</span>
                        </div>
                        {ex.sentence && (
                          <div style={{ marginTop: '8px' }}>
                            <div className="devanagari" style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)' }}>
                              {ex.sentence}
                            </div>
                            <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)' }}>{ex.translation}</div>
                          </div>
                        )}
                      </div>
                    ))}
                  </>
                )}
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
