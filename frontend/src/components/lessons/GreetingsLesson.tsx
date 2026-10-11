import React, { useState, useEffect, useMemo } from 'react';
import { 
    ArrowLeft, 
    Sparkles, 
    Filter,
    Flame
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import AudioPronounceButton from '@/components/AudioPronounceButton';

interface Greeting {
    id: string;
    sanskrit: string;
    transliteration: string;
    english: string;
    context: string;
}

const colorThemes = [
    { from: '#FF5F6D', to: '#FFC371', glow: 'rgba(255, 95, 109, 0.2)' },
    { from: '#2193b0', to: '#6dd5ed', glow: 'rgba(33, 147, 176, 0.2)' },
    { from: '#ee9ca7', to: '#ffdde1', glow: 'rgba(238, 156, 167, 0.2)' },
    { from: '#06beb6', to: '#48b1bf', glow: 'rgba(6, 190, 182, 0.2)' },
    { from: '#614385', to: '#516395', glow: 'rgba(97, 67, 133, 0.2)' },
    { from: '#e65c00', to: '#F9D423', glow: 'rgba(230, 92, 0, 0.2)' },
    { from: '#43cea2', to: '#185a9d', glow: 'rgba(67, 206, 162, 0.2)' },
    { from: '#ff00cc', to: '#3333ff', glow: 'rgba(255, 0, 204, 0.2)' }
];

export default function GreetingsLesson({ onBack }: { onBack: () => void }) {
    const [phrases, setPhrases] = useState<Greeting[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeCategory, setActiveCategory] = useState("All");

    useEffect(() => {
        const fetchGreetings = async () => {
            try {
                const result = await api.lessons.getGreetings();
                if (result.success) {
                    setPhrases(result.data);
                }
            } catch (error) {
                console.error("Failed to fetch greetings", error);
            } finally {
                setLoading(false);
            }
        };
        fetchGreetings();
    }, []);

    const categories = ["All", "Greetings", "Common", "Questions", "Polarity"];

    const filteredPhrases = useMemo(() => {
        return phrases.filter(p => {
            if (activeCategory === "All") return true;
            if (activeCategory === "Greetings") return (p.english.includes("Hello") || p.english.includes("Morning") || p.english.includes("Night") || p.english.includes("Welcome"));
            if (activeCategory === "Questions") return p.english.includes("?");
            if (activeCategory === "Polarity") return (p.english === "Yes" || p.english === "No");
            if (activeCategory === "Common") return !p.english.includes("?") && !p.english.includes("Hello") && !p.english.includes("Morning") && p.english !== "Yes" && p.english !== "No";
            return true;
        });
    }, [phrases, activeCategory]);

    if (loading) return (
        <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
            <motion.div 
                animate={{ scale: [1, 1.1, 1], opacity: [0.5, 1, 0.5] }} 
                transition={{ repeat: Infinity, duration: 2 }}
            >
                <Flame size={64} style={{ color: 'var(--primary)' }} />
            </motion.div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 600, letterSpacing: '1px' }}>Enlightening Content...</h3>
        </div>
    );

    return (
        <div style={{ padding: '40px 20px', maxWidth: '1400px', margin: '0 auto', minHeight: '100vh' }}>
            {/* Zen Header Section */}
            <motion.div 
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="zen-card" 
                style={{ 
                    padding: '60px', 
                    marginBottom: '50px', 
                    borderRadius: '40px',
                    background: 'rgba(255,255,255,0.02)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid var(--border-soft)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    textAlign: 'center',
                    position: 'relative',
                    overflow: 'hidden'
                }}
            >
                <div style={{ position: 'absolute', top: '-100px', left: '-100px', width: '300px', height: '300px', background: 'var(--primary)', opacity: 0.03, borderRadius: '50%', filter: 'blur(80px)' }}></div>
                <div style={{ position: 'absolute', bottom: '-100px', right: '-100px', width: '300px', height: '300px', background: '#3333ff', opacity: 0.03, borderRadius: '50%', filter: 'blur(80px)' }}></div>

                <motion.button 
                    whileHover={{ scale: 1.1, x: -5 }}
                    onClick={onBack} 
                    style={{ position: 'absolute', left: '40px', top: '40px', background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
                >
                    <ArrowLeft size={32} />
                </motion.button>

                <span style={{ color: 'var(--primary)', fontSize: '0.9rem', fontWeight: 800, letterSpacing: '4px', textTransform: 'uppercase', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Sparkles size={20} /> Digital Manuscript
                </span>
                <h1 style={{ fontSize: '4rem', fontWeight: 900, marginBottom: '12px', letterSpacing: '-1px' }}>Essential Phrases</h1>
                <p style={{ color: 'var(--text-dim)', fontSize: '1.25rem', maxWidth: '600px', lineHeight: '1.6', fontWeight: 500 }}>
                    Unlock the melody of ancient communication with modern interactive study.
                </p>

                <div className="flex gap-3 mt-12" style={{ flexWrap: 'wrap', justifyContent: 'center' }}>
                    {categories.map(cat => (
                        <motion.button
                            key={cat}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => setActiveCategory(cat)}
                            style={{
                                padding: '12px 32px',
                                borderRadius: '100px',
                                fontSize: '0.9rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                transition: 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
                                borderWidth: '2px',
                                borderStyle: 'solid',
                                borderColor: activeCategory === cat ? 'var(--primary)' : 'rgba(255,255,255,0.1)',
                                background: activeCategory === cat ? 'var(--primary)' : 'transparent',
                                color: activeCategory === cat ? '#fff' : 'var(--text-dim)',
                                boxShadow: activeCategory === cat ? '0 10px 25px rgba(var(--primary-rgb), 0.3)' : 'none'
                            }}
                        >
                            {cat}
                        </motion.button>
                    ))}
                </div>
            </motion.div>

            {/* Grid of Minimal Excellence */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '30px' }}>
                <AnimatePresence mode="popLayout">
                    {filteredPhrases.map((phrase, index) => {
                        const theme = colorThemes[index % colorThemes.length];
                        
                        return (
                            <motion.div
                                layout
                                key={phrase.id}
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.8 }}
                                transition={{ delay: index * 0.03, type: 'spring', stiffness: 200, damping: 20 }}
                                className="zen-card"
                                style={{ 
                                    padding: 0, 
                                    display: 'flex', 
                                    flexDirection: 'column', 
                                    overflow: 'hidden',
                                    border: '1px solid rgba(255,255,255,0.05)',
                                    background: 'var(--bg-card)',
                                    boxShadow: `0 20px 40px -20px ${theme.glow}`
                                }}
                            >
                                {/* Header Color Strip */}
                                <div style={{ 
                                    height: '40px',
                                    background: `linear-gradient(135deg, ${theme.from} 0%, ${theme.to} 100%)`,
                                }}>
                                </div>

                                {/* Body Content */}
                                <div style={{ padding: '40px 30px', textAlign: 'center', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                                    <div className="flex items-center justify-center gap-2" style={{ marginBottom: '20px' }}>
                                        <motion.div 
                                            style={{ 
                                                fontSize: '4rem', 
                                                fontWeight: 800,
                                                color: 'var(--text-main)',
                                                textShadow: '0 4px 10px rgba(0,0,0,0.1)'
                                            }}
                                            className="devanagari"
                                        >
                                            {phrase.sanskrit}
                                        </motion.div>
                                        <AudioPronounceButton text={phrase.sanskrit} size={20} />
                                    </div>
                                    
                                    <div style={{ marginBottom: '4px', fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)' }}>
                                        {phrase.english}
                                    </div>
                                    <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '2px', opacity: 0.8 }}>
                                        {phrase.transliteration}
                                    </div>
                                </div>

                                {/* Minimalist Context Footer */}
                                <div style={{ padding: '30px', borderTop: '1px solid var(--border-soft)', background: 'rgba(255,255,255,0.01)' }}>
                                    <div style={{ 
                                        background: 'rgba(255,255,255,0.02)', 
                                        padding: '16px 20px', 
                                        borderRadius: '20px', 
                                        fontSize: '0.95rem', 
                                        color: 'var(--text-dim)', 
                                        textAlign: 'center',
                                        lineHeight: '1.5',
                                        border: '1px dashed var(--border-soft)'
                                    }}>
                                        {phrase.context}
                                    </div>
                                </div>
                            </motion.div>
                        );
                    })}
                </AnimatePresence>
            </div>

            {filteredPhrases.length === 0 && (
                <div style={{ textAlign: 'center', padding: '100px 20px', background: 'rgba(255,255,255,0.01)', borderRadius: '40px', border: '2px dashed var(--border-soft)', marginTop: '40px' }}>
                    <h3 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-dim)' }}>No phrases found in this category</h3>
                    <motion.button 
                        whileHover={{ scale: 1.05 }}
                        onClick={() => setActiveCategory("All")}
                        style={{ marginTop: '20px', color: 'var(--primary)', fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
                    >
                        Reset Filters
                    </motion.button>
                </div>
            )}
        </div>
    );
}
