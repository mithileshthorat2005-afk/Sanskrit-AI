'use client';
import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  ArrowRight,
  CheckCircle2, 
  Sparkles, 
  RotateCcw, 
  Award,
  MoveLeft,
  MoveRight,
  MoveUp,
  MoveDown,
  Zap,
  Search,
  BookOpen
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface UpasargaData {
  id: string;
  prefix: string;
  transliteration: string;
  meaning: string;
  example_verb: string;
  example_with_prefix: string;
  example_translation: string;
  example_sentence: string;
  sentence_translation: string;
}

export default function UpasargaLesson({ onBack }: { onBack: () => void }) {
  const [upasargas, setUpasargas] = useState<UpasargaData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPrefix, setSelectedPrefix] = useState<UpasargaData | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
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
        const res = await api.lessons.getUpasarga();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setUpasargas(data);
        if (data.length > 0) setSelectedPrefix(data[0]);
      } catch (error) {
        console.error('Failed to fetch upasarga data', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const filteredUpasargas = upasargas.filter(u =>
    u.prefix.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.transliteration.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.meaning.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.example_with_prefix.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getPrefixIcon = (prefix: string) => {
    const lower = prefix.toLowerCase();
    if (lower === 'प्र') return <MoveRight size={18} />;
    if (lower === 'परा') return <MoveLeft size={18} />;
    if (lower === 'अप') return <MoveDown size={18} />;
    if (lower === 'उत्') return <MoveUp size={18} />;
    if (lower === 'सम्') return <Sparkles size={18} />;
    return <BookOpen size={18} />;
  };

  const startQuiz = () => {
    setQuizMode(true);
    setScore(0);
    setTotalQuestions(0);
    setQuizComplete(false);
    setQuizFeedback(null);
    generateQuizQuestion();
  };

  const generateQuizQuestion = () => {
    if (upasargas.length === 0) return;

    const randomIndex = Math.floor(Math.random() * upasargas.length);
    const question = upasargas[randomIndex];

    // Options: Given a prefix, find its meaning
    const allMeanings = upasargas.map(u => u.meaning);
    const distractors = allMeanings.filter(m => m !== question.meaning);
    const shuffledDistractors = distractors.sort(() => Math.random() - 0.5).slice(0, 3);
    const options = [question.meaning, ...shuffledDistractors].sort(() => Math.random() - 0.5);

    setQuizQuestion({
      ...question,
      options,
      correctAnswer: question.meaning,
    });
  };

  const handleQuizAnswer = (selected: string) => {
    if (!quizQuestion) return;
    const correct = selected === quizQuestion.correctAnswer;
    setQuizFeedback({
      correct,
      message: correct
        ? `✅ Correct! "${quizQuestion.prefix}" means "${quizQuestion.meaning}".`
        : `❌ Incorrect. "${quizQuestion.prefix}" means "${quizQuestion.meaning}".`,
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
          <MoveRight size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Verbal Prefixes...</h3>
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
          <div style={{ background: 'linear-gradient(135deg, #10B981, #059669)', color: 'white', padding: '24px', borderRadius: '50%' }}>
            <Award size={56} />
          </div>
        </div>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Prefix Master!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You identified <b>{score}</b> out of {totalQuestions} verbal prefixes correctly.
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
              उपसर्ग – Verbal Prefixes
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              {quizMode ? 'Match the prefix to its meaning!' : '22 prefixes that transform verb meanings.'}
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
              key={quizQuestion.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div style={{ fontSize: '1.2rem', marginBottom: '12px', fontWeight: 600, color: 'var(--text-dim)' }}>
                What is the meaning of this prefix?
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', justifyContent: 'center', marginBottom: '16px' }}>
                <div className="devanagari" style={{ fontSize: '4rem', fontWeight: 900, color: 'var(--primary)' }}>
                  {quizQuestion.prefix}
                </div>
                <span style={{ fontSize: '1.5rem', color: 'var(--text-light)' }}>+</span>
                <div style={{ fontSize: '1.2rem', color: 'var(--text-dim)' }}>{quizQuestion.example_verb}</div>
              </div>
              <div style={{ fontSize: '1.2rem', color: 'var(--text-main)', textAlign: 'center', marginBottom: '24px' }}>
                → <span className="devanagari" style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)' }}>{quizQuestion.example_with_prefix}</span>
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
        // Main content: Prefix cards with details
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Prefix list with search */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <div style={{ position: 'relative', marginBottom: '16px' }}>
                <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-light)' }} />
                <input
                  type="text"
                  placeholder="Search prefixes..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px 10px 36px',
                    borderRadius: '12px',
                    border: '1px solid var(--border-soft)',
                    background: 'var(--bg-main)',
                    color: 'var(--text-main)',
                    fontSize: '0.9rem',
                    outline: 'none',
                  }}
                />
              </div>

              <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                {filteredUpasargas.map((u) => {
                  const isSelected = selectedPrefix?.id === u.id;
                  return (
                    <button
                      key={u.id}
                      onClick={() => setSelectedPrefix(u)}
                      style={{
                        width: '100%',
                        padding: '12px 16px',
                        borderRadius: '12px',
                        background: isSelected ? 'var(--primary)' : 'var(--bg-main)',
                        color: isSelected ? '#fff' : 'var(--text-main)',
                        border: '1px solid var(--border-soft)',
                        textAlign: 'left',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        marginBottom: '4px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                      }}
                    >
                      <div className="devanagari" style={{ fontSize: '1.8rem', fontWeight: 900 }}>
                        {u.prefix}
                      </div>
                      <div>
                        <div style={{ fontSize: '0.8rem', opacity: 0.7 }}>{u.transliteration}</div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 700 }}>{u.meaning}</div>
                      </div>
                    </button>
                  );
                })}
                {filteredUpasargas.length === 0 && (
                  <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-dim)' }}>
                    No prefixes found.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="lg:col-span-2">
            {selectedPrefix && (
              <motion.div
                key={selectedPrefix.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="zen-card"
                style={{ padding: '32px' }}
              >
                <div className="flex items-center gap-4 mb-6">
                  <div style={{ 
                    padding: '16px', 
                    borderRadius: '16px', 
                    background: 'var(--primary-light)',
                    color: 'var(--primary)'
                  }}>
                    {getPrefixIcon(selectedPrefix.prefix)}
                  </div>
                  <div>
                    <div className="devanagari" style={{ fontSize: '2.8rem', fontWeight: 900, color: 'var(--primary)' }}>
                      {selectedPrefix.prefix}
                    </div>
                    <div style={{ fontSize: '1rem', fontWeight: 700 }}>{selectedPrefix.transliteration}</div>
                  </div>
                </div>

                <div style={{ marginBottom: '24px' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 800 }}>
                    Meaning
                  </div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    {selectedPrefix.meaning}
                  </div>
                </div>

                <div style={{ marginBottom: '24px' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 800 }}>
                    Example
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', padding: '16px', background: 'var(--bg-main)', borderRadius: '12px' }}>
                    <div className="devanagari" style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-main)' }}>
                      {selectedPrefix.prefix}
                    </div>
                    <span style={{ color: 'var(--text-light)' }}>+</span>
                    <div className="devanagari" style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-main)' }}>
                      {selectedPrefix.example_verb}
                    </div>
                    <span style={{ color: 'var(--text-light)' }}>→</span>
                    <div className="devanagari" style={{ fontSize: '1.8rem', fontWeight: 900, color: 'var(--primary)' }}>
                      {selectedPrefix.example_with_prefix}
                    </div>
                  </div>
                  <div style={{ fontSize: '1rem', color: 'var(--text-dim)', marginTop: '8px' }}>
                    {selectedPrefix.example_translation}
                  </div>
                </div>

                <div style={{ padding: '16px', background: 'rgba(var(--primary-rgb), 0.06)', borderRadius: '16px' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 800, marginBottom: '8px' }}>
                    Example Sentence
                  </div>
                  <div className="devanagari" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    {selectedPrefix.example_sentence}
                  </div>
                  <div style={{ fontSize: '1rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                    {selectedPrefix.sentence_translation}
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
