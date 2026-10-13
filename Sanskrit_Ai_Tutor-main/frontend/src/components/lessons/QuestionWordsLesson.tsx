'use client';
import React, { useState, useEffect, useRef } from 'react';
import {
    ArrowLeft,
    CheckCircle2,
    Sparkles,
    MessageCircle,
    Send,
    RotateCcw,
    HelpCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface QuestionWord {
    id: string;
    sanskrit: string;
    transliteration: string;
    englishMeaning: string;
    exampleSanskrit: string;
    exampleEnglish: string;
    context: string;
}

interface ChatMessage {
    id: string;
    sender: 'ai' | 'user' | 'system';
    sanskrit?: string;
    english?: string;
    blank?: string; // The question word id that fills the blank
    userSentence?: string;
    isCorrect?: boolean;
    filled?: boolean;
    filledWord?: string;
}

// Scenario bank: each has an AI statement, user's incomplete question, and the correct answer
const SCENARIOS = [
    {
        aiSanskrit: 'अहं विद्यालयं गच्छामि।',
        aiEnglish: 'I am going to the school.',
        userTemplate: 'भवान् ______ गच्छति?',
        userEnglish: 'You are going ______?',
        answerId: 'qw_4', // कुत्र (Where)
        hint: 'The AI mentioned a place...',
    },
    {
        aiSanskrit: 'सः रामः अस्ति।',
        aiEnglish: 'He is Ram.',
        userTemplate: 'सः ______ अस्ति?',
        userEnglish: 'Who is he?',
        answerId: 'qw_1', // कः (Who - Masc)
        hint: 'The AI is talking about a male person...',
    },
    {
        aiSanskrit: 'सा सीता अस्ति।',
        aiEnglish: 'She is Sita.',
        userTemplate: 'सा ______ अस्ति?',
        userEnglish: 'Who is she?',
        answerId: 'qw_2', // का (Who - Fem)
        hint: 'The AI is talking about a female person...',
    },
    {
        aiSanskrit: 'तत् पुस्तकम् अस्ति।',
        aiEnglish: 'That is a book.',
        userTemplate: 'तत् ______ अस्ति?',
        userEnglish: 'What is that?',
        answerId: 'qw_3', // किम् (What)
        hint: 'The AI is describing an object...',
    },
    {
        aiSanskrit: 'अहं श्वः आगच्छामि।',
        aiEnglish: 'I will come tomorrow.',
        userTemplate: 'भवान् ______ आगच्छति?',
        userEnglish: 'When are you coming?',
        answerId: 'qw_5', // कदा (When)
        hint: 'The AI mentioned a time...',
    },
    {
        aiSanskrit: 'अहं कुशलम् अस्मि।',
        aiEnglish: 'I am well.',
        userTemplate: 'भवान् ______ अस्ति?',
        userEnglish: 'How are you?',
        answerId: 'qw_6', // कथम् (How)
        hint: 'The AI described a state/manner...',
    },
    {
        aiSanskrit: 'अहं हसामि यतः आनन्दः अस्ति।',
        aiEnglish: 'I am laughing because I am happy.',
        userTemplate: 'त्वं ______ हससि?',
        userEnglish: 'Why are you laughing?',
        answerId: 'qw_7', // किमर्थम् (Why)
        hint: 'The AI gave a reason...',
    },
    {
        aiSanskrit: 'अत्र पञ्च पुस्तकानि सन्ति।',
        aiEnglish: 'There are five books here.',
        userTemplate: 'अत्र ______ पुस्तकानि सन्ति?',
        userEnglish: 'How many books are here?',
        answerId: 'qw_8', // कति (How many)
        hint: 'The AI mentioned a quantity...',
    },
];

export default function QuestionWordsLesson({ onBack }: { onBack: () => void }) {
    const [questionWords, setQuestionWords] = useState<QuestionWord[]>([]);
    const [loading, setLoading] = useState(true);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [currentScenarioIdx, setCurrentScenarioIdx] = useState(0);
    const [score, setScore] = useState(0);
    const [showHint, setShowHint] = useState(false);
    const [shakeWord, setShakeWord] = useState<string | null>(null);
    const [gameComplete, setGameComplete] = useState(false);
    const [gameStarted, setGameStarted] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await api.lessons.getQuestionWords();
                const data = Array.isArray(res) ? res : (res?.data || res || []);
                setQuestionWords(data);
            } catch (error) {
                console.error('Failed to fetch question words', error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const startGame = () => {
        setGameStarted(true);
        setCurrentScenarioIdx(0);
        setScore(0);
        setGameComplete(false);
        setShowHint(false);

        // Welcome message
        const welcomeMsg: ChatMessage = {
            id: 'welcome',
            sender: 'system',
            english: '🕉️ गुरुजी has entered the chat! I will make statements. You must ask the right question using the correct Sanskrit question word.',
        };

        // First AI message
        const scenario = SCENARIOS[0];
        const aiMsg: ChatMessage = {
            id: `ai_0`,
            sender: 'ai',
            sanskrit: scenario.aiSanskrit,
            english: scenario.aiEnglish,
        };
        const userMsg: ChatMessage = {
            id: `user_0`,
            sender: 'user',
            userSentence: scenario.userTemplate,
            english: scenario.userEnglish,
            blank: scenario.answerId,
            filled: false,
        };

        setMessages([welcomeMsg, aiMsg, userMsg]);
    };

    const handleWordSelect = (word: QuestionWord) => {
        if (gameComplete) return;

        const scenario = SCENARIOS[currentScenarioIdx];
        const lastUserMsg = messages.findLast(m => m.sender === 'user' && !m.filled);

        if (!lastUserMsg) return;

        if (word.id === scenario.answerId) {
            // Correct!
            const updatedMessages = messages.map(m =>
                m.id === lastUserMsg.id
                    ? { ...m, filled: true, filledWord: word.sanskrit, isCorrect: true }
                    : m
            );

            const correctFeedback: ChatMessage = {
                id: `feedback_${currentScenarioIdx}`,
                sender: 'system',
                english: `✅ Correct! "${word.sanskrit}" (${word.transliteration}) means "${word.englishMeaning}". ${word.context}`,
            };

            const nextIdx = currentScenarioIdx + 1;

            if (nextIdx >= SCENARIOS.length) {
                // Game complete
                setMessages([...updatedMessages, correctFeedback]);
                setScore(s => s + 1);
                setGameComplete(true);
                setShowHint(false);
                return;
            }

            // Next scenario
            const nextScenario = SCENARIOS[nextIdx];
            const nextAiMsg: ChatMessage = {
                id: `ai_${nextIdx}`,
                sender: 'ai',
                sanskrit: nextScenario.aiSanskrit,
                english: nextScenario.aiEnglish,
            };
            const nextUserMsg: ChatMessage = {
                id: `user_${nextIdx}`,
                sender: 'user',
                userSentence: nextScenario.userTemplate,
                english: nextScenario.userEnglish,
                blank: nextScenario.answerId,
                filled: false,
            };

            setMessages([...updatedMessages, correctFeedback, nextAiMsg, nextUserMsg]);
            setScore(s => s + 1);
            setCurrentScenarioIdx(nextIdx);
            setShowHint(false);
        } else {
            // Wrong answer — shake animation
            setShakeWord(word.id);
            setTimeout(() => setShakeWord(null), 500);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}>
                    <MessageCircle size={48} style={{ color: 'var(--primary)' }} />
                </motion.div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Question Words...</h3>
            </div>
        );
    }

    return (
        <div style={{ padding: '10px', maxWidth: '800px', margin: '0 auto' }}>
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                    padding: '20px 28px',
                    marginBottom: '16px',
                    borderRadius: '24px',
                    background: 'rgba(var(--bg-card-rgb), 0.8)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid var(--border-soft)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px'
                }}
            >
                <div className="flex items-center gap-3">
                    <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
                        <ArrowLeft size={22} />
                    </button>
                    <div>
                        <h1 style={{ fontSize: '1.5rem', fontWeight: 900, margin: 0, color: 'var(--text-main)' }}>
                            प्रश्नपदानि — Question Words
                        </h1>
                        <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem', margin: 0 }}>
                            Ask the right question by choosing the correct word!
                        </p>
                    </div>
                </div>
                {gameStarted && (
                    <div className="flex items-center gap-3">
                        <div style={{ fontWeight: 800, color: 'var(--primary)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Sparkles size={16} /> {score}/{SCENARIOS.length}
                        </div>
                        <button
                            onClick={startGame}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '100px',
                                border: '2px solid var(--primary)',
                                background: 'transparent',
                                color: 'var(--primary)',
                                fontWeight: 800,
                                cursor: 'pointer',
                                fontSize: '0.8rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                            }}
                        >
                            <RotateCcw size={14} /> Restart
                        </button>
                    </div>
                )}
            </motion.div>

            {/* Pre-game: Show all question words as reference cards */}
            {!gameStarted && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    {/* Reference Cards */}
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                        gap: '12px',
                        marginBottom: '24px'
                    }}>
                        {questionWords.map((qw, i) => (
                            <motion.div
                                key={qw.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.08 }}
                                style={{
                                    padding: '20px',
                                    borderRadius: '20px',
                                    background: 'rgba(var(--bg-card-rgb), 0.9)',
                                    border: '1px solid var(--border-soft)',
                                    backdropFilter: 'blur(6px)',
                                }}
                            >
                                <div className="devanagari" style={{ fontSize: '2rem', fontWeight: 900, color: 'var(--primary)', marginBottom: '4px' }}>
                                    {qw.sanskrit}
                                </div>
                                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '2px' }}>
                                    {qw.transliteration} — {qw.englishMeaning}
                                </div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginBottom: '8px' }}>
                                    {qw.context}
                                </div>
                                <div style={{
                                    padding: '10px 14px',
                                    borderRadius: '12px',
                                    background: 'var(--bg-main)',
                                    fontSize: '0.75rem',
                                    lineHeight: 1.6
                                }}>
                                    <div className="devanagari" style={{ color: 'var(--text-main)', fontWeight: 600 }}>
                                        {qw.exampleSanskrit}
                                    </div>
                                    <div style={{ color: 'var(--text-light)', fontStyle: 'italic' }}>
                                        {qw.exampleEnglish}
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>

                    {/* Start Button */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="flex justify-center"
                    >
                        <button
                            onClick={startGame}
                            style={{
                                padding: '18px 48px',
                                borderRadius: '100px',
                                background: 'var(--primary)',
                                color: 'white',
                                fontWeight: 900,
                                fontSize: '1.1rem',
                                border: 'none',
                                cursor: 'pointer',
                                boxShadow: '0 8px 32px rgba(var(--primary-rgb), 0.4)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px'
                            }}
                        >
                            <MessageCircle size={22} /> Start Interrogation Game
                        </button>
                    </motion.div>
                </motion.div>
            )}

            {/* Chat Interface */}
            {gameStarted && !gameComplete && (
                <div style={{
                    borderRadius: '32px',
                    overflow: 'hidden',
                    border: '1px solid var(--border-soft)',
                    background: 'rgba(var(--bg-card-rgb), 0.4)',
                    backdropFilter: 'blur(8px)',
                    display: 'flex',
                    flexDirection: 'column',
                    height: '580px',
                }}>
                    {/* Chat header bar */}
                    <div style={{
                        padding: '16px 24px',
                        borderBottom: '1px solid var(--border-soft)',
                        background: 'rgba(var(--bg-card-rgb), 0.9)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px'
                    }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, #FF6B35, #F7931E)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontWeight: 900,
                            fontSize: '1.1rem'
                        }}>
                            गु
                        </div>
                        <div>
                            <div style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--text-main)' }}>गुरुजी (Guruji)</div>
                            <div style={{ fontSize: '0.7rem', color: '#4CAF50' }}>● online</div>
                        </div>
                    </div>

                    {/* Messages area */}
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '20px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px',
                    }}>
                        <AnimatePresence>
                            {messages.map(msg => (
                                <motion.div
                                    key={msg.id}
                                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    transition={{ duration: 0.3 }}
                                    style={{
                                        display: 'flex',
                                        justifyContent: msg.sender === 'ai' ? 'flex-start' : msg.sender === 'user' ? 'flex-end' : 'center',
                                    }}
                                >
                                    {msg.sender === 'system' ? (
                                        <div style={{
                                            padding: '10px 18px',
                                            borderRadius: '16px',
                                            background: 'rgba(var(--primary-rgb), 0.08)',
                                            border: '1px solid rgba(var(--primary-rgb), 0.15)',
                                            fontSize: '0.78rem',
                                            color: 'var(--text-dim)',
                                            textAlign: 'center',
                                            maxWidth: '90%',
                                            lineHeight: 1.5
                                        }}>
                                            {msg.english}
                                        </div>
                                    ) : msg.sender === 'ai' ? (
                                        <div style={{
                                            maxWidth: '75%',
                                            padding: '14px 20px',
                                            borderRadius: '20px 20px 20px 6px',
                                            background: 'rgba(var(--bg-card-rgb), 0.95)',
                                            border: '1px solid var(--border-soft)',
                                            boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
                                        }}>
                                            <div className="devanagari" style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px', lineHeight: 1.4 }}>
                                                {msg.sanskrit}
                                            </div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', fontStyle: 'italic' }}>
                                                {msg.english}
                                            </div>
                                        </div>
                                    ) : (
                                        /* User message bubble */
                                        <div style={{
                                            maxWidth: '75%',
                                            padding: '14px 20px',
                                            borderRadius: '20px 20px 6px 20px',
                                            background: msg.filled
                                                ? (msg.isCorrect ? 'rgba(76, 175, 80, 0.12)' : 'rgba(255, 82, 82, 0.12)')
                                                : 'rgba(var(--primary-rgb), 0.08)',
                                            border: `1px solid ${
                                                msg.filled
                                                    ? (msg.isCorrect ? 'rgba(76, 175, 80, 0.3)' : 'rgba(255, 82, 82, 0.3)')
                                                    : 'rgba(var(--primary-rgb), 0.2)'
                                            }`,
                                            boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
                                        }}>
                                            <div className="devanagari" style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px', lineHeight: 1.4 }}>
                                                {msg.filled
                                                    ? msg.userSentence?.replace('______', msg.filledWord || '')
                                                    : msg.userSentence?.split('______').map((part, idx, arr) => (
                                                        <React.Fragment key={idx}>
                                                            {part}
                                                            {idx < arr.length - 1 && (
                                                                <motion.span
                                                                    animate={{ opacity: [0.4, 1, 0.4] }}
                                                                    transition={{ repeat: Infinity, duration: 1.5 }}
                                                                    style={{
                                                                        display: 'inline-block',
                                                                        padding: '2px 16px',
                                                                        margin: '0 4px',
                                                                        borderRadius: '8px',
                                                                        border: '2px dashed var(--primary)',
                                                                        background: 'rgba(var(--primary-rgb), 0.05)',
                                                                        minWidth: '60px',
                                                                        textAlign: 'center',
                                                                        color: 'var(--primary)',
                                                                        fontSize: '0.9rem',
                                                                        verticalAlign: 'middle'
                                                                    }}
                                                                >
                                                                    ?
                                                                </motion.span>
                                                            )}
                                                        </React.Fragment>
                                                    ))
                                                }
                                            </div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', fontStyle: 'italic' }}>
                                                {msg.english}
                                            </div>
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                        </AnimatePresence>
                        <div ref={chatEndRef} />
                    </div>

                    {/* Hint bar */}
                    <AnimatePresence>
                        {showHint && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                style={{
                                    padding: '10px 24px',
                                    background: 'rgba(255, 193, 7, 0.1)',
                                    borderTop: '1px solid rgba(255, 193, 7, 0.2)',
                                    fontSize: '0.8rem',
                                    color: '#F59E0B',
                                    fontWeight: 600,
                                    textAlign: 'center'
                                }}
                            >
                                💡 {SCENARIOS[currentScenarioIdx]?.hint}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Answer pills tray */}
                    <div style={{
                        padding: '16px 20px',
                        borderTop: '1px solid var(--border-soft)',
                        background: 'rgba(var(--bg-card-rgb), 0.95)',
                    }}>
                        <div className="flex items-center justify-between" style={{ marginBottom: '10px' }}>
                            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-light)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                                Choose a question word:
                            </span>
                            <button
                                onClick={() => setShowHint(h => !h)}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    color: '#F59E0B',
                                    cursor: 'pointer',
                                    fontSize: '0.75rem',
                                    fontWeight: 700,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px'
                                }}
                            >
                                <HelpCircle size={14} /> Hint
                            </button>
                        </div>
                        <div style={{
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: '8px',
                            justifyContent: 'center'
                        }}>
                            {questionWords.map(qw => (
                                <motion.button
                                    key={qw.id}
                                    whileHover={{ scale: 1.08, y: -3 }}
                                    whileTap={{ scale: 0.95 }}
                                    animate={shakeWord === qw.id ? { x: [-6, 6, -6, 6, 0], transition: { duration: 0.4 } } : {}}
                                    onClick={() => handleWordSelect(qw)}
                                    style={{
                                        padding: '10px 18px',
                                        borderRadius: '100px',
                                        borderWidth: '2px',
                                        borderStyle: 'solid',
                                        borderColor: shakeWord === qw.id ? '#FF5252' : 'var(--border-soft)',
                                        background: shakeWord === qw.id
                                            ? 'rgba(255, 82, 82, 0.1)'
                                            : 'rgba(var(--bg-card-rgb), 0.9)',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        gap: '2px',
                                        transition: 'background 0.2s, border 0.2s',
                                    }}
                                >
                                    <span className="devanagari" style={{ fontSize: '1.1rem', fontWeight: 900, color: 'var(--primary)' }}>
                                        {qw.sanskrit}
                                    </span>
                                    <span style={{ fontSize: '0.55rem', color: 'var(--text-light)', fontWeight: 600 }}>
                                        {qw.englishMeaning}
                                    </span>
                                </motion.button>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Game Complete */}
            {gameComplete && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="zen-card text-center"
                    style={{ padding: '60px', borderRadius: '32px' }}
                >
                    <div className="flex justify-center mb-6">
                        <div style={{
                            background: 'linear-gradient(135deg, #FF6B35, #F7931E)',
                            color: 'white',
                            padding: '28px',
                            borderRadius: '50%',
                            boxShadow: '0 8px 32px rgba(255, 107, 53, 0.4)'
                        }}>
                            <Sparkles size={56} />
                        </div>
                    </div>
                    <h2 className="devanagari" style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '8px', color: 'var(--text-main)' }}>
                        शाबाश!
                    </h2>
                    <h3 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '16px', color: 'var(--text-main)' }}>
                        Interrogation Master!
                    </h3>
                    <p style={{ fontSize: '1.1rem', color: 'var(--text-dim)', marginBottom: '32px', lineHeight: 1.6 }}>
                        You correctly used <b>{score}</b> of {SCENARIOS.length} question words.<br />
                        Now you can ask questions in Sanskrit!
                    </p>
                    <div className="flex justify-center gap-4" style={{ flexWrap: 'wrap' }}>
                        <button
                            onClick={startGame}
                            style={{
                                padding: '14px 32px',
                                borderRadius: '100px',
                                border: '2px solid var(--primary)',
                                background: 'transparent',
                                color: 'var(--primary)',
                                fontWeight: 800,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}
                        >
                            <RotateCcw size={18} /> Play Again
                        </button>
                        <button
                            onClick={onBack}
                            style={{
                                padding: '14px 32px',
                                borderRadius: '100px',
                                background: 'var(--primary)',
                                color: 'white',
                                fontWeight: 800,
                                cursor: 'pointer',
                                border: 'none',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                boxShadow: '0 8px 24px rgba(var(--primary-rgb), 0.3)'
                            }}
                        >
                            Finish Lesson <CheckCircle2 size={18} />
                        </button>
                    </div>
                </motion.div>
            )}
        </div>
    );
}
