'use client';
import React, { useState, useEffect } from 'react';
import { ArrowLeft, BookOpen, Clock } from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';

export default function Participles2Lesson({ onBack }: { onBack: () => void }) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.lessons.getParticiples2();
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
    return <div className="flex justify-center p-20"><Clock size={40} className="animate-spin text-[var(--primary)]" /></div>;
  }

  return (
    <div style={{ padding: '10px', maxWidth: '1000px', margin: '0 auto' }}>
      <div className="flex items-center gap-4 mb-8">
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
          <ArrowLeft size={22} />
        </button>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 900, margin: 0, color: 'var(--text-main)' }}>Participles – Part 2</h1>
          <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>Advanced Participle Forms</p>
        </div>
      </div>

      <div className="flex flex-col gap-8">
        {data.map((section, idx) => (
          <motion.div key={section.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.1 }} className="zen-card" style={{ padding: '32px' }}>
            <div className="flex items-center gap-3 mb-6">
              <BookOpen size={24} color="var(--primary)" />
              <div>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>{section.category}</h2>
                <p style={{ color: 'var(--text-dim)' }}>{section.description}</p>
              </div>
            </div>
            
            {section.formation && (
              <div style={{ marginBottom: '24px', padding: '16px', background: 'var(--bg-main)', borderRadius: '12px' }}>
                <strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '4px' }}>Formation Rule:</strong>
                {section.formation}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {section.examples?.map((ex: any, i: number) => (
                <div key={i} style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)' }}>
                  {ex.root && <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)', marginBottom: '8px' }}>Root: <strong className="devanagari text-lg">{ex.root}</strong></div>}
                  {ex.participle && <div className="devanagari" style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '4px' }}>{ex.participle}</div>}
                  {ex.meaning && <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '12px' }}>{ex.meaning}</div>}
                  
                  {ex.sanskrit && <div className="devanagari" style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--primary)', marginBottom: '4px' }}>{ex.sanskrit}</div>}
                  {ex.breakdown && <div style={{ fontSize: '0.8rem', color: 'var(--text-light)', marginBottom: '8px', fontStyle: 'italic' }}>{ex.breakdown}</div>}
                  
                  {ex.sentence && (
                    <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px dashed var(--border-soft)' }}>
                      <div className="devanagari" style={{ fontSize: '1.1rem' }}>{ex.sentence}</div>
                    </div>
                  )}
                  {ex.translation && <div style={{ fontSize: '0.85rem', color: 'var(--text-light)', marginTop: '4px' }}>{ex.translation}</div>}
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
