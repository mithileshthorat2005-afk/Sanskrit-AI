import React, { useState, useEffect } from 'react';
import { 
    ArrowLeft, 
    Flame,
    UserCircle,
    CheckCircle2,
    Sparkles,
    MessageCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import AudioPronounceButton from '@/components/AudioPronounceButton';
import SanskritInput from '@/components/SanskritInput';

interface IntroOption {
    english: string;
    sanskrit: string;
    transliteration: string;
}

interface IntroItem {
    id: string;
    category: string;
    templateSanskrit: string;
    templateTransliteration: string;
    englishMeaning: string;
    options: IntroOption[];
}

export default function SelfIntroLesson({ onBack }: { onBack: () => void }) {
    const [introData, setIntroData] = useState<IntroItem[]>([]);
    const [numbersData, setNumbersData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [activeStep, setActiveStep] = useState(0);
    const [showFinal, setShowFinal] = useState(false);

    useEffect(() => {
        const fetchIntroData = async () => {
            try {
                const [introResult, numbersResult] = await Promise.all([
                    api.lessons.getSelfIntro(),
                    api.lessons.getNumbers()
                ]);
                if (introResult.success) {
                    setIntroData(introResult.data);
                }
                if (numbersResult.success) {
                    setNumbersData(numbersResult.data);
                }
            } catch (error) {
                console.error("Failed to fetch self intro or numbers data", error);
            } finally {
                setLoading(false);
            }
        };
        fetchIntroData();
    }, []);

    const handleInput = (id: string, value: string) => {
        setAnswers({ ...answers, [id]: value });
    };

    const handleNext = () => {
        if (activeStep < introData.length - 1) {
            setActiveStep(activeStep + 1);
        } else {
            setShowFinal(true);
        }
    };

    const generateSentence = (template: string, value: string, placeholder: string) => {
        if (!value) return template;
        return template.replace(`[${placeholder}]`, `<span style="color: var(--primary); font-weight: bold;">${value}</span>`);
    };

    const generateParagraph = (isSanskrit: boolean) => {
        return introData.map((item) => {
            const val = answers[item.id] || `[...]`;
            const template = isSanskrit ? item.templateSanskrit : item.englishMeaning;
            return generateSentence(template, val, isSanskrit ? item.category.split(' ')[0] : item.category.split(' ')[0]);
        }).join(' ');
    };

    // Helper to get the correct placeholder tag for replacement
    const getPlaceholder = (category: string) => category.split(' ')[0]; // E.g., 'Profession (Masculine)' -> 'Profession'

    if (loading) return (
        <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
            <motion.div animate={{ scale: [1, 1.1, 1], opacity: [0.5, 1, 0.5] }} transition={{ repeat: Infinity, duration: 2 }}>
                <Flame size={64} style={{ color: 'var(--primary)' }} />
            </motion.div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 600, letterSpacing: '1px', color: 'var(--text-main)' }}>Forging Identity Matrix...</h3>
        </div>
    );

    if (showFinal) {
        return (
            <div style={{ padding: '40px 20px', maxWidth: '800px', margin: '0 auto' }}>
                <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                    className="zen-card"
                    style={{ padding: '60px', textAlign: 'center', background: 'var(--bg-card)' }}
                >
                    <Sparkles size={48} style={{ color: 'var(--primary)', margin: '0 auto 20px' }} />
                    <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '40px', color: 'var(--text-main)' }}>
                        Your Sanskrit Identity
                    </h2>

                    <div style={{ background: 'rgba(var(--primary-rgb), 0.03)', padding: '40px', borderRadius: '30px', border: '1px solid var(--border-soft)', marginBottom: '40px' }}>
                        {introData.map(item => {
                            const val = answers[item.id];
                            if (!val && item.id !== 'intro_9') return null; // intro_9 is purely closing, no variables
                            
                            const placeholder = getPlaceholder(item.category);
                            let finalSanskrit = item.templateSanskrit;
                            let finalTranslit = item.templateTransliteration;
                            
                            if (item.options.length > 0) {
                                // Find the option user clicked to get the sanskrit word
                                const opt = item.options.find(o => o.sanskrit === val || o.english === val);
                                if (opt) {
                                    finalSanskrit = finalSanskrit.replace(`[${placeholder}]`, opt.sanskrit);
                                    finalTranslit = finalTranslit.replace(`[${placeholder}]`, opt.transliteration);
                                }
                            } else if (item.category === 'Age' && val) {
                                const numEntry = numbersData.find(n => n.number.toString() === val);
                                const replaceValSanskrit = numEntry ? numEntry.sanskrit : val;
                                const replaceValTranslit = numEntry ? numEntry.transliteration : val;
                                finalSanskrit = finalSanskrit.replace(`[${placeholder}]`, replaceValSanskrit);
                                finalTranslit = finalTranslit.replace(`[${placeholder}]`, replaceValTranslit);
                            } else if (val) {
                                finalSanskrit = finalSanskrit.replace(`[${placeholder}]`, val);
                                finalTranslit = finalTranslit.replace(`[${placeholder}]`, val);
                            }

                            return (
                                <motion.div 
                                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} 
                                    key={item.id} 
                                    style={{ marginBottom: '24px', textAlign: 'left' }}
                                >
                                    <div className="devanagari" style={{ fontSize: '2.5rem', color: 'var(--text-main)', lineHeight: '1.4' }}>
                                        {finalSanskrit}
                                    </div>
                                    <AudioPronounceButton text={finalSanskrit} size={20} title="Listen to your Sanskrit introduction" />
                                    <div style={{ fontSize: '1.2rem', color: 'var(--text-light)', fontStyle: 'italic', marginTop: '4px' }}>
                                        {finalTranslit}
                                    </div>
                                </motion.div>
                            )
                        })}
                    </div>

                    <div className="flex gap-4 justify-center">
                        <button onClick={() => setShowFinal(false)} className="btn-secondary" style={{ padding: '16px 32px' }}>
                            Edit Profile
                        </button>
                        <button onClick={onBack} className="btn-primary" style={{ padding: '16px 32px' }}>
                            Complete Lesson <CheckCircle2 size={20} className="ml-2" />
                        </button>
                    </div>
                </motion.div>
            </div>
        );
    }

    const currentItem = introData[activeStep];
    const val = answers[currentItem?.id] || '';
    const placeholder = getPlaceholder(currentItem?.category || '');

    return (
        <div style={{ padding: '40px 20px', maxWidth: '1000px', margin: '0 auto', minHeight: '80vh' }}>
            <motion.div 
                initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
                className="zen-card" 
                style={{ 
                    padding: '40px', marginBottom: '40px', borderRadius: '30px',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
                    border: '1px solid var(--border-soft)'
                }}
            >
                <motion.button onClick={onBack} style={{ position: 'absolute', left: '40px', top: '40px', background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
                    <ArrowLeft size={28} />
                </motion.button>

                <div style={{ color: 'var(--primary)', fontSize: '0.85rem', fontWeight: 800, letterSpacing: '4px', textTransform: 'uppercase', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <UserCircle size={18} /> Interactive Profile
                </div>
                <h1 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '8px', color: 'var(--text-main)' }}>Forge Your Avatar</h1>
            </motion.div>

            <div className="grid md:grid-cols-2 gap-10">
                {/* Form Side */}
                <div className="flex flex-col gap-6">
                    <div className="flex justify-between items-center mb-4">
                        <span style={{ fontWeight: 800, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px' }}>Step {activeStep + 1} of {introData.length}</span>
                        <div className="flex gap-2">
                            {introData.map((_, i) => (
                                <div key={i} style={{ width: '8px', height: '8px', borderRadius: '50%', background: i <= activeStep ? 'var(--primary)' : 'var(--border-soft)' }} />
                            ))}
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        <motion.div 
                            key={activeStep}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            className="zen-card"
                            style={{ padding: '40px', background: 'var(--bg-card)' }}
                        >
                            <h2 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: '8px' }}>
                                What is your {placeholder}?
                            </h2>
                            <p style={{ color: 'var(--text-dim)', marginBottom: '30px' }}>{currentItem.englishMeaning}</p>

                            {currentItem.id === 'intro_9' ? (
                                <div style={{ fontSize: '1.2rem', color: 'var(--primary)', fontStyle: 'italic', padding: '20px', background: 'rgba(var(--primary-rgb), 0.1)', borderRadius: '16px', textAlign: 'center' }}>
                                    Standard greeting conclusion. Just proceed!
                                </div>
                            ) : currentItem.options.length > 0 ? (
                                <div className="grid grid-cols-2 gap-4">
                                    {currentItem.options.map((opt, i) => {
                                        const isSelected = val === opt.sanskrit;
                                        return (
                                            <motion.button
                                                key={i}
                                                whileHover={{ scale: 1.02 }}
                                                whileTap={{ scale: 0.98 }}
                                                onClick={() => handleInput(currentItem.id, opt.sanskrit)}
                                                style={{
                                                    padding: '24px',
                                                    borderRadius: '20px',
                                                    background: isSelected ? 'var(--primary)' : 'var(--bg-main)',
                                                    color: isSelected ? 'white' : 'var(--text-main)',
                                                    border: `2px solid ${isSelected ? 'var(--primary)' : 'var(--border-soft)'}`,
                                                    textAlign: 'center',
                                                    cursor: 'pointer',
                                                    transition: 'all 0.2s'
                                                }}
                                            >
                                                <div className="devanagari" style={{ fontSize: '2rem', marginBottom: '8px' }}>{opt.sanskrit}</div>
                                                <div style={{ fontSize: '1rem', fontWeight: 600 }}>{opt.english}</div>
                                            </motion.button>
                                        )
                                    })}
                                </div>
                            ) : (placeholder === 'Age' || placeholder === 'Number') ? (
                                <input 
                                    type="number"
                                    value={val}
                                    onChange={(e) => handleInput(currentItem.id, e.target.value)}
                                    placeholder={`Enter your ${placeholder.toLowerCase()}...`}
                                    style={{
                                        width: '100%',
                                        padding: '24px 30px',
                                        fontSize: '1.5rem',
                                        background: 'var(--bg-main)',
                                        border: '2px solid var(--border-soft)',
                                        borderRadius: '20px',
                                        color: 'var(--text-main)',
                                        outline: 'none'
                                    }}
                                />
                            ) : (
                                <div style={{ background: 'var(--bg-main)', borderRadius: '20px', padding: '16px', border: '2px solid var(--border-soft)' }}>
                                    <SanskritInput 
                                        value={val}
                                        onChange={(v: string) => handleInput(currentItem.id, v)}
                                        placeholder={`Enter your ${placeholder.toLowerCase()}...`}
                                        showLabel={true}
                                    />
                                </div>
                            )}

                            <div className="mt-10 flex justify-end">
                                <motion.button
                                    whileHover={{ scale: 1.05 }}
                                    onClick={handleNext}
                                    disabled={!val && currentItem.id !== 'intro_9'}
                                    style={{
                                        padding: '16px 40px',
                                        background: (!val && currentItem.id !== 'intro_9') ? 'var(--bg-main)' : 'var(--primary)',
                                        color: (!val && currentItem.id !== 'intro_9') ? 'var(--text-dim)' : '#white',
                                        border: 'none',
                                        borderRadius: '100px',
                                        fontWeight: 800,
                                        cursor: (!val && currentItem.id !== 'intro_9') ? 'not-allowed' : 'pointer'
                                    }}
                                    className="text-white"
                                >
                                    {activeStep === introData.length - 1 ? 'Complete Profile' : 'Next Step →'}
                                </motion.button>
                            </div>
                        </motion.div>
                    </AnimatePresence>
                </div>

                {/* Instant Preview Side */}
                <div>
                     <div className="zen-card sticky top-10" style={{ padding: '40px', border: '1px dashed var(--border-soft)', background: 'var(--bg-card)' }}>
                        <div className="flex items-center gap-3 mb-8" style={{ color: 'var(--primary)', fontWeight: 800, letterSpacing: '2px', textTransform: 'uppercase', fontSize: '0.9rem' }}>
                            <MessageCircle size={20} /> Live Preview
                        </div>

                        {introData.filter((_, i) => i <= activeStep).map((item, i) => {
                            const itemVal = answers[item.id];
                            if (!itemVal && item.id !== 'intro_9') return null;

                            const p = getPlaceholder(item.category);
                            let finalSanskrit = item.templateSanskrit;
                            let isCurrent = i === activeStep;

                            if (item.options.length > 0) {
                                const opt = item.options.find(o => o.sanskrit === itemVal || o.english === itemVal);
                                if (opt) finalSanskrit = finalSanskrit.replace(`[${p}]`, opt.sanskrit);
                                else finalSanskrit = finalSanskrit.replace(`[${p}]`, `...`);
                            } else if (item.category === 'Age' && itemVal) {
                                const numEntry = numbersData.find(n => n.number.toString() === itemVal);
                                finalSanskrit = finalSanskrit.replace(`[${p}]`, numEntry ? numEntry.sanskrit : itemVal);
                            } else {
                                finalSanskrit = finalSanskrit.replace(`[${p}]`, itemVal || `...`);
                            }

                            return (
                                <motion.div 
                                    key={i}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: isCurrent ? 1 : 0.4, scale: isCurrent ? 1 : 0.95 }}
                                    style={{ marginBottom: '24px', transformOrigin: 'left center' }}
                                >
                                    <div className="devanagari" style={{ fontSize: isCurrent ? '2.8rem' : '2rem', color: isCurrent ? 'var(--text-main)' : 'var(--text-light)', transition: 'all 0.3s' }}>
                                        {finalSanskrit}
                                    </div>
                                </motion.div>
                            )
                        })}
                     </div>
                </div>
            </div>
        </div>
    );
}
