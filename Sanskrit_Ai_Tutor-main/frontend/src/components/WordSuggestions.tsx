// frontend/src/components/WordSuggestions.tsx
"use client";
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiRequest } from '@/lib/api';

interface Suggestion {
  word: string;
  meaning: string;
  sanskrit: string;
}

interface WordSuggestionsProps {
  prefix: string;
  onSelect: (word: string) => void;
  enabled: boolean;
}

export default function WordSuggestions({ prefix, onSelect, enabled }: WordSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!enabled || !prefix || prefix.length < 1) {
      setSuggestions([]);
      setSelectedIndex(-1);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await apiRequest(
          `/suggestions?prefix=${encodeURIComponent(prefix)}&limit=6`
        );
        setSuggestions(data.suggestions || []);
        setSelectedIndex(-1);
      } catch (err) {
        console.error("Suggestion error:", err);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [prefix, enabled]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!enabled || suggestions.length === 0) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % suggestions.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + suggestions.length) % suggestions.length);
      } else if (e.key === 'Enter' && selectedIndex >= 0) {
        e.preventDefault();
        onSelect(suggestions[selectedIndex].word);
        setSuggestions([]);
      } else if (e.key === 'Escape') {
        setSuggestions([]);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, suggestions, selectedIndex, onSelect]);

  if (!enabled || suggestions.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="suggestions-dropdown"
        style={{
          position: 'absolute',
          bottom: '100%',
          left: '40px',
          right: '40px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-soft)',
          borderRadius: '16px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
          zIndex: 100,
          marginBottom: '8px',
          overflow: 'hidden'
        }}
      >
        {loading && (
          <div style={{ padding: '12px 20px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            Loading suggestions...
          </div>
        )}
        {!loading && suggestions.map((sug, idx) => (
          <motion.div
            key={sug.word}
            whileHover={{ background: 'rgba(var(--primary-rgb), 0.05)' }}
            onClick={() => onSelect(sug.word)}
            style={{
              padding: '12px 20px',
              cursor: 'pointer',
              borderBottom: idx < suggestions.length - 1 ? '1px solid var(--border-soft)' : 'none',
              background: selectedIndex === idx ? 'rgba(var(--primary-rgb), 0.08)' : 'transparent',
              transition: 'all 0.1s'
            }}
          >
            <div className="devanagari" style={{ fontSize: '1.2rem', fontWeight: '600', color: 'var(--primary)' }}>
              {sug.word}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
              {sug.meaning}
            </div>
          </motion.div>
        ))}
        <div style={{ padding: '6px 12px', fontSize: '0.7rem', color: 'var(--text-light)', background: 'var(--bg-main)', textAlign: 'center', borderTop: '1px solid var(--border-soft)' }}>
          ↑ ↓ Enter to navigate • Esc to close
        </div>
      </motion.div>
    </AnimatePresence>
  );
}