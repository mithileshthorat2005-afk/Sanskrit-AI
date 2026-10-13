'use client';
import React, { useState, useEffect } from 'react';
import { ArrowLeft, BookOpen, Music } from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';

export default function ChandasLesson({ onBack }: { onBack: () => void }) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.lessons.getChandas();
        setData(res?.success ? res.data : (Array.isArray(res) ? res : []));
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return null;

  return (
    <div style={{ padding: '10px', maxWidth: '1000px', margin: '0 auto' }}>
      <div className="flex items-center gap-4 mb-8">
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
          <ArrowLeft size={22} />
        </button>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 900, margin: 0, color: 'var(--text-main)' }}>Introduction to Prosody</h1>
          <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>Sanskrit Metres (Chandas)</p>
        </div>
      </div>

      <div className="flex flex-col gap-8">
        {data.map((section, idx) => (
          <motion.div key={section.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.1 }} className="zen-card" style={{ padding: '32px' }}>
            <div className="flex items-center gap-3 mb-6">
              {idx === 0 ? <BookOpen size={24} color="var(--primary)" /> : <Music size={24} color="var(--primary)" />}
              <div>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>{section.topic}</h2>
                {section.description && <p style={{ color: 'var(--text-dim)' }}>{section.description}</p>}
              </div>
            </div>

            {section.terms && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {section.terms.map((t: any, i: number) => (
                  <div key={i} style={{ padding: '20px', background: 'var(--bg-main)', borderRadius: '16px', textAlign: 'center', border: '1px solid var(--border-soft)' }}>
                    <div className="devanagari" style={{ fontSize: '2rem', color: 'var(--primary)', fontWeight: 700, marginBottom: '8px' }}>{t.term}</div>
                    <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>{t.meaning}</div>
                  </div>
                ))}
              </div>
            )}

            {section.examples && (
              <div className="grid grid-cols-1 gap-6">
                {section.examples.map((ex: any, i: number) => (
                  <div key={i} style={{ padding: '24px', background: 'var(--bg-main)', borderRadius: '16px', border: '1px solid var(--border-soft)', borderLeft: '4px solid var(--primary)' }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="devanagari" style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0 }}>{ex.name}</h3>
                    </div>
                    <p style={{ color: 'var(--text-dim)', marginBottom: '16px' }}>{ex.description}</p>
                    <div style={{ background: 'rgba(var(--primary-rgb), 0.05)', padding: '16px', borderRadius: '12px' }}>
                      <div className="devanagari" style={{ fontSize: '1.4rem', color: 'var(--text-main)', marginBottom: '8px' }}>{ex.example}</div>
                      <div style={{ fontFamily: 'monospace', letterSpacing: '4px', color: 'var(--primary)', fontWeight: 600 }}>{ex.analysis}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
