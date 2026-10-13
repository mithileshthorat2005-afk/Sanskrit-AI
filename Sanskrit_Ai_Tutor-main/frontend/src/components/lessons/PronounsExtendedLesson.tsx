'use client';
import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  Sparkles, 
  RotateCcw, 
  Award,
  Users,
  User,
  UserPlus,
  UsersRound,
  Zap,
  Filter
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface PronounData {
  id: string;
  category: string;
  number: string;
  gender: string | null;
  sanskrit: string;
  transliteration: string;
  englishMeaning: string;
}

export default function PronounsExtendedLesson({ onBack }: { onBack: () => void }) {
  const [pronouns, setPronouns] = useState<PronounData[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState<string | null>(null);
  const [filterNumber, setFilterNumber] = useState<string | null>(null);
  const [filterGender, setFilterGender] = useState<string | null>(null);
  const [selectedPronoun, setSelectedPronoun] = useState<PronounData | null>(null);
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
        const res = await api.lessons.getPronounsExtended();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setPronouns(data);
        if (data.length > 0) setSelectedPronoun(data[0]);
      } catch (error) {
        console.error('Failed to fetch extended pronouns', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const getFilteredPronouns = () => {
    let filtered = pronouns;
    if (filterCategory) {
      filtered = filtered.filter(p => p.category === filterCategory);
    }
    if (filterNumber) {
      filtered = filtered.filter(p => p.number === filterNumber);
    }
    if (filterGender) {
      filtered = filtered.filter(p => p.gender === filterGender);
    }
    return filtered;
  };

  const filteredPronouns = getFilteredPronouns();

  // Get unique categories, numbers, genders for filter buttons
  const categories = [...new Set(pronouns.map(p => p.category))];
  const numbers = [...new Set(pronouns.map(p => p.number))];
  const genders = [...new Set(pronouns.filter(p => p.gender).map(p => p.gender))];

  const startQuiz = () => {
    setQuizMode(true);
    setScore(0);
    setTotalQuestions(0);
    setQuizComplete(false);
    setQuizFeedback(null);
    generateQuizQuestion();
  };

  const generateQuizQuestion = () => {
    // All pronoun forms as potential questions
    const allForms = pronouns.map(p => ({ ...p }));
    if (allForms.length === 0) return;

    const randomIndex = Math.floor(Math.random() * allForms.length);
    const question = allForms[randomIndex];

    // Build a question: given an English meaning, find the correct Sanskrit form
    // We'll show 4 options, one correct.
    const allMeanings = pronouns.map(p => p.englishMeaning);
    const distractors = allMeanings.filter(m => m !== question.englishMeaning);
    const shuffledDistractors = distractors.sort(() => Math.random() - 0.5).slice(0, 3);
    const options = [question.englishMeaning, ...shuffledDistractors].sort(() => Math.random() - 0.5);

    setQuizQuestion({
      ...question,
      options,
      correctAnswer: question.englishMeaning,
    });
  };

  const handleQuizAnswer = (selected: string) => {
    if (!quizQuestion) return;
    const correct = selected === quizQuestion.correctAnswer;
    setQuizFeedback({
      correct,
      message: correct
        ? `✅ Correct! "${quizQuestion.sanskrit}" means "${quizQuestion.englishMeaning}".`
        : `❌ Incorrect. The correct meaning is "${quizQuestion.englishMeaning}".`,
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
          <Users size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Pronoun Forms...</h3>
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
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Pronoun Pro!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You identified <b>{score}</b> out of {totalQuestions} pronoun forms correctly.
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
              Pronouns – Dual & Plural
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              {quizMode ? 'Match the Sanskrit pronoun to its meaning!' : 'Explore all pronoun forms by category, number, and gender.'}
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
                What is the meaning of this pronoun?
              </div>
              <div className="devanagari" style={{ fontSize: '3.5rem', fontWeight: 900, color: 'var(--primary)', marginBottom: '8px' }}>
                {quizQuestion.sanskrit}
              </div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginBottom: '24px' }}>
                {quizQuestion.category} · {quizQuestion.number} · {quizQuestion.gender || 'no gender'}
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
        // Main content: Pronouns grid with filters
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Filters sidebar */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <div className="flex items-center gap-2 mb-4">
                <Filter size={18} color="var(--primary)" />
                <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                  Filters
                </h3>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px' }}>Category</div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setFilterCategory(null)}
                    style={{
                      padding: '4px 12px',
                      borderRadius: '8px',
                      background: !filterCategory ? 'var(--primary)' : 'var(--bg-main)',
                      color: !filterCategory ? '#fff' : 'var(--text-dim)',
                      border: '1px solid var(--border-soft)',
                      fontSize: '0.75rem',
                      cursor: 'pointer'
                    }}
                  >
                    All
                  </button>
                  {categories.map(cat => (
                    <button
                      key={cat}
                      onClick={() => setFilterCategory(filterCategory === cat ? null : cat)}
                      style={{
                        padding: '4px 12px',
                        borderRadius: '8px',
                        background: filterCategory === cat ? 'var(--primary)' : 'var(--bg-main)',
                        color: filterCategory === cat ? '#fff' : 'var(--text-dim)',
                        border: '1px solid var(--border-soft)',
                        fontSize: '0.75rem',
                        cursor: 'pointer'
                      }}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px' }}>Number</div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setFilterNumber(null)}
                    style={{
                      padding: '4px 12px',
                      borderRadius: '8px',
                      background: !filterNumber ? 'var(--primary)' : 'var(--bg-main)',
                      color: !filterNumber ? '#fff' : 'var(--text-dim)',
                      border: '1px solid var(--border-soft)',
                      fontSize: '0.75rem',
                      cursor: 'pointer'
                    }}
                  >
                    All
                  </button>
                  {numbers.map(num => (
                    <button
                      key={num}
                      onClick={() => setFilterNumber(filterNumber === num ? null : num)}
                      style={{
                        padding: '4px 12px',
                        borderRadius: '8px',
                        background: filterNumber === num ? 'var(--primary)' : 'var(--bg-main)',
                        color: filterNumber === num ? '#fff' : 'var(--text-dim)',
                        border: '1px solid var(--border-soft)',
                        fontSize: '0.75rem',
                        cursor: 'pointer'
                      }}
                    >
                      {num}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px' }}>Gender</div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setFilterGender(null)}
                    style={{
                      padding: '4px 12px',
                      borderRadius: '8px',
                      background: !filterGender ? 'var(--primary)' : 'var(--bg-main)',
                      color: !filterGender ? '#fff' : 'var(--text-dim)',
                      border: '1px solid var(--border-soft)',
                      fontSize: '0.75rem',
                      cursor: 'pointer'
                    }}
                  >
                    All
                  </button>
                  {genders.map(g => (
                    <button
                      key={g}
                      onClick={() => setFilterGender(filterGender === g ? null : g)}
                      style={{
                        padding: '4px 12px',
                        borderRadius: '8px',
                        background: filterGender === g ? 'var(--primary)' : 'var(--bg-main)',
                        color: filterGender === g ? '#fff' : 'var(--text-dim)',
                        border: '1px solid var(--border-soft)',
                        fontSize: '0.75rem',
                        cursor: 'pointer'
                      }}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Pronoun Cards */}
          <div className="lg:col-span-3">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {filteredPronouns.map((p) => {
                const isSelected = selectedPronoun?.id === p.id;
                let icon;
                if (p.category === 'First Person') icon = <User size={20} />;
                else if (p.category === 'Second Person') icon = <UserPlus size={20} />;
                else if (p.category === 'Third Person') icon = <UsersRound size={20} />;
                else icon = <Users size={20} />;

                return (
                  <motion.div
                    key={p.id}
                    whileHover={{ y: -4 }}
                    onClick={() => setSelectedPronoun(p)}
                    style={{
                      padding: '20px',
                      borderRadius: '16px',
                      background: isSelected ? 'var(--primary)' : 'var(--bg-main)',
                      color: isSelected ? '#fff' : 'var(--text-main)',
                      border: '1px solid var(--border-soft)',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      boxShadow: isSelected ? '0 8px 24px rgba(var(--primary-rgb), 0.2)' : 'none',
                    }}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      {icon}
                      <span style={{ fontSize: '0.7rem', opacity: 0.7, textTransform: 'uppercase' }}>{p.number}</span>
                      {p.gender && <span style={{ fontSize: '0.7rem', opacity: 0.7 }}>· {p.gender}</span>}
                    </div>
                    <div className="devanagari" style={{ fontSize: '2.2rem', fontWeight: 900 }}>
                      {p.sanskrit}
                    </div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 600, opacity: 0.8 }}>
                      {p.transliteration}
                    </div>
                    <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                      {p.englishMeaning}
                    </div>
                  </motion.div>
                );
              })}
              {filteredPronouns.length === 0 && (
                <div style={{ gridColumn: '1 / -1', padding: '40px', textAlign: 'center', color: 'var(--text-dim)' }}>
                  No pronouns match the current filters.
                </div>
              )}
            </div>

            {/* Selected pronoun details */}
            {selectedPronoun && (
              <motion.div
                key={selectedPronoun.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ marginTop: '24px', padding: '20px', background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border-soft)' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div className="devanagari" style={{ fontSize: '2.5rem', fontWeight: 900, color: 'var(--primary)' }}>
                      {selectedPronoun.sanskrit}
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>{selectedPronoun.transliteration}</div>
                    <div style={{ color: 'var(--text-dim)' }}>{selectedPronoun.englishMeaning}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>{selectedPronoun.category}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>{selectedPronoun.number}</div>
                    {selectedPronoun.gender && <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>{selectedPronoun.gender}</div>}
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
