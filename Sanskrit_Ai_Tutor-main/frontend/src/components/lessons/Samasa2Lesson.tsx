'use client';
import React, { useState, useEffect } from 'react';
import { ArrowLeft, GitMerge, BookOpen } from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';

export default function Samasa2Lesson({ onBack }: { onBack: () => void }) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.lessons.getSamasa2();
        setData(res?.success ? res.data : (Array.isArray(res) ? res : []));
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}>
          <GitMerge size={48} style={{ color: 'var(--primary)' }} />
        </motion.div>
      </div>
    );
  }

  return (
    <div style={{ padding: '10px', maxWidth: '1000px', margin: '0 auto' }}>
      <div className="flex items-center gap-4 mb-8">
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
          <ArrowLeft size={22} />
        </button>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 900, margin: 0, color: 'var(--text-main)' }}>Samāsa – Compounds (Part 2)</h1>
          <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>Advanced Compound Analysis & Expansion</p>
        </div>
      </div>

      <div className="flex flex-col gap-8">
        {data.map((section, idx) => (
          <motion.div key={section.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.1 }} className="zen-card" style={{ padding: '32px' }}>
            <div className="flex items-center gap-3 mb-6">
              <BookOpen size={24} color="var(--primary)" />
              <div>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>{section.type}</h2>
                <p style={{ color: 'var(--text-dim)' }}>{section.description}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {section.examples?.map((ex: any, i: number) => (
                <div key={i} style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)' }}>
                  <div className="devanagari" style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '8px' }}>
                    {ex.compound}
                  </div>
                  {ex.type && <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '4px' }}>Type: {ex.type}</div>}
                  {ex.components && <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>Components: {ex.components}</div>}
                  {ex.expansion && <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>Expansion: {ex.expansion}</div>}
                  {ex.meaning && <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>Meaning: {ex.meaning}</div>}
                  {ex.explanation && <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>Explanation: {ex.explanation}</div>}
                  {ex.sentence && (
                    <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px dashed var(--border-soft)' }}>
                      <div className="devanagari" style={{ fontSize: '1.1rem' }}>{ex.sentence}</div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>{ex.translation}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
