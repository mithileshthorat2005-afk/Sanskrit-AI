'use client';
import React, { useState, useEffect } from 'react';
import {
    ArrowLeft,
    CheckCircle2,
    Sparkles,
    RotateCcw,
    Zap,
    HelpCircle,
    Heart
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import AudioPronounceButton from '@/components/AudioPronounceButton';

interface FamilyMember {
    id: string;
    sanskrit: string;
    transliteration: string;
    englishMeaning: string;
    gender: 'masculine' | 'feminine' | 'neuter';
}

// Tree layout positions for each family member keyed by id
const TREE_LAYOUT: Record<string, { x: number; y: number; row: string }> = {
    fam_7:  { x: 15, y: 5,  row: 'grandparents' },    // Paternal Grandfather
    fam_8:  { x: 30, y: 5,  row: 'grandparents' },    // Paternal Grandmother
    fam_9:  { x: 70, y: 5,  row: 'grandparents' },    // Maternal Grandfather
    fam_10: { x: 85, y: 5,  row: 'grandparents' },    // Maternal Grandmother
    fam_11: { x: 8,  y: 35, row: 'parents' },         // Uncle (Father's)
    fam_2:  { x: 22.5, y: 35, row: 'parents' },       // Father
    fam_1:  { x: 45, y: 35, row: 'parents' },         // Mother
    fam_12: { x: 67.5, y: 35, row: 'parents' },       // Uncle (Mother's)
    fam_13: { x: 78, y: 35, row: 'parents' },         // Husband
    fam_14: { x: 92, y: 35, row: 'parents' },         // Wife
    fam_3:  { x: 20, y: 65, row: 'siblings' },        // Brother
    fam_4:  { x: 75, y: 65, row: 'siblings' },        // Sister
    fam_15: { x: 90, y: 65, row: 'siblings' },        // Friend (moved to side)
    fam_5:  { x: 35, y: 90, row: 'children' },        // Son
    fam_6:  { x: 65, y: 90, row: 'children' },        // Daughter
};

const GENDER_COLORS: Record<string, { bg: string; border: string; text: string }> = {
    masculine: { bg: 'rgba(68, 138, 255, 0.08)', border: '#448AFF', text: '#448AFF' },
    feminine:  { bg: 'rgba(255, 82, 130, 0.08)', border: '#FF5282', text: '#FF5282' },
    neuter:    { bg: 'rgba(76, 175, 80, 0.08)',  border: '#4CAF50', text: '#4CAF50' },
};

// SVG connector lines between family nodes
const CONNECTIONS = [
    // Grandparents to Parents
    { from: 'fam_7', to: 'fam_2' },
    { from: 'fam_8', to: 'fam_2' },
    { from: 'fam_9', to: 'fam_1' },
    { from: 'fam_10', to: 'fam_1' },
    // Parents to siblings
    { from: 'fam_2', to: 'fam_3' },
    { from: 'fam_1', to: 'fam_3' },
    { from: 'fam_2', to: 'fam_4' },
    { from: 'fam_1', to: 'fam_4' },
    // Uncle connections
    { from: 'fam_7', to: 'fam_11' },
    { from: 'fam_9', to: 'fam_12' },
    // Children
    { from: 'fam_3', to: 'fam_5' },
    { from: 'fam_4', to: 'fam_6' },
];

export default function FamilyLesson({ onBack }: { onBack: () => void }) {
    const [familyData, setFamilyData] = useState<FamilyMember[]>([]);
    const [loading, setLoading] = useState(true);
    const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set());
    const [quizMode, setQuizMode] = useState(false);
    const [quizTarget, setQuizTarget] = useState<FamilyMember | null>(null);
    const [quizScore, setQuizScore] = useState(0);
    const [quizAttempted, setQuizAttempted] = useState<Set<string>>(new Set());
    const [feedback, setFeedback] = useState<{ id: string; correct: boolean } | null>(null);

    useEffect(() => {
        const fetchFamily = async () => {
            try {
                const res = await api.lessons.getFamily();
                const data = Array.isArray(res) ? res : (res?.data || res || []);
                setFamilyData(data);
            } catch (error) {
                console.error('Failed to fetch family data', error);
            } finally {
                setLoading(false);
            }
        };
        fetchFamily();
    }, []);

    const handleReveal = (id: string) => {
        if (quizMode) return;
        setRevealedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    };

    const startQuizMode = () => {
        setQuizMode(true);
        setQuizScore(0);
        setQuizAttempted(new Set());
        setRevealedIds(new Set());
        pickNextQuizTarget(new Set());
    };

    const pickNextQuizTarget = (attempted: Set<string>) => {
        const remaining = familyData.filter(m => !attempted.has(m.id));
        if (remaining.length === 0) {
            setQuizTarget(null);
            return;
        }
        const random = remaining[Math.floor(Math.random() * remaining.length)];
        setQuizTarget(random);
    };

    const handleQuizClick = (id: string) => {
        if (!quizMode || !quizTarget) return;
        
        if (id === quizTarget.id) {
            setFeedback({ id, correct: true });
            setQuizScore(s => s + 1);
            const newAttempted = new Set(quizAttempted);
            newAttempted.add(id);
            setQuizAttempted(newAttempted);
            setRevealedIds(prev => new Set(prev).add(id));
            setTimeout(() => {
                setFeedback(null);
                pickNextQuizTarget(newAttempted);
            }, 800);
        } else {
            setFeedback({ id, correct: false });
            setTimeout(() => setFeedback(null), 600);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}>
                    <Heart size={48} style={{ color: 'var(--primary)' }} />
                </motion.div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Family Tree...</h3>
            </div>
        );
    }

    const allRevealed = revealedIds.size === familyData.length;
    const quizComplete = quizMode && quizTarget === null && quizAttempted.size > 0;

    return (
        <div style={{ padding: '10px', maxWidth: '1100px', margin: '0 auto' }}>
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
                            कुटुम्बः — Family Tree
                        </h1>
                        <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
                            {quizMode ? 'Tap the correct node to place the word!' : 'Tap any node to reveal its Sanskrit name.'}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    {quizMode && quizTarget && (
                        <motion.div
                            key={quizTarget.id}
                            initial={{ scale: 0.8, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            style={{
                                padding: '10px 20px',
                                background: 'var(--primary)',
                                color: 'white',
                                borderRadius: '16px',
                                fontWeight: 800,
                                fontSize: '1.1rem'
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span className="devanagari" style={{ fontSize: '1.3rem' }}>{quizTarget.sanskrit}</span>
                                <span style={{ opacity: 0.8, fontSize: '0.85rem' }}>({quizTarget.transliteration})</span>
                                <AudioPronounceButton text={quizTarget.sanskrit} size={16} title={`Pronounce: ${quizTarget.sanskrit}`} />
                            </div>
                        </motion.div>
                    )}
                    {quizMode && (
                        <div style={{ fontWeight: 800, color: 'var(--primary)', fontSize: '0.9rem' }}>
                            <Sparkles size={16} /> {quizScore}/{familyData.length}
                        </div>
                    )}
                    <button
                        onClick={quizMode ? () => { setQuizMode(false); setRevealedIds(new Set()); } : startQuizMode}
                        style={{
                            padding: '10px 20px',
                            borderRadius: '100px',
                            border: '2px solid var(--primary)',
                            background: quizMode ? 'var(--primary)' : 'transparent',
                            color: quizMode ? 'white' : 'var(--primary)',
                            fontWeight: 800,
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                        }}
                    >
                        {quizMode ? <><RotateCcw size={14} /> Exit Quiz</> : <><Zap size={14} /> Quiz Mode</>}
                    </button>
                </div>
            </motion.div>

            {/* Quiz Complete */}
            {quizComplete && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="zen-card text-center"
                    style={{ padding: '60px', borderRadius: '32px', marginBottom: '24px' }}
                >
                    <div className="flex justify-center mb-6">
                        <div style={{ background: '#FFC107', color: 'white', padding: '24px', borderRadius: '50%' }}>
                            <Sparkles size={64} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Family Expert!</h2>
                    <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>
                        You correctly placed <b>{quizScore}</b> of {familyData.length} family members.
                    </p>
                    <button onClick={onBack} className="btn-primary" style={{ padding: '16px 32px', borderRadius: '100px', margin: '0 auto' }}>
                        Finish Module <CheckCircle2 size={20} style={{ marginLeft: '8px' }} />
                    </button>
                </motion.div>
            )}

            {/* Family Tree Container */}
            {!quizComplete && (
                <div style={{ width: '100%', overflowX: 'auto', borderRadius: '32px', border: '1px solid var(--border-soft)' }}>
                    <div 
                        style={{ 
                            position: 'relative', 
                            width: '100%', 
                            height: '800px', 
                            minWidth: '1100px',
                            background: 'rgba(var(--bg-card-rgb), 0.5)',
                            backdropFilter: 'blur(8px)',
                            overflow: 'hidden',
                            boxShadow: 'inset 0 0 40px rgba(0,0,0,0.05)'
                        }}
                    >
                    {/* Row Labels */}
                    {[
                        { label: 'Grandparents', y: '3%' },
                        { label: 'Parents & Elders', y: '33%' },
                        { label: 'You & Siblings', y: '63%' },
                        { label: 'Next Generation', y: '88%' },
                    ].map(r => (
                        <div key={r.label} style={{ position: 'absolute', left: '0', top: r.y, width: '100%', textAlign: 'center', fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-light)', textTransform: 'uppercase', letterSpacing: '2px', pointerEvents: 'none', zIndex: 0 }}>
                            {r.label}
                        </div>
                    ))}

                    {/* SVG Connector Lines */}
                    <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 1 }}>
                        {CONNECTIONS.map((conn, i) => {
                            const from = TREE_LAYOUT[conn.from];
                            const to = TREE_LAYOUT[conn.to];
                            if (!from || !to) return null;
                            return (
                                <line
                                    key={i}
                                    x1={`${from.x}%`}
                                    y1={`${from.y + 8}%`}
                                    x2={`${to.x}%`}
                                    y2={`${to.y}%`}
                                    stroke="var(--border-soft)"
                                    strokeWidth="1.5"
                                    strokeDasharray="6,4"
                                    opacity={0.6}
                                />
                            );
                        })}
                    </svg>

                    {/* Central "Me" Node */}
                    <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.3, type: 'spring' }}
                        style={{
                            position: 'absolute',
                            left: '50%',
                            top: '63%',
                            transform: 'translateX(-50%)',
                            width: '100px',
                            height: '100px',
                            borderRadius: '50%',
                            background: 'var(--primary)',
                            color: 'white',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            zIndex: 5,
                            boxShadow: '0 8px 32px rgba(var(--primary-rgb), 0.4)',
                            border: '4px solid rgba(255,255,255,0.3)'
                        }}
                    >
                        <span className="devanagari" style={{ fontSize: '1.6rem', fontWeight: 900 }}>अहम्</span>
                        <span style={{ fontSize: '0.65rem', fontWeight: 700, opacity: 0.8 }}>ME</span>
                    </motion.div>

                    {/* Family Nodes */}
                    {familyData.map((member, i) => {
                        const pos = TREE_LAYOUT[member.id];
                        if (!pos) return null;
                        const isRevealed = revealedIds.has(member.id);
                        const colors = GENDER_COLORS[member.gender];
                        const isFeedback = feedback?.id === member.id;
                        const feedbackCorrect = feedback?.correct;

                        return (
                            <motion.div
                                key={member.id}
                                initial={{ opacity: 0, scale: 0.5 }}
                                animate={{ 
                                    opacity: 1, 
                                    scale: 1,
                                    ...(isFeedback && !feedbackCorrect ? { x: ["-50%", "-48%", "-52%", "-48%", "-52%", "-50%"] } : { x: "-50%" })
                                }}
                                transition={{ 
                                    delay: i * 0.05, 
                                    type: 'spring', 
                                    stiffness: 300,
                                    x: isFeedback && !feedbackCorrect ? { duration: 0.4 } : {}
                                }}
                                whileHover={{ scale: 1.08, y: -4 }}
                                onClick={() => quizMode ? handleQuizClick(member.id) : handleReveal(member.id)}
                                style={{
                                    position: 'absolute',
                                    left: `${pos.x}%`,
                                    top: `${pos.y + 4}%`,
                                    width: '110px',
                                    minHeight: '70px',
                                    borderRadius: '18px',
                                    padding: '10px 8px',
                                    cursor: 'pointer',
                                    zIndex: 3,
                                    textAlign: 'center',
                                    transition: 'background 0.3s, border 0.3s, box-shadow 0.3s',
                                    background: isFeedback
                                        ? (feedbackCorrect ? 'rgba(76, 175, 80, 0.15)' : 'rgba(255, 82, 82, 0.15)')
                                        : isRevealed ? colors.bg : 'rgba(var(--bg-card-rgb), 0.9)',
                                    border: `2px solid ${
                                        isFeedback
                                            ? (feedbackCorrect ? '#4CAF50' : '#FF5252')
                                            : isRevealed ? colors.border : 'var(--border-soft)'
                                    }`,
                                    boxShadow: isRevealed
                                        ? `0 6px 20px ${colors.border}22`
                                        : '0 4px 12px rgba(0,0,0,0.05)',
                                    backdropFilter: 'blur(6px)'
                                }}
                            >
                                <AnimatePresence mode="wait">
                                    {isRevealed ? (
                                        <motion.div
                                            key="revealed"
                                            initial={{ rotateY: 90 }}
                                            animate={{ rotateY: 0 }}
                                            exit={{ rotateY: -90 }}
                                            transition={{ duration: 0.3 }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
                                                <div className="devanagari" style={{ fontSize: '1.3rem', fontWeight: 900, color: colors.text, lineHeight: 1.2 }}>
                                                    {member.sanskrit}
                                                </div>
                                                <div onClick={(e) => e.stopPropagation()}>
                                                    <AudioPronounceButton text={member.sanskrit} size={14} title={`Pronounce: ${member.sanskrit}`} />
                                                </div>
                                            </div>
                                            <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 600, marginTop: '2px' }}>
                                                {member.transliteration}
                                            </div>
                                            <div style={{ fontSize: '0.6rem', color: 'var(--text-light)', marginTop: '4px', fontWeight: 700, textTransform: 'uppercase' }}>
                                                {member.englishMeaning}
                                            </div>
                                        </motion.div>
                                    ) : (
                                        <motion.div
                                            key="hidden"
                                            initial={{ rotateY: -90 }}
                                            animate={{ rotateY: 0 }}
                                            exit={{ rotateY: 90 }}
                                            transition={{ duration: 0.3 }}
                                        >
                                            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.3 }}>
                                                {member.englishMeaning}
                                            </div>
                                            <div style={{ fontSize: '0.6rem', color: 'var(--text-light)', marginTop: '4px' }}>
                                                {quizMode ? '?' : 'Tap to reveal'}
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        );
                    })}
                    </div>
                </div>
            )}

            {/* All Revealed CTA */}
            {allRevealed && !quizMode && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-center mt-8 gap-4"
                >
                    <button onClick={startQuizMode} className="btn-primary" style={{ padding: '16px 32px', borderRadius: '100px' }}>
                        <Zap size={18} style={{ marginRight: '8px' }} /> Start Quiz Mode
                    </button>
                    <button onClick={onBack} className="btn-secondary" style={{ padding: '16px 32px', borderRadius: '100px' }}>
                        Finish Lesson <CheckCircle2 size={18} style={{ marginLeft: '8px' }} />
                    </button>
                </motion.div>
            )}
        </div>
    );
}
