'use client';
import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  Sparkles, 
  RotateCcw, 
  Award,
  BookOpen,
  PenLine,
  HelpCircle,
  Eye,
  EyeOff,
  Zap,
  ChevronRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface VocabularyItem {
  word: string;
  meaning: string;
}

interface Question {
  question: string;
  answer: string;
}

interface ReadingPassage {
  id: string;
  title: string;
  text: string;
  translation: string;
  vocabulary: VocabularyItem[];
  questions: Question[];
  composition_prompt: string;
}

export default function ReadingCompositionLesson({ onBack }: { onBack: () => void }) {
  const [passages, setPassages] = useState<ReadingPassage[]>([]);
  const [loading, setLoading] = useState(true);
  const [activePassage, setActivePassage] = useState<ReadingPassage | null>(null);
  const [showTranslation, setShowTranslation] = useState(false);
  const [answeredQuestions, setAnsweredQuestions] = useState<{ [key: number]: string }>({});
  const [questionFeedback, setQuestionFeedback] = useState<{ [key: number]: boolean | null }>({});
  const [compositionText, setCompositionText] = useState('');
  const [compositionSubmitted, setCompositionSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState<'reading' | 'composition'>('reading');
  const [score, setScore] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [quizComplete, setQuizComplete] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.lessons.getReadingComposition();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setPassages(data);
        if (data.length > 0) setActivePassage(data[0]);
      } catch (error) {
        console.error('Failed to fetch reading data', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleQuestionAnswer = (qIndex: number, answer: string) => {
    if (!activePassage) return;
    const correct = answer.trim().toLowerCase() === activePassage.questions[qIndex].answer.trim().toLowerCase();
    setAnsweredQuestions({ ...answeredQuestions, [qIndex]: answer });
    setQuestionFeedback({ ...questionFeedback, [qIndex]: correct });
    if (correct) {
      setScore(s => s + 1);
    }
    setTotalQuestions(t => t + 1);

    // Check if all questions answered
    const totalQ = activePassage.questions.length;
    const answered = Object.keys(answeredQuestions).length;
    if (answered + 1 === totalQ) {
      setTimeout(() => setQuizComplete(true), 1000);
    }
  };

  const handleCompositionSubmit = () => {
    if (compositionText.trim().length > 10) {
      setCompositionSubmitted(true);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}>
          <BookOpen size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Reading Passages...</h3>
      </div>
    );
  }

  if (quizComplete && activePassage) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="zen-card text-center"
        style={{ padding: '60px', borderRadius: '32px' }}
      >
        <div className="flex justify-center mb-6">
          <div style={{ background: 'linear-gradient(135deg, #10B981, #059669)', color: 'white', padding: '24px', borderRadius: '50%' }}>
            <Award size={56} />
          </div>
        </div>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Reading Complete!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You answered <b>{score}</b> out of {totalQuestions} questions correctly.
        </p>
        <div className="flex justify-center gap-4">
          <button
            onClick={() => {
              setQuizComplete(false);
              setAnsweredQuestions({});
              setQuestionFeedback({});
              setScore(0);
              setTotalQuestions(0);
              // Move to next passage if available
              const currentIdx = passages.findIndex(p => p.id === activePassage.id);
              if (currentIdx < passages.length - 1) {
                setActivePassage(passages[currentIdx + 1]);
              }
            }}
            className="btn-secondary"
            style={{ padding: '14px 32px' }}
          >
            <RotateCcw size={18} /> Next Passage
          </button>
          <button onClick={onBack} className="btn-primary" style={{ padding: '14px 32px' }}>
            Finish Lesson <CheckCircle2 size={18} />
          </button>
        </div>
      </motion.div>
    );
  }

  if (!activePassage) return null;

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
              Reading & Composition
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              Apply your Sanskrit knowledge through reading and writing.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveTab('reading')}
            style={{
              padding: '8px 20px',
              borderRadius: '100px',
              border: '2px solid var(--border-soft)',
              background: activeTab === 'reading' ? 'var(--primary)' : 'transparent',
              color: activeTab === 'reading' ? '#fff' : 'var(--text-dim)',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <BookOpen size={16} style={{ display: 'inline', marginRight: '6px' }} />
            Reading
          </button>
          <button
            onClick={() => setActiveTab('composition')}
            style={{
              padding: '8px 20px',
              borderRadius: '100px',
              border: '2px solid var(--border-soft)',
              background: activeTab === 'composition' ? 'var(--primary)' : 'transparent',
              color: activeTab === 'composition' ? '#fff' : 'var(--text-dim)',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <PenLine size={16} style={{ display: 'inline', marginRight: '6px' }} />
            Composition
          </button>
        </div>
      </motion.div>

      {activeTab === 'reading' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar: Passage list */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
                Passages
              </h3>
              <div className="flex flex-col gap-2">
                {passages.map((p) => {
                  const isActive = activePassage?.id === p.id;
                  return (
                    <button
                      key={p.id}
                      onClick={() => {
                        setActivePassage(p);
                        setQuizComplete(false);
                        setAnsweredQuestions({});
                        setQuestionFeedback({});
                        setScore(0);
                        setTotalQuestions(0);
                      }}
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
                      <div style={{ fontSize: '0.9rem' }}>{p.title}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Passage Content */}
          <div className="lg:col-span-2">
            <motion.div
              key={activePassage.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="zen-card"
              style={{ padding: '32px' }}
            >
              <h2 className="devanagari" style={{ fontSize: '1.8rem', fontWeight: 900, color: 'var(--primary)', marginBottom: '16px' }}>
                {activePassage.title}
              </h2>

              {/* Text */}
              <div style={{ padding: '20px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)', marginBottom: '16px' }}>
                <div className="devanagari" style={{ fontSize: '1.4rem', lineHeight: '1.8', color: 'var(--text-main)', fontWeight: 500 }}>
                  {activePassage.text}
                </div>
                <button
                  onClick={() => setShowTranslation(!showTranslation)}
                  style={{
                    marginTop: '12px',
                    background: 'none',
                    border: 'none',
                    color: 'var(--primary)',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '0.9rem',
                  }}
                >
                  {showTranslation ? <EyeOff size={16} /> : <Eye size={16} />}
                  {showTranslation ? 'Hide Translation' : 'Show Translation'}
                </button>
                {showTranslation && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    style={{ marginTop: '12px', padding: '12px', background: 'var(--bg-card)', borderRadius: '12px', color: 'var(--text-dim)', fontSize: '1rem' }}
                  >
                    {activePassage.translation}
                  </motion.div>
                )}
              </div>

              {/* Vocabulary */}
              <div style={{ marginBottom: '24px' }}>
                <h4 style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>
                  Key Vocabulary
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {activePassage.vocabulary.map((v, i) => (
                    <span key={i} style={{ padding: '6px 14px', background: 'var(--bg-main)', borderRadius: '12px', border: '1px solid var(--border-soft)', fontSize: '0.9rem' }}>
                      <span className="devanagari" style={{ fontWeight: 700, color: 'var(--primary)' }}>{v.word}</span>
                      <span style={{ color: 'var(--text-dim)', marginLeft: '6px' }}>— {v.meaning}</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Questions */}
              <div>
                <h4 style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>
                  Comprehension Questions
                </h4>
                <div className="flex flex-col gap-4">
                  {activePassage.questions.map((q, index) => {
                    const isAnswered = answeredQuestions[index] !== undefined;
                    const isCorrect = questionFeedback[index];
                    return (
                      <div key={index} style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)' }}>
                        <div className="devanagari" style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px' }}>
                          {q.question}
                        </div>
                        {!isAnswered ? (
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <input
                              type="text"
                              placeholder="Type your answer in Sanskrit..."
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  handleQuestionAnswer(index, e.currentTarget.value);
                                }
                              }}
                              style={{
                                flex: 1,
                                padding: '10px 16px',
                                borderRadius: '12px',
                                border: '1px solid var(--border-soft)',
                                background: 'var(--bg-card)',
                                color: 'var(--text-main)',
                                fontSize: '0.95rem',
                                outline: 'none',
                              }}
                            />
                            <button
                              onClick={(e) => {
                                const input = e.currentTarget.parentElement?.querySelector('input') as HTMLInputElement;
                                if (input) handleQuestionAnswer(index, input.value);
                              }}
                              className="btn-primary"
                              style={{ padding: '10px 20px' }}
                            >
                              <CheckCircle2 size={18} />
                            </button>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <span style={{ fontWeight: 600, color: isCorrect ? '#4CAF50' : '#FF5252' }}>
                              {isCorrect ? '✅ Correct!' : '❌ Incorrect. Expected: '}
                              {!isCorrect && <span className="devanagari" style={{ fontWeight: 700 }}>{q.answer}</span>}
                            </span>
                            {isCorrect && <span className="devanagari" style={{ fontWeight: 700, color: '#4CAF50' }}>{answeredQuestions[index]}</span>}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      ) : (
        // Composition Tab
        <div className="zen-card" style={{ padding: '40px', maxWidth: '800px', margin: '0 auto' }}>
          <div className="flex items-center gap-3 mb-6">
            <PenLine size={24} color="var(--primary)" />
            <h2 style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--text-main)' }}>
              Composition Exercise
            </h2>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <p style={{ fontSize: '1.1rem', color: 'var(--text-dim)', marginBottom: '16px' }}>
              {activePassage.composition_prompt}
            </p>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', fontStyle: 'italic' }}>
              Try to use at least 3 new vocabulary words from the passage.
            </p>
          </div>

          {!compositionSubmitted ? (
            <div>
              <textarea
                value={compositionText}
                onChange={(e) => setCompositionText(e.target.value)}
                placeholder="Write your composition in Sanskrit here (3-5 sentences)..."
                style={{
                  width: '100%',
                  minHeight: '200px',
                  padding: '20px',
                  fontSize: '1.2rem',
                  fontFamily: '"Noto Sans Devanagari", sans-serif',
                  borderRadius: '16px',
                  border: '1px solid var(--border-soft)',
                  background: 'var(--bg-main)',
                  color: 'var(--text-main)',
                  resize: 'vertical',
                  outline: 'none',
                }}
              />
              <div className="flex justify-end mt-4">
                <button
                  onClick={handleCompositionSubmit}
                  className="btn-primary"
                  style={{ padding: '12px 32px' }}
                  disabled={compositionText.trim().length < 10}
                >
                  Submit Composition <ChevronRight size={18} />
                </button>
              </div>
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{ padding: '24px', background: 'rgba(76, 175, 80, 0.08)', borderRadius: '16px', border: '1px solid #4CAF50' }}
            >
              <div className="flex items-center gap-3 mb-4">
                <CheckCircle2 size={24} color="#4CAF50" />
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#4CAF50' }}>Composition Submitted!</h3>
              </div>
              <div className="devanagari" style={{ fontSize: '1.2rem', lineHeight: '1.8', color: 'var(--text-main)', whiteSpace: 'pre-wrap' }}>
                {compositionText}
              </div>
              <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => {
                    setCompositionSubmitted(false);
                    setCompositionText('');
                  }}
                  className="btn-secondary"
                  style={{ padding: '10px 24px' }}
                >
                  <RotateCcw size={16} /> Rewrite
                </button>
                <button
                  onClick={onBack}
                  className="btn-primary"
                  style={{ padding: '10px 24px' }}
                >
                  Finish Lesson <CheckCircle2 size={18} />
                </button>
              </div>
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}
