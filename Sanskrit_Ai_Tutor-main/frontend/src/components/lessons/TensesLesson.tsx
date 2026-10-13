'use client';
import React, { useState, useEffect } from 'react';
import { ArrowLeft, CheckCircle2, Sparkles, RotateCcw, Award, Clock, Calendar, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface Conjugation {
  person: string;
  sanskrit: string;
  transliteration: string;
  english: string;
}

interface TenseData {
  id: string;
  name: string;
  description: string;
  conjugations: Conjugation[];
  example_sentence: string;
  translation: string;
}

export default function TensesLesson({ onBack }: { onBack: () => void }) {
  const [tenses, setTenses] = useState<TenseData[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTense, setActiveTense] = useState<TenseData | null>(null);
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
        const res = await api.lessons.getTenses();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setTenses(data);
        if (data.length > 0) setActiveTense(data[0]);
      } catch (error) {
        console.error('Failed to fetch tenses data', error);
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
    // Collect all verb forms from all tenses
    const allForms = tenses.flatMap(t => 
      t.conjugations.map(c => ({ ...c, tenseName: t.name, tenseId: t.id }))
    );
    if (allForms.length === 0) return;

    const randomIndex = Math.floor(Math.random() * allForms.length);
    const question = allForms[randomIndex];

    // Options: show 3 tense names, one correct
    const allTenseNames = tenses.map(t => t.name);
    const distractors = allTenseNames.filter(name => name !== question.tenseName);
    const shuffledDistractors = distractors.sort(() => Math.random() - 0.5).slice(0, 3);
    const options = [question.tenseName, ...shuffledDistractors].sort(() => Math.random() - 0.5);

    setQuizQuestion({
      ...question,
      options,
    });
  };

  const handleQuizAnswer = (selected: string) => {
    if (!quizQuestion) return;
    const correct = selected === quizQuestion.tenseName;
    setQuizFeedback({
      correct,
      message: correct
        ? `✅ Correct! "${quizQuestion.sanskrit}" is ${quizQuestion.tenseName} tense.`
        : `❌ Incorrect. "${quizQuestion.sanskrit}" is ${quizQuestion.tenseName} tense.`,
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
          <Clock size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Verb Tenses...</h3>
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
          <div style={{ background: 'linear-gradient(135deg, #3B82F6, #1D4ED8)', color: 'white', padding: '24px', borderRadius: '50%' }}>
            <Award size={56} />
          </div>
        </div>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Tense Master!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You identified <b>{score}</b> out of {totalQuestions} tenses correctly.
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
              Verb Tenses – Past, Present & Future
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              {quizMode ? 'Identify the tense of the verb form!' : 'Explore conjugation patterns across time.'}
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
              key={quizQuestion.sanskrit}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div style={{ fontSize: '1.2rem', marginBottom: '12px', fontWeight: 600, color: 'var(--text-dim)' }}>
                Which tense is the verb form?
              </div>
              <div className="devanagari" style={{ fontSize: '3rem', fontWeight: 900, color: 'var(--text-main)', marginBottom: '8px' }}>
                {quizQuestion.sanskrit}
              </div>
              <div style={{ fontSize: '1rem', color: 'var(--text-light)', marginBottom: '24px' }}>
                Meaning: "{quizQuestion.english}" ({quizQuestion.person})
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
                      background: quizFeedback && opt === quizQuestion.tenseName ? 'rgba(76, 175, 80, 0.1)' : 'var(--bg-main)',
                      fontWeight: 700,
                      cursor: quizFeedback ? 'default' : 'pointer',
                      transition: 'all 0.2s',
                      color: quizFeedback && opt === quizQuestion.tenseName ? '#4CAF50' : 'var(--text-main)',
                      borderColor: quizFeedback && opt === quizQuestion.tenseName ? '#4CAF50' : 'var(--border-soft)',
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
        // Main content: Tenses overview with conjugation tables
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar: Tense list */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
                Tenses
              </h3>
              <div className="flex flex-col gap-2">
                {tenses.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveTense(t)}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '12px',
                      background: activeTense?.id === t.id ? 'var(--primary)' : 'var(--bg-main)',
                      color: activeTense?.id === t.id ? '#fff' : 'var(--text-main)',
                      border: '1px solid var(--border-soft)',
                      textAlign: 'left',
                      fontWeight: 700,
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    <div style={{ fontSize: '1rem' }}>{t.name}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="lg:col-span-2">
            {activeTense && (
              <motion.div
                key={activeTense.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="zen-card"
                style={{ padding: '32px' }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <Calendar size={24} color="var(--primary)" />
                  <div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--text-main)' }}>
                      {activeTense.name} Tense
                    </h2>
                    <p style={{ color: 'var(--text-dim)' }}>{activeTense.description}</p>
                  </div>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.95rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--border-soft)' }}>
                        <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 800, color: 'var(--text-dim)' }}>Person</th>
                        <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 800, color: 'var(--text-dim)' }}>Sanskrit</th>
                        <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 800, color: 'var(--text-dim)' }}>Transliteration</th>
                        <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 800, color: 'var(--text-dim)' }}>English</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeTense.conjugations.map((c, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-soft)' }}>
                          <td style={{ padding: '10px 8px', fontWeight: 600 }}>{c.person}</td>
                          <td className="devanagari" style={{ padding: '10px 8px', fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary)' }}>
                            {c.sanskrit}
                          </td>
                          <td style={{ padding: '10px 8px', fontStyle: 'italic' }}>{c.transliteration}</td>
                          <td style={{ padding: '10px 8px' }}>{c.english}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div style={{ marginTop: '24px', padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>
                    Example Sentence
                  </div>
                  <div className="devanagari" style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    {activeTense.example_sentence}
                  </div>
                  <div style={{ fontSize: '1rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                    {activeTense.translation}
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
