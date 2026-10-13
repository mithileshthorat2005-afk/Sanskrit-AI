import React, { useState, useEffect } from 'react';
import { ArrowLeft, CheckCircle2, Play, RefreshCw, Volume2, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import AudioPronounceButton from '@/components/AudioPronounceButton';

interface VerbItem {
    id: string;
    root: string;
    sanskrit: string;
    transliteration: string;
    englishMeaning: string;
    exampleSanskrit: string;
    exampleEnglish: string;
}

interface PronounItem {
    id: string;
    sanskrit: string;
    englishMeaning: string;
}

export default function VerbsLesson({ onBack }: { onBack: () => void }) {
    const [verbs, setVerbs] = useState<VerbItem[]>([]);
    const [pronouns, setPronouns] = useState<PronounItem[]>([]);
    const [loading, setLoading] = useState(true);
    
    // Game State
    const [currentIndex, setCurrentIndex] = useState(0);
    const [selectedWords, setSelectedWords] = useState<string[]>([]);
    const [options, setOptions] = useState<string[]>([]);
    const [isCorrect, setIsCorrect] = useState<boolean | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [verbsRes, pronounsRes] = await Promise.all([
                    api.lessons.getVerbs(),
                    api.lessons.getPronouns()
                ]);
                
                if (verbsRes.success || pronounsRes.success) {
                    const vData = verbsRes.success ? verbsRes.data : verbsRes;
                    const pData = pronounsRes.success ? pronounsRes.data : pronounsRes;
                    // Handle case where .data isn't wrapped
                    setVerbs(Array.isArray(vData) ? vData : []);
                    setPronouns(Array.isArray(pData) ? pData : []);
                } else if (Array.isArray(verbsRes) && Array.isArray(pronounsRes)) {
                    setVerbs(verbsRes);
                    setPronouns(pronounsRes);
                }
            } catch (error) {
                console.error("Failed to fetch data", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    useEffect(() => {
        if (verbs.length > 0) {
            setupLevel(currentIndex);
        }
    }, [verbs, currentIndex]);

    const setupLevel = (index: number) => {
        const verb = verbs[index];
        if (!verb) return;

        // Extract correct words from the sanskrit example (remove danda '।')
        const correctSentence = verb.exampleSanskrit.replace('।', '').trim();
        const correctWords = correctSentence.split(' ');
        
        // Generate distractors
        const distractors = new Set<string>();
        
        // Add some random verbs
        while (distractors.size < 2 && verbs.length > 2) {
            const randomVerb = verbs[Math.floor(Math.random() * verbs.length)];
            if (randomVerb.sanskrit !== verb.sanskrit) {
                distractors.add(randomVerb.sanskrit);
            }
        }
        
        // Add some random pronouns if available
        if (pronouns.length > 0) {
            while (distractors.size < 4) {
                const randomPronoun = pronouns[Math.floor(Math.random() * pronouns.length)];
                if (!correctWords.includes(randomPronoun.sanskrit)) {
                    distractors.add(randomPronoun.sanskrit);
                }
            }
        } else {
            distractors.add("सा");
            distractors.add("अहम्");
        }

        const allOptions = [...correctWords, ...Array.from(distractors)].sort(() => Math.random() - 0.5);
        
        setOptions(allOptions);
        setSelectedWords([]);
        setIsCorrect(null);
    };

    const handleSelectOption = (word: string) => {
        if (isCorrect) return; // Prevent selection if already correct
        
        const verb = verbs[currentIndex];
        const correctSequence = verb.exampleSanskrit.replace('।', '').trim().split(' ');
        const targetLen = correctSequence.length;

        if (selectedWords.length < targetLen) {
            const newSelection = [...selectedWords, word];
            setSelectedWords(newSelection);
            
            // Remove from options
            setOptions(options.filter((o, idx) => !(o === word && idx === options.indexOf(word))));

            // Check if filled
            if (newSelection.length === targetLen) {
                if (newSelection.join(' ') === correctSequence.join(' ')) {
                    setIsCorrect(true);
                    setTimeout(() => {
                        if (currentIndex < verbs.length - 1) {
                            setCurrentIndex(currentIndex + 1);
                        }
                    }, 2000);
                } else {
                    setIsCorrect(false);
                }
            }
        }
    };

    const handleRemoveWord = (word: string, index: number) => {
        if (isCorrect) return;
        
        const newSelection = [...selectedWords];
        newSelection.splice(index, 1);
        setSelectedWords(newSelection);
        setOptions([...options, word]);
        setIsCorrect(null);
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: "linear" }}>
                    <RefreshCw size={48} style={{ color: 'var(--primary)' }} />
                </motion.div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-main)' }}>Loading Action Words...</h3>
            </div>
        );
    }

    if (verbs.length === 0) return <div>No verbs available.</div>;

    const currentVerb = verbs[currentIndex];
    const correctSequence = currentVerb.exampleSanskrit.replace('।', '').trim().split(' ');
    
    const isLevelComplete = currentIndex >= verbs.length - 1 && isCorrect;

    return (
        <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', minHeight: '70vh' }}>
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
                <h1 style={{ fontSize: '2rem', fontWeight: 900, marginBottom: '4px', color: 'var(--text-main)' }}>Sentence Builder</h1>
                <p style={{ color: 'var(--text-dim)', fontSize: '0.95rem' }}>Select the correct words to form the translation.</p>
                
                <div style={{ marginTop: '16px', background: 'var(--bg-main)', padding: '6px 16px', borderRadius: '20px', fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Action {currentIndex + 1} of {verbs.length}
                </div>
            </motion.div>

            {isLevelComplete ? (
                <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                    className="zen-card text-center" style={{ padding: '60px', borderRadius: '30px' }}
                >
                    <div className="flex justify-center mb-6">
                        <div style={{ background: '#4CAF50', color: 'white', padding: '20px', borderRadius: '50%' }}>
                            <CheckCircle2 size={64} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '16px' }}>Mastery Achieved!</h2>
                    <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginBottom: '32px' }}>You have learned the foundations of Sanskrit action words.</p>
                    <button onClick={onBack} className="btn-primary" style={{ padding: '16px 32px', fontSize: '1.1rem', borderRadius: '100px', margin: '0 auto' }}>
                        Finish Module <CheckCircle2 size={20} className="ml-2" />
                    </button>
                </motion.div>
            ) : (
                <div className="flex flex-col gap-8">
                    {/* The Target Sentence */}
                    <div className="zen-card flex flex-col items-center justify-center relative" style={{ padding: '60px 40px', minHeight: '250px', background: isCorrect ? 'rgba(76, 175, 80, 0.05)' : 'var(--bg-card)', border: isCorrect ? '2px solid #4CAF50' : '1px solid var(--border-soft)', transition: 'all 0.5s ease' }}>
                        <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '40px', textAlign: 'center' }}>
                            "{currentVerb.exampleEnglish}"
                        </div>
                        
                        <div className="flex flex-wrap justify-center gap-4">
                            {correctSequence.map((_, i) => (
                                <div 
                                    key={i} 
                                    onClick={() => selectedWords[i] && handleRemoveWord(selectedWords[i], i)}
                                    className="devanagari"
                                    style={{ 
                                        width: '140px', 
                                        height: '70px', 
                                        borderRadius: '16px', 
                                        border: selectedWords[i] ? 'none' : '2px dashed var(--border-soft)',
                                        background: selectedWords[i] ? (isCorrect ? '#4CAF50' : isCorrect === false ? '#FF5252' : 'var(--primary)') : 'transparent',
                                        color: selectedWords[i] ? 'white' : 'transparent',
                                        display: 'flex', 
                                        alignItems: 'center', 
                                        justifyContent: 'center',
                                        fontSize: '1.8rem',
                                        fontWeight: 900,
                                        cursor: selectedWords[i] && !isCorrect ? 'pointer' : 'default',
                                        boxShadow: selectedWords[i] ? '0 10px 20px -5px rgba(0,0,0,0.2)' : 'none',
                                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                        position: 'relative'
                                    }}
                                >
                                    {selectedWords[i] || ''}
                                    {selectedWords[i] === currentVerb.sanskrit && isCorrect && (
                                        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} style={{ position: 'absolute', top: '-10px', right: '-10px', background: '#FFC107', borderRadius: '50%', padding: '4px', color: '#fff' }}>
                                            <Sparkles size={16} />
                                        </motion.div>
                                    )}
                                </div>
                            ))}
                        </div>

                        <AnimatePresence>
                            {isCorrect === false && (
                                <motion.div 
                                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                                    style={{ position: 'absolute', bottom: '20px', color: '#FF5252', fontWeight: 700 }}
                                >
                                    Not quite correct. Tap words to remove them and try again.
                                </motion.div>
                            )}
                            {isCorrect === true && (
                                <motion.div 
                                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                                    style={{ position: 'absolute', bottom: '20px', color: '#4CAF50', fontWeight: 700 }}
                                >
                                    Excellent! You built the sentence.
                                    <AudioPronounceButton text={currentVerb.exampleSanskrit} size={18} title="Listen to the Sanskrit sentence" />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Word Bank */}
                    <div className="flex flex-wrap justify-center gap-4" style={{ padding: '20px' }}>
                        <AnimatePresence>
                            {options.map((option, idx) => (
                                <motion.button
                                    key={`${option}-${idx}`}
                                    layout
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.5 }}
                                    whileHover={{ y: -4, scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                    onClick={() => handleSelectOption(option)}
                                    className="devanagari"
                                    style={{
                                        padding: '16px 32px',
                                        background: 'var(--bg-card)',
                                        border: '2px solid var(--border-soft)',
                                        borderRadius: '20px',
                                        fontSize: '1.8rem',
                                        fontWeight: 800,
                                        color: 'var(--text-main)',
                                        cursor: 'pointer',
                                        boxShadow: '0 8px 16px -8px rgba(0,0,0,0.1)',
                                        transition: 'box-shadow 0.3s ease, border-color 0.3s ease'
                                    }}
                                    onMouseOver={(e) => e.currentTarget.style.borderColor = 'var(--primary)'}
                                    onMouseOut={(e) => e.currentTarget.style.borderColor = 'var(--border-soft)'}
                                >
                                    {option}
                                </motion.button>
                            ))}
                        </AnimatePresence>
                    </div>
                </div>
            )}
        </div>
    );
}
