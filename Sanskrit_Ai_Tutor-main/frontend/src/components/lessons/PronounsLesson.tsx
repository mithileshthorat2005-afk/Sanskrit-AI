import React, { useState, useEffect } from 'react';
import { 
    ArrowLeft, 
    User,
    UserPlus,
    Users,
    Navigation,
    BookOpen,
    Eye,
    MessageCircle,
    CheckCircle2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface PronounItem {
    id: string;
    sanskrit: string;
    transliteration: string;
    englishMeaning: string;
    category: string;
    example: string;
}

export default function PronounsLesson({ onBack }: { onBack: () => void }) {
    const [pronouns, setPronouns] = useState<PronounItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeId, setActiveId] = useState<string | null>(null);

    useEffect(() => {
        const fetchPronouns = async () => {
            try {
                const res = await api.lessons.getPronouns();
                if (res.success) {
                    setPronouns(res.data);
                }
            } catch (error) {
                console.error("Failed to fetch pronouns data", error);
            } finally {
                setLoading(false);
            }
        };
        fetchPronouns();
    }, []);

    const getIconForCategory = (category: string) => {
        const iconSize = 24;
        if (category.toLowerCase().includes('first person')) return <User size={iconSize} />;
        if (category.toLowerCase().includes('second person')) return <UserPlus size={iconSize} />;
        if (category.toLowerCase().includes('third person')) return <Users size={iconSize} />;
        if (category.toLowerCase().includes('demonstrative')) return <Navigation size={iconSize} />;
        return <User size={iconSize} />;
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: "linear" }}>
                <Eye size={48} style={{ color: 'var(--primary)' }} />
            </motion.div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-main)' }}>Loading Context Map...</h3>
        </div>
    );

    const activeItem = pronouns.find(p => p.id === activeId);

    return (
        <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto', minHeight: '80vh' }}>
            {/* Header */}
            <motion.div 
                initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
                className="zen-card" 
                style={{ 
                    padding: '24px', marginBottom: '32px', borderRadius: '24px',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
                    border: '1px solid var(--border-soft)', position: 'relative',
                    background: 'rgba(var(--bg-card-rgb), 0.8)',
                    backdropFilter: 'blur(10px)'
                }}
            >
                <motion.button onClick={onBack} style={{ position: 'absolute', left: '24px', top: '24px', background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
                    <ArrowLeft size={24} />
                </motion.button>
                <h1 style={{ fontSize: '2rem', fontWeight: 900, marginBottom: '4px', color: 'var(--text-main)' }}>The Pronoun Map</h1>
                <p style={{ color: 'var(--text-dim)', fontSize: '0.95rem' }}>Tap a node to reveal its grammatical frequency.</p>
            </motion.div>

            <div className="flex flex-col lg:flex-row gap-6 items-start">
                
                {/* Visual Map Side (Interactive Grid) */}
                <div className="flex-1 w-full relative" style={{ background: 'var(--bg-card)', padding: '24px', borderRadius: '24px', border: '1px solid var(--border-soft)', minHeight: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '16px', width: '100%' }}>
                        {pronouns.map((item) => {
                            const isActive = activeId === item.id;
                            
                            let themeColor = 'var(--primary)';
                            if (item.category.includes('First')) themeColor = 'hsl(350, 80%, 65%)'; 
                            else if (item.category.includes('Second')) themeColor = 'hsl(210, 80%, 65%)'; 
                            else if (item.category.includes('Third')) themeColor = 'hsl(45, 90%, 55%)'; 
                            else if (item.category.includes('Demonstrative')) themeColor = 'hsl(145, 60%, 50%)'; 
                            
                            return (
                                <motion.div
                                    layoutId={`node-${item.id}`}
                                    key={item.id}
                                    whileHover={isActive ? {} : { scale: 1.05, y: -4 }}
                                    whileTap={{ scale: 0.95 }}
                                    onClick={() => setActiveId(item.id)}
                                    style={{
                                        background: isActive ? themeColor : 'rgba(var(--bg-main-rgb), 0.3)',
                                        border: `1.5px solid ${isActive ? themeColor : 'var(--border-soft)'}`,
                                        borderRadius: '20px',
                                        padding: '16px 12px',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        cursor: 'pointer',
                                        boxShadow: isActive ? `0 12px 24px -8px ${themeColor}66` : 'none',
                                        color: isActive ? 'white' : 'var(--text-main)',
                                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                        position: 'relative',
                                        overflow: 'hidden'
                                    }}
                                >
                                    <div style={{ opacity: isActive ? 1 : 0.4, marginBottom: '12px', transform: isActive ? 'scale(1.1)' : 'scale(1)', transition: 'all 0.3s ease' }}>
                                        {getIconForCategory(item.category)}
                                    </div>
                                    <div className="devanagari" style={{ fontSize: '2rem', fontWeight: 900, marginBottom: '2px' }}>
                                        {item.sanskrit}
                                    </div>
                                    {isActive && (
                                        <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px', opacity: 0.9 }}>
                                            {item.transliteration}
                                        </motion.div>
                                    )}
                                </motion.div>
                            )
                        })}
                    </div>
                </div>

                {/* Details Panel Side */}
                <div className="lg:w-80 xl:w-96 w-full sticky top-6">
                    <AnimatePresence mode="wait">
                        {activeItem ? (
                            <motion.div
                                key={activeItem.id}
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95, position: 'absolute' }}
                                className="zen-card"
                                style={{
                                    padding: '24px',
                                    borderRadius: '24px',
                                    background: 'var(--bg-card)',
                                    border: '1px solid var(--border-soft)',
                                    boxShadow: '0 20px 40px rgba(0,0,0,0.08)'
                                }}
                            >
                                <div style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--primary)', letterSpacing: '2px', textTransform: 'uppercase', marginBottom: '6px' }}>
                                    {activeItem.category}
                                </div>
                                <h2 className="devanagari" style={{ fontSize: '3rem', fontWeight: 900, color: 'var(--text-main)', marginBottom: '4px', lineHeight: 1 }}>
                                    {activeItem.sanskrit}
                                </h2>
                                <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-light)', fontStyle: 'italic', marginBottom: '20px' }}>
                                    "{activeItem.transliteration}"
                                </div>
                                
                                <div style={{ height: '2px', background: 'var(--border-soft)', width: '30px', marginBottom: '20px' }} />

                                <div style={{ marginBottom: '24px' }}>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 800, marginBottom: '4px', letterSpacing: '1px' }}>Universal Meaning</div>
                                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)' }}>
                                        {activeItem.englishMeaning}
                                    </div>
                                </div>

                                <div style={{ background: 'rgba(var(--primary-rgb), 0.04)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(var(--primary-rgb), 0.1)' }}>
                                    <div className="flex gap-2 items-center" style={{ fontSize: '0.75rem', color: 'var(--primary)', textTransform: 'uppercase', fontWeight: 800, marginBottom: '10px', letterSpacing: '1px' }}>
                                        <MessageCircle size={16} /> Linguistic Context
                                    </div>
                                    <div className="devanagari" style={{ fontSize: '1.2rem', color: 'var(--text-main)', lineHeight: '1.4', marginBottom: '6px' }}>
                                        {activeItem.example.split(' (')[0]}
                                    </div>
                                    <div style={{ fontSize: '0.95rem', color: 'var(--text-dim)', fontWeight: 500 }}>
                                        {activeItem.example.split(' (')[1] ? `(${activeItem.example.split(' (')[1]}` : ''}
                                    </div>
                                </div>
                            </motion.div>
                        ) : (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                style={{
                                    height: '100%',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-dim)',
                                    padding: '48px 32px',
                                    textAlign: 'center',
                                    border: '2px dashed var(--border-soft)',
                                    borderRadius: '24px',
                                    background: 'rgba(var(--bg-card-rgb), 0.3)'
                                }}
                            >
                                <Navigation size={40} style={{ opacity: 0.15, marginBottom: '16px' }} />
                                <p style={{ fontSize: '1rem', fontWeight: 600, lineHeight: 1.5 }}>Select a node to inspect its Sanskrit essence.</p>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
            
            {(activeId && pronouns.length > 0 && activeId === pronouns[pronouns.length - 1]?.id) && (
                <motion.div 
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-center mt-10"
                >
                    <button onClick={onBack} className="btn-primary" style={{ padding: '16px 32px', fontSize: '1.1rem', borderRadius: '100px' }}>
                        Finish Lesson <CheckCircle2 size={20} className="ml-2" />
                    </button>
                </motion.div>
            )}
        </div>
    );
}
