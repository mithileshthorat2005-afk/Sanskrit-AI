'use client';
import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  Sparkles, 
  RotateCcw, 
  Award,
  FileText,
  Clock,
  ArrowRight,
  Zap,
  BookOpen
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface Example {
  root: string;
  participle: string;
  meaning: string;
  sentence: string;
  translation: string;
}

interface ParticipleCategory {
  id: string;
  category: string;
  description: string;
  formation: string;
  usage: string;
  examples: Example[];
}

export default function ParticiplesLesson({ onBack }: { onBack: () => void }) {
  const [participles, setParticiples] = useState<ParticipleCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState<ParticipleCategory | null>(null);
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
        const res = await api.lessons.getParticiples();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setParticiples(data);
        if (data.length > 0) setActiveCategory(data[0]);
      } catch (error) {
        console.error('Failed to fetch participles data', error);
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
    // Collect all examples from all categories
    const allExamples = participles.flatMap(c => 
      c.examples.map(ex => ({ 
        ...ex, 
        categoryName: c.category, 
        categoryId: c.id 
      }))
    );
    if (allExamples.length === 0) return;

    const randomIndex = Math.floor(Math.random() * allExamples.length);
    const question = allExamples[randomIndex];

    // Options: given a participle, identify its category
    const allCategoryNames = participles.map(c => c.category);
    const distractors = allCategoryNames.filter(name => name !== question.categoryName);
    const shuffledDistractors = distractors.sort(() => Math.random() - 0.5).slice(0, 3);
    const options = [question.categoryName, ...shuffledDistractors].sort(() => Math.random() - 0.5);

    setQuizQuestion({
      ...question,
      options,
      correctAnswer: question.categoryName,
    });
  };

  const handleQuizAnswer = (selected: string) => {
    if (!quizQuestion) return;
    const correct = selected === quizQuestion.correctAnswer;
    setQuizFeedback({
      correct,
      message: correct
        ? `✅ Correct! "${quizQuestion.participle}" is from ${quizQuestion.categoryName}.`
        : `❌ Incorrect. "${quizQuestion.participle}" is from ${quizQuestion.categoryName}.`,
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
          <FileText size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Participles...</h3>
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
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Participle Master!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You identified <b>{score}</b> out of {totalQuestions} participles correctly.
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

  const getCategoryColor = (category: string) => {
    if (category.includes('Past Passive')) return '#3B82F6';
    if (category.includes('Future Passive')) return '#10B981';
    if (category.includes('Gerund')) return '#F59E0B';
    return 'var(--primary)';
  };

  const getCategoryIcon = (category: string) => {
    if (category.includes('Past Passive')) return <Clock size={18} />;
    if (category.includes('Future Passive')) return <Sparkles size={18} />;
    if (category.includes('Gerund')) return <ArrowRight size={18} />;
    return <BookOpen size={18} />;
  };

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
              Participles – कृत् प्रत्यय
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              {quizMode ? 'Identify the participle type!' : 'Past, Future, and Gerund forms.'}
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
              key={quizQuestion.participle}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div style={{ fontSize: '1.2rem', marginBottom: '12px', fontWeight: 600, color: 'var(--text-dim)' }}>
                What type of participle is this?
              </div>
              <div className="devanagari" style={{ fontSize: '2.8rem', fontWeight: 900, color: 'var(--primary)', marginBottom: '8px' }}>
                {quizQuestion.participle}
              </div>
              <div style={{ fontSize: '1rem', color: 'var(--text-light)', marginBottom: '24px' }}>
                From root "{quizQuestion.root}" · Meaning: {quizQuestion.meaning}
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
        // Main content: Category details
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar: Category list */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
                Participle Types
              </h3>
              <div className="flex flex-col gap-2">
                {participles.map((c) => {
                  const isActive = activeCategory?.id === c.id;
                  const color = getCategoryColor(c.category);
                  return (
                    <button
                      key={c.id}
                      onClick={() => setActiveCategory(c)}
                      style={{
                        padding: '12px 16px',
                        borderRadius: '12px',
                        background: isActive ? color : 'var(--bg-main)',
                        color: isActive ? '#fff' : 'var(--text-main)',
                        border: '1px solid var(--border-soft)',
                        textAlign: 'left',
                        fontWeight: 700,
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                      }}
                    >
                      {getCategoryIcon(c.category)}
                      <div>
                        <div style={{ fontSize: '0.85rem' }}>{c.category}</div>
                        <div style={{ fontSize: '0.7rem', opacity: 0.7 }}>{c.examples.length} examples</div>
                      </div>
                    </button>
                  );
                })}
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
                  {getCategoryIcon(activeCategory.category)}
                  <div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--text-main)' }}>
                      {activeCategory.category}
                    </h2>
                    <p style={{ color: 'var(--text-dim)' }}>{activeCategory.description}</p>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '24px' }}>
                  <div style={{ padding: '12px', background: 'var(--bg-main)', borderRadius: '12px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>Formation</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '4px' }}>{activeCategory.formation}</div>
                  </div>
                  <div style={{ padding: '12px', background: 'var(--bg-main)', borderRadius: '12px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>Usage</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '4px' }}>{activeCategory.usage}</div>
                  </div>
                </div>

                <h4 style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>
                  Examples
                </h4>
                <div className="flex flex-col gap-4">
                  {activeCategory.examples.map((ex, i) => (
                    <div key={i} style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
                        <span style={{ padding: '4px 12px', background: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--border-soft)', fontSize: '0.8rem', fontWeight: 600 }}>
                          {ex.root}
                        </span>
                        <span style={{ padding: '4px 12px', background: 'rgba(var(--primary-rgb), 0.08)', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                          → {ex.participle}
                        </span>
                      </div>
                      <div className="devanagari" style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-main)' }}>
                        {ex.sentence}
                      </div>
                      <div style={{ fontSize: '0.95rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                        {ex.translation}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-light)', marginTop: '4px', fontStyle: 'italic' }}>
                        Meaning: {ex.meaning}
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
