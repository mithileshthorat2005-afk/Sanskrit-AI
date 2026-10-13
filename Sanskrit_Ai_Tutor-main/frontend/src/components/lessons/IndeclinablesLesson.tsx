'use client';
import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  Sparkles, 
  RotateCcw, 
  Award,
  Hash,
  Link,
  Clock,
  MapPin,
  AtSign,
  Zap,
  Search,
  Filter
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface IndeclinableData {
  id: string;
  sanskrit: string;
  transliteration: string;
  meaning: string;
  category: string;
  usage: string;
  example_sentence: string;
  sentence_translation: string;
}

export default function IndeclinablesLesson({ onBack }: { onBack: () => void }) {
  const [indeclinables, setIndeclinables] = useState<IndeclinableData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItem, setSelectedItem] = useState<IndeclinableData | null>(null);
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
        const res = await api.lessons.getIndeclinables();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setIndeclinables(data);
        if (data.length > 0) setSelectedItem(data[0]);
      } catch (error) {
        console.error('Failed to fetch indeclinables data', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Get unique categories
  const categories = [...new Set(indeclinables.map(i => i.category))];

  const filteredItems = indeclinables.filter(i => {
    const matchesCategory = selectedCategory ? i.category === selectedCategory : true;
    const matchesSearch = 
      i.sanskrit.includes(searchTerm) ||
      i.transliteration.toLowerCase().includes(searchTerm.toLowerCase()) ||
      i.meaning.toLowerCase().includes(searchTerm.toLowerCase()) ||
      i.category.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const getCategoryIcon = (category: string) => {
    switch(category) {
      case 'Conjunction': return <Link size={18} />;
      case 'Adverb': return <Clock size={18} />;
      case 'Particle': return <AtSign size={18} />;
      case 'Preposition': return <MapPin size={18} />;
      case 'Interjection': return <Sparkles size={18} />;
      default: return <Hash size={18} />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch(category) {
      case 'Conjunction': return '#3B82F6';
      case 'Adverb': return '#10B981';
      case 'Particle': return '#F59E0B';
      case 'Preposition': return '#8B5CF6';
      case 'Interjection': return '#EC4899';
      default: return 'var(--primary)';
    }
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
    if (indeclinables.length === 0) return;

    const randomIndex = Math.floor(Math.random() * indeclinables.length);
    const question = indeclinables[randomIndex];

    // Options: given a Sanskrit word, find its meaning
    const allMeanings = indeclinables.map(i => i.meaning);
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
        ? `✅ Correct! "${quizQuestion.sanskrit}" means "${quizQuestion.meaning}".`
        : `❌ Incorrect. "${quizQuestion.sanskrit}" means "${quizQuestion.meaning}".`,
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
          <Hash size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Indeclinables...</h3>
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
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Avyaya Expert!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You identified <b>{score}</b> out of {totalQuestions} indeclinables correctly.
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
              Indeclinables – अव्यय
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              {quizMode ? 'Match the word to its meaning!' : '25 words that never change form.'}
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
                What is the meaning of this word?
              </div>
              <div className="devanagari" style={{ fontSize: '3.5rem', fontWeight: 900, color: 'var(--primary)', marginBottom: '8px' }}>
                {quizQuestion.sanskrit}
              </div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginBottom: '24px' }}>
                {quizQuestion.transliteration} · {quizQuestion.category}
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
        // Main content: Grid with filters
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Filters sidebar */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <div className="flex items-center gap-2 mb-4">
                <Filter size={18} color="var(--primary)" />
                <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                  Categories
                </h3>
              </div>

              <div style={{ position: 'relative', marginBottom: '16px' }}>
                <Search size={16} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-light)' }} />
                <input
                  type="text"
                  placeholder="Search words..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px 8px 32px',
                    borderRadius: '10px',
                    border: '1px solid var(--border-soft)',
                    background: 'var(--bg-main)',
                    color: 'var(--text-main)',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>

              <div className="flex flex-col gap-2">
                <button
                  onClick={() => setSelectedCategory(null)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: !selectedCategory ? 'var(--primary)' : 'var(--bg-main)',
                    color: !selectedCategory ? '#fff' : 'var(--text-dim)',
                    border: '1px solid var(--border-soft)',
                    textAlign: 'left',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    fontWeight: !selectedCategory ? 700 : 500,
                  }}
                >
                  All ({indeclinables.length})
                </button>
                {categories.map(cat => {
                  const count = indeclinables.filter(i => i.category === cat).length;
                  const color = getCategoryColor(cat);
                  const isSelected = selectedCategory === cat;
                  return (
                    <button
                      key={cat}
                      onClick={() => setSelectedCategory(isSelected ? null : cat)}
                      style={{
                        padding: '8px 12px',
                        borderRadius: '8px',
                        background: isSelected ? color : 'var(--bg-main)',
                        color: isSelected ? '#fff' : 'var(--text-dim)',
                        border: '1px solid var(--border-soft)',
                        textAlign: 'left',
                        fontSize: '0.85rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontWeight: isSelected ? 700 : 500,
                      }}
                    >
                      {getCategoryIcon(cat)}
                      <span>{cat}</span>
                      <span style={{ marginLeft: 'auto', opacity: 0.6, fontSize: '0.75rem' }}>{count}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Word Cards */}
          <div className="lg:col-span-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredItems.map((item) => {
                const color = getCategoryColor(item.category);
                const isSelected = selectedItem?.id === item.id;
                return (
                  <motion.div
                    key={item.id}
                    whileHover={{ y: -4 }}
                    onClick={() => setSelectedItem(item)}
                    style={{
                      padding: '20px',
                      borderRadius: '16px',
                      background: isSelected ? 'var(--bg-card)' : 'var(--bg-main)',
                      border: isSelected ? `2px solid ${color}` : '1px solid var(--border-soft)',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      boxShadow: isSelected ? `0 4px 16px ${color}22` : 'none',
                    }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="devanagari" style={{ fontSize: '2rem', fontWeight: 900, color: 'var(--text-main)' }}>
                        {item.sanskrit}
                      </div>
                      <span style={{ 
                        fontSize: '0.7rem', 
                        padding: '3px 10px', 
                        borderRadius: '8px', 
                        background: `${color}20`,
                        color: color,
                        fontWeight: 700,
                      }}>
                        {item.category}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-dim)' }}>
                      {item.transliteration}
                    </div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>
                      {item.meaning}
                    </div>
                    {isSelected && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-soft)' }}
                      >
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                          {item.usage}
                        </div>
                        <div className="devanagari" style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '6px' }}>
                          {item.example_sentence}
                        </div>
                        <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                          {item.sentence_translation}
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                );
              })}
              {filteredItems.length === 0 && (
                <div style={{ gridColumn: '1 / -1', padding: '40px', textAlign: 'center', color: 'var(--text-dim)' }}>
                  No words match the current filters.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
