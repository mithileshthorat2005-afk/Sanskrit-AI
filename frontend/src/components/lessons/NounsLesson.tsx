import React, { useState, useEffect } from 'react';
import { 
    ArrowLeft, 
    CheckCircle2, 
    Zap, 
    Info, 
    HelpCircle,
    User,
    UserPlus,
    Box,
    Sparkles,
    AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { api } from '@/lib/api';
import AudioPronounceButton from '@/components/AudioPronounceButton';

interface NounItem {
    id: string;
    sanskrit: string;
    transliteration: string;
    englishMeaning: string;
    gender: 'masculine' | 'feminine' | 'neuter';
    hint: string;
}

export default function NounsLesson({ onBack }: { onBack: () => void }) {
    const [nouns, setNouns] = useState<NounItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCheatCode, setShowCheatCode] = useState(true);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [score, setScore] = useState(0);
    const [gameComplete, setGameComplete] = useState(false);
    const [feedback, setFeedback] = useState<'correct' | 'wrong' | null>(null);

    // Draggable state
    const x = useMotionValue(0);
    const y = useMotionValue(0);
    const rotateValue = useTransform(x, [-200, 200], [-25, 25]);
    const opacityValue = useTransform(x, [-200, -150, 0, 150, 200], [0, 1, 1, 1, 0]);

    useEffect(() => {
        const fetchNouns = async () => {
            try {
                const res = await api.lessons.getNouns();
                // Ensure res is array even if wrapped in data
                const data = Array.isArray(res) ? res : (res?.data || res || []);
                setNouns(data.sort(() => Math.random() - 0.5));
            } catch (error) {
                console.error("Failed to fetch nouns", error);
            } finally {
                setLoading(false);
            }
        };
        fetchNouns();
    }, []);

    const handleDragEnd = (event: any, info: any) => {
        const threshold = 100;
        
        if (info.offset.x < -threshold) {
            checkAnswer('masculine');
        } else if (info.offset.x > threshold) {
            checkAnswer('feminine');
        } else if (info.offset.y > threshold) {
            checkAnswer('neuter');
        }
    };

    const checkAnswer = (selectedGender: string) => {
        const correctGender = nouns[currentIndex].gender;
        
        if (selectedGender === correctGender) {
            setFeedback('correct');
            setScore(s => s + 1);
            setTimeout(() => {
                nextNoun();
            }, 600);
        } else {
            setFeedback('wrong');
            setTimeout(() => {
                setFeedback(null);
            }, 600);
        }
    };

    const nextNoun = () => {
        setFeedback(null);
        if (currentIndex < nouns.length - 1) {
            setCurrentIndex(i => i + 1);
        } else {
            setGameComplete(true);
        }
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: "linear" }}>
                <Zap size={48} style={{ color: 'var(--primary)' }} />
            </motion.div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Noun Manuscripts...</h3>
        </div>
    );

    if (showCheatCode) {
        return (
            <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="max-w-4xl mx-auto"
            >
                <div className="zen-card" style={{ padding: '40px', borderRadius: '32px' }}>
                    <div className="flex items-center gap-4 mb-8">
                        <div style={{ background: 'var(--primary)', color: 'white', padding: '12px', borderRadius: '16px' }}>
                            <Zap size={32} />
                        </div>
                        <div>
                            <h1 style={{ fontSize: '2.4rem', fontWeight: 900 }}>The Gender Cheat Code</h1>
                            <p style={{ color: 'var(--text-dim)' }}>Master the patterns to unlock fluent Sanskrit.</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
                        <div style={{ background: 'rgba(var(--primary-rgb), 0.05)', padding: '24px', borderRadius: '24px', border: '1px solid var(--border-soft)' }}>
                            <div className="flex items-center gap-2 mb-4" style={{ color: 'var(--primary)', fontWeight: 800, textTransform: 'uppercase', fontSize: '0.8rem' }}>
                                <User size={16} /> Masculine
                            </div>
                            <div className="devanagari text-center" style={{ fontSize: '3rem', marginBottom: '16px', color: 'var(--primary)' }}>◌ः</div>
                            <p style={{ fontSize: '0.95rem', lineHeight: 1.6, color: 'var(--text-main)', fontWeight: 600 }}>Usually ends in <b>Visarga (: / ḥ)</b></p>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Example: बालकः (Boy)</span>
                        </div>

                        <div style={{ background: 'rgba(255, 82, 82, 0.05)', padding: '24px', borderRadius: '24px', border: '1px solid rgba(255, 82, 82, 0.1)' }}>
                            <div className="flex items-center gap-2 mb-4" style={{ color: '#FF5252', fontWeight: 800, textTransform: 'uppercase', fontSize: '0.8rem' }}>
                                <UserPlus size={16} /> Feminine
                            </div>
                            <div className="devanagari text-center" style={{ fontSize: '3rem', marginBottom: '16px', color: '#FF5252' }}>◌ा | ◌ी</div>
                            <p style={{ fontSize: '0.95rem', lineHeight: 1.6, color: 'var(--text-main)', fontWeight: 600 }}>Usually ends in <b>Long 'ā' or 'ī'</b></p>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Example: बालिका (Girl)</span>
                        </div>

                        <div style={{ background: 'rgba(76, 175, 80, 0.05)', padding: '24px', borderRadius: '24px', border: '1px solid rgba(76, 175, 80, 0.1)' }}>
                            <div className="flex items-center gap-2 mb-4" style={{ color: '#4CAF50', fontWeight: 800, textTransform: 'uppercase', fontSize: '0.8rem' }}>
                                <Box size={16} /> Neuter
                            </div>
                            <div className="devanagari text-center" style={{ fontSize: '3rem', marginBottom: '16px', color: '#4CAF50' }}>◌म्</div>
                            <p style={{ fontSize: '0.95rem', lineHeight: 1.6, color: 'var(--text-main)', fontWeight: 600 }}>Usually ends in <b>Halant 'm' (म्)</b></p>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Example: फलम् (Fruit)</span>
                        </div>
                    </div>

                    <div className="flex justify-center">
                        <button 
                            className="btn-primary" 
                            style={{ padding: '20px 60px', borderRadius: '100px', fontSize: '1.2rem' }}
                            onClick={() => setShowCheatCode(false)}
                        >
                            Start Sorting Game <Play className="ml-2" />
                        </button>
                    </div>
                </div>
            </motion.div>
        );
    }

    if (gameComplete) {
        return (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center p-20">
                <div className="zen-card" style={{ padding: '60px', borderRadius: '40px' }}>
                    <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="mb-8 flex justify-center">
                        <div style={{ background: '#FFC107', padding: '30px', borderRadius: '50%', color: 'white' }}>
                            <Sparkles size={80} />
                        </div>
                    </motion.div>
                    <h1 style={{ fontSize: '3rem', fontWeight: 900, marginBottom: '16px' }}>Master Classifier!</h1>
                    <p style={{ fontSize: '1.4rem', color: 'var(--text-dim)', marginBottom: '40px' }}>
                        You correctly identified <b>{score}</b> Sanskrit genders.
                    </p>
                    <button onClick={onBack} className="btn-primary" style={{ margin: '0 auto', padding: '20px 40px', borderRadius: '100px' }}>
                        Back to Lessons <CheckCircle2 className="ml-2" />
                    </button>
                </div>
            </motion.div>
        );
    }

    const currentNoun = nouns[currentIndex];

    return (
        <div style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto', height: '80vh', display: 'flex', flexDirection: 'column' }}>
            <div className="flex justify-between items-center mb-8">
                <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ArrowLeft size={20} /> Quit Game
                </button>
                <div style={{ fontWeight: 800, color: 'var(--primary)' }}>
                    WORD {currentIndex + 1} / {nouns.length}
                </div>
                <div className="flex items-center gap-2" style={{ fontWeight: 800 }}>
                    <Sparkles size={18} color="#FFC107" /> SCORE: {score}
                </div>
            </div>

            <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                
                {/* Visual Background Indicators */}
                <div style={{ position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', opacity: 0.2, textAlign: 'center', color: 'var(--primary)' }}>
                    <User size={120} />
                    <div style={{ fontWeight: 900 }}>MALE</div>
                </div>
                <div style={{ position: 'absolute', right: 0, top: '50%', transform: 'translateY(-50%)', opacity: 0.2, textAlign: 'center', color: '#FF5252' }}>
                    <UserPlus size={120} />
                    <div style={{ fontWeight: 900 }}>FEMALE</div>
                </div>
                <div style={{ position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)', opacity: 0.2, textAlign: 'center', color: '#4CAF50' }}>
                    <Box size={100} />
                    <div style={{ fontWeight: 900 }}>NEUTER</div>
                </div>

                {/* The Floating Card */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentNoun.id}
                        drag
                        dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
                        onDragEnd={handleDragEnd}
                        className="zen-card cursor-grab active:cursor-grabbing"
                        style={{
                            x, 
                            y, 
                            rotate: rotateValue, 
                            opacity: opacityValue, 
                            width: '320px', 
                            height: '420px', 
                            zIndex: 10,
                            padding: '40px',
                            borderRadius: '32px',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            textAlign: 'center',
                            background: feedback === 'correct' ? '#4CAF50' : feedback === 'wrong' ? '#FF5252' : 'var(--bg-card)',
                            color: feedback ? 'white' : 'var(--text-main)',
                            border: '1px solid var(--border-soft)',
                            boxShadow: '0 30px 60px rgba(0,0,0,0.1)'
                        }}
                    >
                        <motion.div
                            animate={feedback === 'wrong' ? { x: [-10, 10, -10, 10, 0] } : {}}
                            transition={{ duration: 0.4 }}
                        >
                            <div className="flex items-center justify-center gap-3">
                                <div className="devanagari" style={{ fontSize: '4.5rem', fontWeight: 900, marginBottom: '8px' }}>
                                    {currentNoun.sanskrit}
                                </div>
                                <div onClick={(e) => e.stopPropagation()}>
                                    <AudioPronounceButton text={currentNoun.sanskrit} size={28} title={`Pronounce: ${currentNoun.sanskrit}`} />
                                </div>
                            </div>
                            <div style={{ fontSize: '1.4rem', opacity: 0.7, fontStyle: 'italic', marginBottom: '32px' }}>
                                "{currentNoun.transliteration}"
                            </div>
                            <div style={{ height: '2px', background: 'rgba(0,0,0,0.1)', width: '40px', margin: '0 auto 32px auto' }} />
                            <div style={{ fontSize: '1.8rem', fontWeight: 800 }}>
                                {currentNoun.englishMeaning}
                            </div>
                            
                            {feedback === 'wrong' && (
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ marginTop: '24px', fontWeight: 800, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <AlertCircle size={18} /> HINT: {currentNoun.hint}
                                </motion.div>
                            )}
                        </motion.div>
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* Instruction Footer */}
            <div className="text-center p-8" style={{ color: 'var(--text-dim)', fontWeight: 600 }}>
                Swipe Left for <b>Male</b> | Right for <b>Female</b> | Down for <b>Neuter</b>
            </div>
        </div>
    );
}

const Play = ({ className }: { className?: string }) => (
  <svg className={className} width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3l14 9-14 9V3z"/></svg>
);
