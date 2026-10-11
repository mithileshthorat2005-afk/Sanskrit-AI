import React, { useState, useEffect } from 'react';
import { 
    ArrowLeft, 
    Sparkles, 
    Flame,
    Calculator
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import AudioPronounceButton from '@/components/AudioPronounceButton';

interface NumberItem {
    id: string;
    number: number;
    sanskrit: string;
    transliteration: string;
}

const colorThemes = [
    { from: '#f85032', to: '#e73827', glow: 'rgba(248, 80, 50, 0.5)' },
    { from: '#00c6ff', to: '#0072ff', glow: 'rgba(0, 198, 255, 0.5)' },
    { from: '#f7971e', to: '#ffd200', glow: 'rgba(247, 151, 30, 0.5)' },
    { from: '#9d50bb', to: '#6e48aa', glow: 'rgba(157, 80, 187, 0.5)' },
    { from: '#11998e', to: '#38ef7d', glow: 'rgba(17, 153, 142, 0.5)' },
    { from: '#8e2de2', to: '#4a00e0', glow: 'rgba(142, 45, 226, 0.5)' },
    { from: '#eb3349', to: '#f45c43', glow: 'rgba(235, 51, 73, 0.5)' },
    { from: '#4568dc', to: '#b06ab3', glow: 'rgba(69, 104, 220, 0.5)' },
    { from: '#ff512f', to: '#dd2476', glow: 'rgba(255, 81, 47, 0.5)' },
    { from: '#1d976c', to: '#93f9b9', glow: 'rgba(29, 151, 108, 0.5)' }
];

export default function NumbersLesson({ onBack }: { onBack: () => void }) {
    const [numbers, setNumbers] = useState<NumberItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeId, setActiveId] = useState<string | null>(null);

    useEffect(() => {
        const fetchNumbers = async () => {
            try {
                const result = await api.lessons.getNumbers();
                if (result.success) {
                    setNumbers(result.data);
                }
            } catch (error) {
                console.error("Failed to fetch numbers", error);
            } finally {
                setLoading(false);
            }
        };
        fetchNumbers();
    }, []);

    const handleCardClick = (id: string) => {
        setActiveId(activeId === id ? null : id);
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
            <motion.div 
                animate={{ scale: [1, 1.1, 1], opacity: [0.5, 1, 0.5] }} 
                transition={{ repeat: Infinity, duration: 2 }}
            >
                <Flame size={64} style={{ color: 'var(--primary)' }} />
            </motion.div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 600, letterSpacing: '1px', color: 'var(--text-main)' }}>Summoning Numbers...</h3>
        </div>
    );

    return (
        <div style={{ padding: '40px 20px', maxWidth: '1200px', margin: '0 auto', minHeight: '100vh' }}>
            {/* Zen Header Section */}
            <motion.div 
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                className="zen-card" 
                style={{ 
                    padding: '50px 40px', 
                    marginBottom: '50px', 
                    borderRadius: '40px',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-soft)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    textAlign: 'center',
                    position: 'relative',
                    overflow: 'hidden',
                    boxShadow: '0 20px 40px rgba(0,0,0,0.03)'
                }}
            >
                <div style={{ position: 'absolute', top: '-100px', left: '-100px', width: '300px', height: '300px', background: 'var(--primary)', opacity: 0.05, borderRadius: '50%', filter: 'blur(80px)' }}></div>
                <div style={{ position: 'absolute', bottom: '-100px', right: '-100px', width: '300px', height: '300px', background: '#38ef7d', opacity: 0.05, borderRadius: '50%', filter: 'blur(80px)' }}></div>

                <motion.button 
                    whileHover={{ scale: 1.1, x: -5 }}
                    onClick={onBack} 
                    style={{ position: 'absolute', left: '40px', top: '40px', background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
                >
                    <ArrowLeft size={32} />
                </motion.button>

                <div style={{ color: 'var(--primary)', fontSize: '0.85rem', fontWeight: 800, letterSpacing: '4px', textTransform: 'uppercase', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Calculator size={18} /> Foundations
                </div>
                <h1 style={{ fontSize: '3.5rem', fontWeight: 900, marginBottom: '12px', letterSpacing: '-1px', color: 'var(--text-main)' }}>The Divine Count</h1>
                <p style={{ color: 'var(--text-dim)', fontSize: '1.15rem', maxWidth: '600px', lineHeight: '1.6', fontWeight: 500 }}>
                    Tap each cardinal block to reveal its sacred Devanagari form and visual quantity representation.
                </p>
            </motion.div>

            {/* Tap-to-Reveal Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '20px' }}>
                <AnimatePresence mode="popLayout">
                    {numbers.map((item, index) => {
                        const theme = colorThemes[index % colorThemes.length];
                        const isActive = activeId === item.id;
                        
                        return (
                            <motion.div
                                layout
                                key={item.id}
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                whileHover={isActive ? {} : { scale: 1.05, y: -5 }}
                                transition={{ type: 'spring', stiffness: 200, damping: 20 }}
                                onClick={() => handleCardClick(item.id)}
                                className="zen-card cursor-pointer"
                                style={{ 
                                    padding: isActive ? '30px' : '40px', 
                                    display: 'flex', 
                                    flexDirection: 'column', 
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    border: `1px solid ${isActive ? 'transparent' : 'var(--border-soft)'}`,
                                    borderRadius: '24px',
                                    background: isActive ? `linear-gradient(135deg, ${theme.from} 0%, ${theme.to} 100%)` : 'var(--bg-card)',
                                    boxShadow: isActive ? `0 20px 40px -10px ${theme.glow}` : '0 8px 20px rgba(0,0,0,0.03)',
                                    color: isActive ? '#fff' : 'var(--text-main)',
                                    minHeight: '220px',
                                    position: 'relative',
                                    overflow: 'hidden',
                                    transition: 'background 0.4s ease, box-shadow 0.4s ease'
                                }}
                            >
                                {isActive ? (
                                    <motion.div 
                                        initial={{ opacity: 0, scale: 0.8 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        style={{ textAlign: 'center', width: '100%', zIndex: 2 }}
                                    >
                                        <div style={{ fontSize: '1rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '4px', color: 'rgba(255,255,255,0.9)', marginBottom: '16px' }}>
                                            Number {item.number}
                                        </div>
                                        <div className="flex items-center justify-center gap-3 mb-2">
                                            <div className="devanagari" style={{ fontSize: item.sanskrit.length > 8 ? '2.8rem' : '3.8rem', fontWeight: 900, textShadow: '0 8px 16px rgba(0,0,0,0.25)', color: '#fff' }}>
                                                {item.sanskrit}
                                            </div>
                                            <div onClick={(e) => e.stopPropagation()}>
                                                <AudioPronounceButton text={item.sanskrit} size={24} className="bg-white/20 text-white hover:bg-white/30" title={`Pronounce: ${item.sanskrit}`} />
                                            </div>
                                        </div>
                                        <div style={{ fontSize: '1.2rem', fontWeight: 800, letterSpacing: '1px', textTransform: 'uppercase', color: '#fff', textShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
                                            {item.transliteration}
                                        </div>
                                        
                                        {/* Visual Dots for Quantity - Max 10 dots to save space */}
                                        <div className="flex flex-wrap justify-center gap-2 mt-6" style={{ maxWidth: '400px', margin: '1.5rem auto 0 auto' }}>
                                            {Array.from({ length: Math.min(item.number, 10) }).map((_, i) => (
                                                <motion.div
                                                    key={i}
                                                    initial={{ opacity: 0, scale: 0 }}
                                                    animate={{ opacity: 1, scale: 1 }}
                                                    transition={{ delay: 0.1 + (i * 0.05) }}
                                                    style={{
                                                        width: '12px',
                                                        height: '12px',
                                                        borderRadius: '50%',
                                                        background: '#fff',
                                                        boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                                                    }}
                                                />
                                            ))}
                                            {item.number > 10 && (
                                                <motion.div
                                                    initial={{ opacity: 0 }}
                                                    animate={{ opacity: 1 }}
                                                    style={{ 
                                                        background: 'rgba(255,255,255,0.2)', 
                                                        padding: '4px 10px', 
                                                        borderRadius: '8px', 
                                                        fontSize: '0.8rem', 
                                                        fontWeight: 900,
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        marginLeft: '4px'
                                                    }}
                                                >
                                                    + { (item.number - 10).toLocaleString() } more
                                                </motion.div>
                                            )}
                                        </div>
                                    </motion.div>
                                ) : (
                                    <motion.div 
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}
                                    >
                                        <div style={{ 
                                            fontSize: item.number >= 1000 ? '3rem' : '5rem', 
                                            fontWeight: 950, 
                                            background: `linear-gradient(135deg, ${theme.from} 0%, ${theme.to} 100%)`, 
                                            WebkitBackgroundClip: 'text', 
                                            WebkitTextFillColor: 'transparent',
                                            lineHeight: 1,
                                            filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.05))',
                                            transition: 'all 0.3s ease'
                                        }}>
                                            {item.number.toLocaleString()}
                                        </div>
                                        <div className="mt-2 flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                                            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">{item.sanskrit}</span>
                                            <AudioPronounceButton text={item.sanskrit} size={14} title={`Pronounce: ${item.sanskrit}`} />
                                        </div>
                                    </motion.div>
                                )}
                                
                                {/* Background Watermark */}
                                {isActive && (
                                    <div style={{ 
                                        position: 'absolute', 
                                        right: '-10px', 
                                        bottom: '-20px', 
                                        fontSize: item.number >= 1000 ? '5rem' : '8rem', 
                                        fontWeight: 900, 
                                        color: '#fff', 
                                        opacity: 0.12, 
                                        zIndex: 1, 
                                        pointerEvents: 'none' 
                                    }}>
                                        {item.number.toLocaleString()}
                                    </div>
                                )}
                            </motion.div>
                        );
                    })}
                </AnimatePresence>
            </div>
        </div>
    );
}
