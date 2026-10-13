import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import { Flame, Star, CheckCircle, AlertCircle, XCircle, Trophy, Sparkles, ArrowRight, RotateCcw } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import AudioPronounceButton from '@/components/AudioPronounceButton';

export default function DailyStreak() {
    const { user } = useAuth();
    const [questions, setQuestions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const [streak, setStreak] = useState(0);
    const [currentDay, setCurrentDay] = useState(1);
    const [currentDayStr, setCurrentDayStr] = useState('');
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

    const [status, setStatus] = useState<'loading' | 'played_today' | 'playing' | 'failed' | 'completed'>('loading');
    const [shake, setShake] = useState(false);
    const [attempts, setAttempts] = useState(0);
    const [showHint, setShowHint] = useState(false);
    const [selectedOption, setSelectedOption] = useState<string | null>(null);

    useEffect(() => {
        const fetchQuestions = async () => {
            try {
                const res = await api.lessons.getDailyQuestions();
                const data = Array.isArray(res) ? res : (res?.data || []);
                setQuestions(data);
                if (data && data.length > 0) {
                    initializeStreak(data);
                } else {
                    setStatus('playing');
                }
            } catch (err) {
                console.error("Failed to load daily questions", err);
                setStatus('playing');
            } finally {
                setLoading(false);
            }
        };
        fetchQuestions();
    }, []);

    const initializeStreak = (allQs: any[]) => {
        if (!allQs || allQs.length === 0) return;

        const storedStreak = parseInt(localStorage.getItem('sanskrit_streak') || '0', 10);
        const storedLastPlayed = localStorage.getItem('sanskrit_last_played');
        const storedCurrentDay = parseInt(localStorage.getItem('sanskrit_current_day') || '1', 10);

        setStreak(storedStreak);
        setCurrentDay(storedCurrentDay);
        
        let qIndex = allQs.findIndex(q => q.day === storedCurrentDay);
        if (qIndex === -1) qIndex = 0;
        setCurrentQuestionIndex(qIndex);

        const today = new Date().toISOString().split('T')[0];
        setCurrentDayStr(today);

        if (storedLastPlayed === today) {
            setStatus('played_today');
        } else if (storedLastPlayed) {
            const yesterdayDate = new Date();
            yesterdayDate.setDate(yesterdayDate.getDate() - 1);
            const yesterday = yesterdayDate.toISOString().split('T')[0];

            if (storedLastPlayed === yesterday) {
                setStatus('playing');
            } else {
                setStreak(0);
                localStorage.setItem('sanskrit_streak', '0');
                setStatus('playing');
            }
        } else {
            setStatus('playing');
        }
    };

    const handleAnswer = (option: string) => {
        if (status !== 'playing') return;
        setSelectedOption(option);

        const currentQ = questions[currentQuestionIndex];
        
        if (option === currentQ.answer) {
            const newStreak = streak + 1;
            setStreak(newStreak);
            localStorage.setItem('sanskrit_streak', newStreak.toString());
            localStorage.setItem('sanskrit_last_played', currentDayStr);

            try {
                if (user?.username) {
                    void api.user.recordDailyActivity(100).catch(() => {
                        // Local streak behavior remains available if the API is offline.
                    });
                }
            } catch {
                // Ignore malformed local profile data; the local streak still works.
            }
            
            const nextDay = Math.min(currentQ.day + 1, questions.length);
            localStorage.setItem('sanskrit_current_day', nextDay.toString());
            
            setTimeout(() => setStatus('completed'), 700);
        } else {
            if (attempts === 0) {
                setAttempts(1);
                setShake(true);
                setTimeout(() => {
                    setShake(false);
                    setSelectedOption(null);
                    setShowHint(true);
                }, 600);
            } else {
                setStreak(0);
                localStorage.setItem('sanskrit_streak', '0');
                localStorage.setItem('sanskrit_last_played', currentDayStr);
                setTimeout(() => setStatus('failed'), 700);
            }
        }
    };

    if (loading) {
        return (
            <div className="daily-loading-card">
                <motion.div 
                    animate={{ scale: [1, 1.15, 1], rotate: [0, 8, -8, 0] }} 
                    transition={{ repeat: Infinity, duration: 1.8 }} 
                    className="loading-icon"
                >
                    <Flame size={48} fill="var(--primary)" />
                </motion.div>
                <div className="loading-text">Preparing Sacred Daily Challenge...</div>
                <style jsx>{`
                    .daily-loading-card {
                        background: var(--bg-card);
                        border-radius: var(--radius-xl);
                        padding: 60px 40px;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        gap: 20px;
                        border: 1px solid var(--border-soft);
                        text-align: center;
                        box-shadow: var(--shadow-sm);
                    }
                    .loading-icon { color: var(--primary); margin: 0 auto; }
                    .loading-text { font-size: 0.88rem; color: var(--text-dim); font-weight: 700; letter-spacing: 2px; text-transform: uppercase; }
                `}</style>
            </div>
        );
    }

    return (
        <LayoutGroup>
            <AnimatePresence mode="wait">
                {status === 'played_today' ? (
                    <motion.div 
                        key="played"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="played-today-card" 
                    >
                        <div className="card-inner">
                            <div className="info-side">
                                <div className="badge-row">
                                    <div className="success-badge">
                                        <CheckCircle size={16} /> Daily Mantra Completed
                                    </div>
                                    <div className="topic-tag">Day {currentDay} Cleared</div>
                                </div>
                                <h3 className="card-title">Sacred Wisdom Absorbed</h3>
                                <p className="card-desc">
                                    Your learning path remains clear. You have completed today's challenge with focus and discipline.
                                </p>
                                <div className="next-time">Next Daily Mantra unlocks tomorrow</div>
                            </div>

                            <div className="stats-side">
                                <div className="streak-orb">
                                    <div className="orb-bg"></div>
                                    <div className="orb-content">
                                        <div className="streak-val">{streak}</div>
                                        <div className="streak-sub">Day Streak</div>
                                        <Flame size={24} fill="var(--primary)" color="var(--primary)" />
                                    </div>
                                </div>
                            </div>
                        </div>
                        <style jsx>{`
                            .played-today-card {
                                background: var(--bg-card);
                                border-radius: var(--radius-xl);
                                border: 1px solid var(--border-soft);
                                overflow: hidden;
                                position: relative;
                                box-shadow: var(--shadow-sm);
                            }
                            .card-inner { padding: 40px; display: flex; flex-direction: column; md-flex-direction: row; gap: 32px; align-items: center; position: relative; z-index: 2; }
                            @media (min-width: 768px) { .card-inner { flex-direction: row; } }
                            .info-side { flex: 1; }
                            .badge-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
                            .success-badge { background: rgba(110, 139, 94, 0.15); color: var(--accent-green); padding: 6px 14px; border-radius: 12px; font-size: 0.82rem; font-weight: 800; display: flex; align-items: center; gap: 8px; }
                            .topic-tag { background: var(--bg-main); color: var(--text-dim); padding: 6px 14px; border-radius: 12px; font-size: 0.82rem; font-weight: 700; border: 1px solid var(--border-soft); }
                            .card-title { font-size: 2rem; margin-bottom: 12px; letter-spacing: -0.5px; }
                            .card-desc { color: var(--text-dim); font-size: 1.05rem; line-height: 1.6; margin-bottom: 20px; }
                            .next-time { color: var(--primary); font-size: 0.82rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }
                            .stats-side { flex-shrink: 0; }
                            .streak-orb { width: 160px; height: 160px; position: relative; display: flex; align-items: center; justify-content: center; }
                            .orb-bg { position: absolute; inset: 0; background: var(--primary); opacity: 0.1; border-radius: 50%; filter: blur(16px); }
                            .orb-content { position: relative; z-index: 2; text-align: center; }
                            .streak-val { font-size: 3.5rem; font-weight: 900; font-family: 'Marcellus', serif; line-height: 1; margin-bottom: -4px; color: var(--text-main); }
                            .streak-sub { font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; color: var(--text-dim); margin-bottom: 6px; }
                        `}</style>
                    </motion.div>
                ) : status === 'completed' ? (
                    <motion.div 
                        key="completed"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="success-overlay-card"
                    >
                        <motion.div 
                            initial={{ y: 15 }} animate={{ y: 0 }}
                            className="success-content"
                        >
                            <div className="trophy-wrap">
                                <Trophy size={54} />
                            </div>
                            <h2 className="success-title">Uttamam! (उत्तमम्)</h2>
                            <p className="success-msg">Your answer is accurate. Your daily streak has reached <strong>{streak} days</strong>.</p>
                            
                            <div className="reward-badges">
                                <div className="reward-pill">+25 Karma Points</div>
                                <div className="reward-pill">Level Progress Boosted</div>
                            </div>
                            
                            <button onClick={() => window.location.reload()} className="dismiss-btn">
                                Continue Learning Journey <ArrowRight size={18} />
                            </button>
                        </motion.div>
                        <style jsx>{`
                            .success-overlay-card {
                                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                                border-radius: var(--radius-xl);
                                padding: 50px 32px;
                                color: white;
                                text-align: center;
                                position: relative;
                                overflow: hidden;
                                box-shadow: 0 16px 40px rgba(16, 185, 129, 0.3);
                            }
                            .success-content { position: relative; z-index: 10; }
                            .trophy-wrap { position: relative; width: 54px; height: 54px; margin: 0 auto 24px auto; color: #fff; }
                            .success-title { font-size: 2.8rem; font-weight: 900; margin-bottom: 10px; color: #fff; font-family: 'Marcellus', serif; }
                            .success-msg { font-size: 1.15rem; opacity: 0.95; margin-bottom: 28px; }
                            .reward-badges { display: flex; justify-content: center; gap: 12px; margin-bottom: 32px; flex-wrap: wrap; }
                            .reward-pill { background: rgba(255,255,255,0.22); backdrop-filter: blur(8px); padding: 8px 20px; border-radius: 12px; font-weight: 800; font-size: 0.85rem; }
                            .dismiss-btn { background: white; color: #047857; padding: 14px 32px; border-radius: 16px; border: none; font-weight: 800; font-size: 0.95rem; cursor: pointer; transition: all 0.3s; display: inline-flex; align-items: center; gap: 8px; }
                            .dismiss-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(0,0,0,0.15); }
                        `}</style>
                    </motion.div>
                ) : status === 'failed' ? (
                    <motion.div 
                        key="failed"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="failure-overlay-card"
                    >
                        <XCircle size={56} style={{ marginBottom: '20px' }} />
                        <h2>Keep Practicing</h2>
                        <p>A momentary lapse in focus. Your streak has been reset, but your knowledge remains intact.</p>
                        <button onClick={() => window.location.reload()} className="dismiss-btn" style={{ background: '#fff', color: '#dc2626' }}>
                            <RotateCcw size={16} /> Try Again
                        </button>
                        <style jsx>{`
                            .failure-overlay-card {
                                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                                border-radius: var(--radius-xl);
                                padding: 50px 32px;
                                color: white;
                                text-align: center;
                                display: flex;
                                flex-direction: column;
                                align-items: center;
                                justify-content: center;
                                box-shadow: 0 16px 40px rgba(239, 68, 68, 0.3);
                            }
                            h2 { font-size: 2.4rem; color: #fff; margin-bottom: 12px; font-family: 'Marcellus', serif; }
                            p { font-size: 1.05rem; opacity: 0.92; max-width: 480px; margin-bottom: 28px; line-height: 1.6; }
                            .dismiss-btn { padding: 14px 32px; border-radius: 16px; border: none; font-weight: 800; font-size: 0.95rem; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
                        `}</style>
                    </motion.div>
                ) : (
                    <motion.div 
                        key="playing"
                        layout
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={shake ? { x: [-10, 10, -10, 10, 0], opacity: 1 } : { x: 0, opacity: 1 }}
                        transition={shake ? { duration: 0.4 } : { duration: 0.5 }}
                        className="quest-card"
                    >
                        <div className="quest-header">
                            <div className="header-meta">
                                <div className="day-badge">Day <strong>{currentDay}</strong> of 50</div>
                                <div className="topic-label"><Sparkles size={14} /> {questions[currentQuestionIndex]?.topic}</div>
                            </div>
                            <div className="header-streak">
                                <Flame size={20} fill="currentColor" />
                                <span>{streak}</span>
                            </div>
                        </div>

                        <div className="quest-body">
                            <div className="flex items-center justify-center gap-2">
                                <h2 className="quest-question">{questions[currentQuestionIndex]?.question}</h2>
                                <AudioPronounceButton text={questions[currentQuestionIndex]?.question || ''} size={20} />
                            </div>

                            <div className="options-grid">
                                {questions[currentQuestionIndex]?.options.map((opt: string, i: number) => {
                                    const isSelected = selectedOption === opt;
                                    return (
                                        <motion.button
                                            key={i}
                                            whileHover={{ y: -3, borderColor: 'var(--primary)' }}
                                            whileTap={{ scale: 0.98 }}
                                            onClick={() => handleAnswer(opt)}
                                            className={`option-btn ${isSelected ? 'selected' : ''}`}
                                            disabled={selectedOption !== null}
                                        >
                                            <div className="option-index">{String.fromCharCode(65 + i)}</div>
                                            <div className="option-text">{opt}</div>
                                            {isSelected && (
                                                <motion.div layoutId="highlight" className="option-glow" />
                                            )}
                                        </motion.button>
                                    );
                                })}
                            </div>

                            <AnimatePresence>
                                {showHint && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="hint-container"
                                    >
                                        <div className="hint-icon">
                                            <AlertCircle size={20} />
                                        </div>
                                        <div className="hint-content">
                                            <div className="hint-label">Divine Guidance</div>
                                            <p className="hint-text">{questions[currentQuestionIndex]?.hint}</p>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        <div className="quest-footer">
                            <div className="progress-bar-wrap">
                                <motion.div 
                                    className="progress-fill"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${(currentDay / 50) * 100}%` }}
                                />
                            </div>
                        </div>

                        <style jsx>{`
                            .quest-card {
                                background: var(--bg-card);
                                border-radius: var(--radius-xl);
                                border: 1px solid var(--border-soft);
                                overflow: hidden;
                                box-shadow: var(--shadow-md);
                            }
                            .quest-header {
                                background: var(--bg-subtle);
                                border-bottom: 1px solid var(--border-soft);
                                padding: 20px 32px;
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                            }
                            .header-meta { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }
                            .day-badge { background: var(--primary-light); color: var(--primary); padding: 5px 14px; border-radius: 10px; font-size: 0.82rem; font-weight: 700; letter-spacing: 0.5px; border: 1px solid rgba(var(--primary-rgb),0.2); }
                            .topic-label { font-size: 0.82rem; font-weight: 700; color: var(--text-dim); display: flex; align-items: center; gap: 6px; text-transform: uppercase; letter-spacing: 1px; }
                            .header-streak { display: flex; align-items: center; gap: 6px; color: #f59e0b; font-weight: 900; font-size: 1.25rem; }
                            
                            .quest-body { padding: 36px 32px; }
                            .quest-question { font-size: 1.65rem; font-weight: 800; color: var(--text-main); margin-bottom: 32px; line-height: 1.4; letter-spacing: -0.4px; }
                            
                            .options-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
                            @media (min-width: 768px) { .options-grid { grid-template-columns: repeat(3, 1fr); } }
                            
                            .option-btn {
                                background: var(--bg-main);
                                border: 1.5px solid var(--border-soft);
                                border-radius: var(--radius-lg);
                                padding: 20px 20px;
                                text-align: left;
                                cursor: pointer;
                                transition: all 0.3s var(--transition);
                                display: flex;
                                flex-direction: column;
                                gap: 12px;
                                position: relative;
                                color: var(--text-main);
                                box-shadow: var(--shadow-sm);
                            }
                            .option-btn:hover:not(.selected) { border-color: var(--primary); transform: translateY(-3px); box-shadow: var(--shadow-md); }
                            .option-btn.selected { 
                                background: var(--primary); 
                                border-color: var(--primary); 
                                color: #ffffff !important;
                                transform: scale(1.01);
                                boxShadow: var(--shadow-glow); 
                            }
                            .option-index { 
                                width: 30px; 
                                height: 30px; 
                                background: rgba(var(--primary-rgb), 0.12); 
                                border-radius: 10px; 
                                color: var(--primary); 
                                font-weight: 800; 
                                font-size: 0.8rem; 
                                display: flex; 
                                align-items: center; 
                                justify-content: center;
                                transition: all 0.3s;
                            }
                            .option-btn.selected .option-index { background: rgba(255,255,255,0.25); color: #fff; }
                            .option-text { font-size: 1.08rem; font-weight: 700; color: inherit; }
                            .option-glow { position: absolute; inset: 0; background: rgba(255,255,255,0.05); border-radius: var(--radius-lg); }

                            .hint-container { margin-top: 28px; display: flex; gap: 16px; background: rgba(245, 158, 11, 0.1); padding: 20px; border-radius: var(--radius-md); border: 1px solid rgba(245, 158, 11, 0.25); }
                            .hint-icon { width: 38px; height: 38px; background: rgba(245, 158, 11, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #d97706; flex-shrink: 0; }
                            .hint-label { font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: #d97706; letter-spacing: 1px; margin-bottom: 3px; }
                            .hint-text { margin: 0; color: var(--text-main); line-height: 1.5; font-size: 0.92rem; font-weight: 500; }
                            
                            .quest-footer { background: var(--bg-main); padding: 0; }
                            .progress-bar-wrap { height: 6px; background: var(--border-soft); width: 100%; position: relative; }
                            .progress-fill { height: 100%; background: var(--primary); position: absolute; left: 0; top: 0; border-radius: 0 3px 3px 0; }
                        `}</style>
                    </motion.div>
                )}
            </AnimatePresence>
        </LayoutGroup>
    );
}
