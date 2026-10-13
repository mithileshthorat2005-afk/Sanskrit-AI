'use client';
import React, { useState, useEffect } from 'react';
import { ArrowLeft, CheckCircle2, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';

export default function StriPratyayaLesson({ onBack }: { onBack: () => void }) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [quizMode, setQuizMode] = useState(false);
  const [quizQuestion, setQuizQuestion] = useState<any>(null);
  const [score, setScore] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.lessons.getStriPratyaya();
        setData(res?.success ? res.data : (Array.isArray(res) ? res : []));
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const generateQuiz = () => {
    const allExamples = data.flatMap(d => d.examples.map((ex: any) => ({ ...ex, rule: d.rule, suffix: d.suffix })));
    if (!allExamples.length) return;
    const randomEx = allExamples[Math.floor(Math.random() * allExamples.length)];
    const distractors = allExamples.filter((ex: any) => ex.feminine !== randomEx.feminine).map((ex: any) => ex.feminine);
    const options = [randomEx.feminine, ...distractors.sort(() => Math.random() - 0.5).slice(0, 3)].sort(() => Math.random() - 0.5);
    setQuizQuestion({ ...randomEx, options });
    setQuizMode(true);
  };

  const handleAnswer = (ans: string) => {
    if (ans === quizQuestion.feminine) {
      setScore(s => s + 1);
      setTimeout(generateQuiz, 1000);
    }
  };

  if (loading) return null;

  return (
    <div style={{ padding: '10px', maxWidth: '1000px', margin: '0 auto' }}>
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-4">
          <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
            <ArrowLeft size={22} />
          </button>
          <div>
            <h1 style={{ fontSize: '1.8rem', fontWeight: 900, margin: 0, color: 'var(--text-main)' }}>Strī Pratyaya</h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>Feminine Formation Rules</p>
          </div>
        </div>
        {!quizMode && (
          <button onClick={generateQuiz} className="btn-primary" style={{ padding: '8px 20px', borderRadius: '100px' }}>
            <Zap size={16} /> Practice Quiz
          </button>
        )}
      </div>

      {quizMode && quizQuestion ? (
        <div className="zen-card text-center" style={{ padding: '40px', maxWidth: '600px', margin: '0 auto' }}>
          <p style={{ color: 'var(--text-dim)' }}>Score: {score}</p>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>What is the feminine form of:</h2>
          <div className="devanagari" style={{ fontSize: '3rem', color: 'var(--primary)', marginBottom: '24px' }}>
            {quizQuestion.masculine}
          </div>
          <p style={{ color: 'var(--text-light)', marginBottom: '24px' }}>Meaning: {quizQuestion.meaning}</p>
          <div className="grid grid-cols-2 gap-4">
            {quizQuestion.options.map((opt: string, i: number) => (
              <button
                key={i}
                onClick={() => handleAnswer(opt)}
                style={{ padding: '16px', borderRadius: '12px', border: '2px solid var(--border-soft)', fontSize: '1.5rem', cursor: 'pointer' }}
                className="devanagari bg-[var(--bg-main)] hover:border-[var(--primary)] transition-colors"
              >
                {opt}
              </button>
            ))}
          </div>
          <button onClick={() => setQuizMode(false)} style={{ marginTop: '24px', color: 'var(--text-dim)', background: 'none', border: 'none', cursor: 'pointer' }}>Exit Quiz</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {data.map((rule, idx) => (
            <motion.div key={rule.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: idx * 0.1 }} className="zen-card" style={{ padding: '24px' }}>
              <div className="flex justify-between items-start mb-4">
                <div style={{ width: '50px', height: '50px', borderRadius: '16px', background: 'rgba(var(--primary-rgb), 0.1)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.8rem' }} className="devanagari font-bold">
                  -{rule.suffix}
                </div>
              </div>
              <p style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '16px', minHeight: '40px' }}>{rule.rule}</p>
              <div className="flex flex-col gap-3">
                {rule.examples?.map((ex: any, i: number) => (
                  <div key={i} className="flex justify-between items-center" style={{ padding: '12px', background: 'var(--bg-main)', borderRadius: '12px' }}>
                    <div className="flex items-center gap-4 devanagari" style={{ fontSize: '1.3rem' }}>
                      <span style={{ color: 'var(--text-dim)' }}>{ex.masculine}</span>
                      <span style={{ color: 'var(--border-soft)' }}>→</span>
                      <span style={{ color: 'var(--primary)', fontWeight: 700 }}>{ex.feminine}</span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-light)' }}>{ex.meaning}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
