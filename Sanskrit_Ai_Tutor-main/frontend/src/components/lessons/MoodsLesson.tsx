'use client';
import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  Sparkles, 
  RotateCcw, 
  Award, 
  Command,
  Wand2,
  Zap,
  BookOpen
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface Conjugation {
  person: string;
  sanskrit: string;
  transliteration: string;
  english: string;
}

interface ExampleSentence {
  sanskrit: string;
  translation: string;
  transliteration: string;
  context: string;
}

interface MoodData {
  id: string;
  name: string;
  description: string;
  usage_rules: string[];
  conjugations: Conjugation[];
  example_sentences: ExampleSentence[];
}

export default function MoodsLesson({ onBack }: { onBack: () => void }) {
  const [moods, setMoods] = useState<MoodData[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeMood, setActiveMood] = useState<MoodData | null>(null);
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
        const res = await api.lessons.getMoods();
        const data = res?.success ? res.data : (Array.isArray(res) ? res : []);
        setMoods(data);
        if (data.length > 0) setActiveMood(data[0]);
      } catch (error) {
        console.error('Failed to fetch moods data', error);
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
    // Collect all verb forms from all moods
    const allForms = moods.flatMap(m => 
      m.conjugations.map(c => ({ ...c, moodName: m.name, moodId: m.id }))
    );
    if (allForms.length === 0) return;

    const randomIndex = Math.floor(Math.random() * allForms.length);
    const question = allForms[randomIndex];

    // Options: show 3 mood names, one correct
    const allMoodNames = moods.map(m => m.name);
    const distractors = allMoodNames.filter(name => name !== question.moodName);
    const shuffledDistractors = distractors.sort(() => Math.random() - 0.5).slice(0, 3);
    const options = [question.moodName, ...shuffledDistractors].sort(() => Math.random() - 0.5);

    setQuizQuestion({
      ...question,
      options,
    });
  };

  const handleQuizAnswer = (selected: string) => {
    if (!quizQuestion) return;
    const correct = selected === quizQuestion.moodName;
    setQuizFeedback({
      correct,
      message: correct
        ? `✅ Correct! "${quizQuestion.sanskrit}" is from the ${quizQuestion.moodName} mood.`
        : `❌ Incorrect. "${quizQuestion.sanskrit}" is from the ${quizQuestion.moodName} mood.`,
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
          <Command size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Verb Moods...</h3>
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
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Mood Master!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
          You identified <b>{score}</b> out of {totalQuestions} verb moods correctly.
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

  const getMoodIcon = (moodName: string) => {
    if (moodName.toLowerCase().includes('imperative')) return <Command size={20} />;
    if (moodName.toLowerCase().includes('optative')) return <Wand2 size={20} />;
    return <BookOpen size={20} />;
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
              Verb Moods – Imperative & Optative
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              {quizMode ? 'Identify the mood of the verb form!' : 'Commands, wishes, and possibilities in Sanskrit.'}
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
                Which mood is this verb form?
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
                      background: quizFeedback && opt === quizQuestion.moodName ? 'rgba(76, 175, 80, 0.1)' : 'var(--bg-main)',
                      fontWeight: 700,
                      cursor: quizFeedback ? 'default' : 'pointer',
                      transition: 'all 0.2s',
                      color: quizFeedback && opt === quizQuestion.moodName ? '#4CAF50' : 'var(--text-main)',
                      borderColor: quizFeedback && opt === quizQuestion.moodName ? '#4CAF50' : 'var(--border-soft)',
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
        // Main content: Moods overview with conjugation tables
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar: Mood list */}
          <div className="lg:col-span-1">
            <div className="zen-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
                Verb Moods
              </h3>
              <div className="flex flex-col gap-2">
                {moods.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setActiveMood(m)}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '12px',
                      background: activeMood?.id === m.id ? 'var(--primary)' : 'var(--bg-main)',
                      color: activeMood?.id === m.id ? '#fff' : 'var(--text-main)',
                      border: '1px solid var(--border-soft)',
                      textAlign: 'left',
                      fontWeight: 700,
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    <div className="flex items-center gap-2">
                      {getMoodIcon(m.name)}
                      <span>{m.name}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="lg:col-span-2">
            {activeMood && (
              <motion.div
                key={activeMood.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="zen-card"
                style={{ padding: '32px' }}
              >
                <div className="flex items-center gap-3 mb-4">
                  {getMoodIcon(activeMood.name)}
                  <div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--text-main)' }}>
                      {activeMood.name} Mood
                    </h2>
                    <p style={{ color: 'var(--text-dim)' }}>{activeMood.description}</p>
                  </div>
                </div>

                {/* Usage Rules */}
                <div style={{ marginBottom: '24px', padding: '16px', background: 'rgba(var(--primary-rgb), 0.06)', borderRadius: '16px' }}>
                  <h4 style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>
                    Usage Rules
                  </h4>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {activeMood.usage_rules.map((rule, i) => (
                      <li key={i} style={{ padding: '6px 0', fontSize: '0.95rem', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: 'var(--primary)' }}>•</span>
                        {rule}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Conjugation Table */}
                <h4 style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>
                  Conjugations
                </h4>
                <div style={{ overflowX: 'auto', marginBottom: '24px' }}>
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
                      {activeMood.conjugations.map((c, i) => (
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

                {/* Example Sentences */}
                <h4 style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>
                  Example Sentences
                </h4>
                <div className="flex flex-col gap-3">
                  {activeMood.example_sentences.map((ex, i) => (
                    <div key={i} style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)' }}>
                      <div className="devanagari" style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-main)' }}>
                        {ex.sanskrit}
                      </div>
                      <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                        {ex.transliteration}
                      </div>
                      <div style={{ fontSize: '1rem', color: 'var(--text-light)', marginTop: '4px' }}>
                        {ex.translation}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--primary)', marginTop: '6px', fontWeight: 600 }}>
                        {ex.context}
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
