'use client';
import React, { useState, useEffect } from 'react';
import { ArrowLeft, CheckCircle2, Sparkles, RotateCcw, Award, Zap, BookOpen, GitMerge } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface SandhiRule {
  rule_name: string;
  rule: string;
  example_before: string;
  example_after: string;
  example_sentence: string;
  translation: string;
}

interface SandhiCategory {
  id: string;
  category: string;
  description: string;
  rules: SandhiRule[];
}

export default function SandhiLesson({ onBack }: { onBack: () => void }) {
  const [sandhiData, setSandhiData] = useState<SandhiCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState<SandhiCategory | null>(null);
  const [quizMode, setQuizMode] = useState(false);
  const [quizQuestion, setQuizQuestion] = useState<any>(null);
  const [quizOptions, setQuizOptions] = useState<string[]>([]);
  const [quizFeedback, setQuizFeedback] = useState<{ correct: boolean; message: string } | null>(null);
  const [score, setScore] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [quizComplete, setQuizComplete] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.lessons.getSandhi();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setSandhiData(data);
        if (data.length > 0) setActiveCategory(data[0]);
      } catch (error) {
        console.error('Failed to fetch sandhi data', error);
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
    const allRules = sandhiData.flatMap(c => c.rules.map(r => ({ ...r, category: c.category })));
    if (allRules.length === 0) return;

    const randomIndex = Math.floor(Math.random() * allRules.length);
    const question = allRules[randomIndex];

    // Options: Show 4 possible rules, one is correct
    const allRuleNames = allRules.map(r => r.rule_name);
    const distractors = allRuleNames.filter(name => name !== question.rule_name);
    const shuffledDistractors = distractors.sort(() => Math.random() - 0.5).slice(0, 3);
    const options = [question.rule_name, ...shuffledDistractors].sort(() => Math.random() - 0.5);

    setQuizQuestion({
      ...question,
      options,
    });
  };

  const handleQuizAnswer = (selected: string) => {
    if (!quizQuestion) return;
    const correct = selected === quizQuestion.rule_name;
    setQuizFeedback({
      correct,
      message: correct
        ? `✅ Correct! The rule is "${quizQuestion.rule_name}". ${quizQuestion.rule}`
        : `❌ The correct rule is "${quizQuestion.rule_name}". ${quizQuestion.rule}`,
    });
    setTotalQuestions(t => t + 1);
    if (correct) setScore(s => s + 1);
    setShowAnswer(true);

    setTimeout(() => {
      if (totalQuestions + 1 >= 8) {
        setQuizComplete(true);
        setQuizMode(false);
      } else {
        setQuizFeedback(null);
        setShowAnswer(false);
        generateQuizQuestion();
      }
    }, 2500);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}>
          <GitMerge size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Sandhi Rules...</h3>
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
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Sandhi Master!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You identified <b>{score}</b> out of {totalQuestions} sandhi rules correctly.
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

  const allRules = sandhiData.flatMap(c => c.rules);
  const totalRules = allRules.length;

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
              सन्धिः – Sandhi Rules
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              {quizMode ? 'Identify the correct sandhi rule!' : `${totalRules} rules to master sound combination`}
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
              key={quizQuestion.example_before}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div style={{ fontSize: '1.2rem', marginBottom: '12px', fontWeight: 600, color: 'var(--text-dim)' }}>
                What sandhi rule is applied here?
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', marginBottom: '8px' }}>
                <div className="devanagari" style={{ fontSize: '2.2rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  {quizQuestion.example_before}
                </div>
                <span style={{ fontSize: '1.5rem', color: 'var(--text-light)' }}>→</span>
                <div className="devanagari" style={{ fontSize: '2.2rem', fontWeight: 700, color: 'var(--primary)' }}>
                  {quizQuestion.example_after}
                </div>
              </div>
              <div style={{ fontSize: '0.95rem', color: 'var(--text-light)', marginBottom: '24px' }}>
                Category: <strong>{quizQuestion.category}</strong>
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
                      background: quizFeedback && opt === quizQuestion.rule_name ? 'rgba(76, 175, 80, 0.1)' : 'var(--bg-main)',
                      fontWeight: 700,
                      cursor: quizFeedback ? 'default' : 'pointer',
                      transition: 'all 0.2s',
                      color: quizFeedback && opt === quizQuestion.rule_name ? '#4CAF50' : 'var(--text-main)',
                      borderColor: quizFeedback && opt === quizQuestion.rule_name ? '#4CAF50' : 'var(--border-soft)',
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
        // Main content: Rules by category
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar: Category list */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
                Sandhi Types
              </h3>
              <div className="flex flex-col gap-2">
                {sandhiData.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setActiveCategory(c)}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '12px',
                      background: activeCategory?.id === c.id ? 'var(--primary)' : 'var(--bg-main)',
                      color: activeCategory?.id === c.id ? '#fff' : 'var(--text-main)',
                      border: '1px solid var(--border-soft)',
                      textAlign: 'left',
                      fontWeight: 700,
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    <div style={{ fontSize: '0.9rem' }}>{c.category}</div>
                    <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>{c.rules.length} rules</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="lg:col-span-2">
            {activeCategory && (
              <motion.div
                key={activeCategory.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="zen-card"
                style={{ padding: '32px' }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <BookOpen size={24} color="var(--primary)" />
                  <div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--text-main)' }}>
                      {activeCategory.category}
                    </h2>
                    <p style={{ color: 'var(--text-dim)' }}>{activeCategory.description}</p>
                  </div>
                </div>

                <div className="flex flex-col gap-6">
                  {activeCategory.rules.map((rule, i) => (
                    <div
                      key={i}
                      style={{
                        padding: '20px',
                        background: 'var(--bg-main)',
                        borderRadius: '16px',
                        border: '1px solid var(--border-soft)',
                      }}
                    >
                      <div className="flex justify-between items-start mb-3">
                        <h4 style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--text-main)' }}>
                          {rule.rule_name}
                        </h4>
                        <span className="badge badge-primary" style={{ fontSize: '0.7rem' }}>
                          {rule.rule}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
                        <div className="devanagari" style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-main)' }}>
                          {rule.example_before}
                        </div>
                        <span style={{ fontSize: '1.2rem', color: 'var(--text-light)' }}>→</span>
                        <div className="devanagari" style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--primary)' }}>
                          {rule.example_after}
                        </div>
                      </div>

                      <div style={{ padding: '12px', background: 'rgba(var(--primary-rgb), 0.06)', borderRadius: '12px' }}>
                        <div className="devanagari" style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-main)' }}>
                          {rule.example_sentence}
                        </div>
                        <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)' }}>
                          {rule.translation}
                        </div>
                      </div>
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
