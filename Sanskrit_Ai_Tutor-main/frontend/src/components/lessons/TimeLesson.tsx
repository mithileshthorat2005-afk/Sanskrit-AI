'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    ArrowLeft,
    CheckCircle2,
    Sparkles,
    Clock,
    Calendar,
    RotateCcw,
    ChevronRight,
    Sun,
    Moon
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

interface TimeItem {
    id: string;
    category: string;
    sanskrit: string;
    transliteration: string;
    englishMeaning: string;
    rule?: string;
}

// Hour name prefixes for dynamic clock
const HOUR_PREFIXES = ['', 'एक', 'द्वि', 'त्रि', 'चतुर्', 'पञ्च', 'षड्', 'सप्त', 'अष्ट', 'नव', 'दश', 'एकादश', 'द्वादश'];
const HOUR_TRANSLIT = ['', 'Eka', 'Dvi', 'Tri', 'Catur', 'Pañca', 'Ṣaḍ', 'Sapta', 'Aṣṭa', 'Nava', 'Daśa', 'Ekādaśa', 'Dvādaśa'];

const DAY_COLORS: Record<string, { from: string; to: string; glow: string }> = {
    'Sunday':    { from: '#FF6B35', to: '#F7931E', glow: 'rgba(255, 107, 53, 0.3)' },
    'Monday':    { from: '#6366F1', to: '#818CF8', glow: 'rgba(99, 102, 241, 0.3)' },
    'Tuesday':   { from: '#EF4444', to: '#F87171', glow: 'rgba(239, 68, 68, 0.3)' },
    'Wednesday': { from: '#10B981', to: '#34D399', glow: 'rgba(16, 185, 129, 0.3)' },
    'Thursday':  { from: '#F59E0B', to: '#FBBF24', glow: 'rgba(245, 158, 11, 0.3)' },
    'Friday':    { from: '#EC4899', to: '#F472B6', glow: 'rgba(236, 72, 153, 0.3)' },
    'Saturday':  { from: '#8B5CF6', to: '#A78BFA', glow: 'rgba(139, 92, 246, 0.3)' },
};

export default function TimeLesson({ onBack }: { onBack: () => void }) {
    const [timeData, setTimeData] = useState<TimeItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'clock' | 'days'>('clock');

    // Clock state
    const [clockHour, setClockHour] = useState(3);
    const [clockMinute, setClockMinute] = useState(0);
    const [isDragging, setIsDragging] = useState(false);
    const clockRef = useRef<SVGSVGElement>(null);

    // Days game state
    const [targetDayIdx, setTargetDayIdx] = useState(2); // Tuesday
    const [placedToday, setPlacedToday] = useState<number | null>(null);
    const [placedYesterday, setPlacedYesterday] = useState<number | null>(null);
    const [placedTomorrow, setPlacedTomorrow] = useState<number | null>(null);
    const [dayPhase, setDayPhase] = useState<'today' | 'yesterday' | 'tomorrow' | 'complete'>('today');
    const [dayScore, setDayScore] = useState(0);
    const [dayRound, setDayRound] = useState(0);
    const [showDayFeedback, setShowDayFeedback] = useState<'correct' | 'wrong' | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await api.lessons.getTimeAndDays();
                const data = Array.isArray(res) ? res : (res?.data || res || []);
                setTimeData(data);
            } catch (error) {
                console.error('Failed to fetch time data', error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    // ========== CLOCK LOGIC ==========
    const getSanskritTime = useCallback((hour: number, minute: number) => {
        const h = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
        const prefix = HOUR_PREFIXES[h] || '';
        const translit = HOUR_TRANSLIT[h] || '';
        
        if (minute === 0) {
            return {
                sanskrit: `${prefix}वादनम्`,
                transliteration: `${translit}-vādanam`,
                english: `${h}:00 O'clock`,
                rule: ''
            };
        } else if (minute === 15) {
            return {
                sanskrit: `सपाद-${prefix}वादनम्`,
                transliteration: `Sapāda-${translit.toLowerCase()}vādanam`,
                english: `${h}:15 (Quarter past ${h})`,
                rule: "सपाद (Sapāda) = With a quarter"
            };
        } else if (minute === 30) {
            return {
                sanskrit: `सार्ध-${prefix}वादनम्`,
                transliteration: `Sārdha-${translit.toLowerCase()}vādanam`,
                english: `${h}:30 (Half past ${h})`,
                rule: "सार्ध (Sārdha) = With a half"
            };
        } else if (minute === 45) {
            const nextH = h === 12 ? 1 : h + 1;
            const nextPrefix = HOUR_PREFIXES[nextH] || '';
            const nextTranslit = HOUR_TRANSLIT[nextH] || '';
            return {
                sanskrit: `पादोन-${nextPrefix}वादनम्`,
                transliteration: `Pādona-${nextTranslit.toLowerCase()}vādanam`,
                english: `${h}:45 (Quarter to ${nextH})`,
                rule: "पादोन (Pādona) = Minus a quarter (use NEXT hour)"
            };
        }
        // For intermediate minutes, show the closest quarter
        return {
            sanskrit: `${prefix}वादनम्`,
            transliteration: `${translit}-vādanam`,
            english: `~${h}:${minute.toString().padStart(2, '0')}`,
            rule: 'Drag to :00, :15, :30, or :45 for Sanskrit names'
        };
    }, []);

    const handleClockInteraction = useCallback((clientX: number, clientY: number) => {
        if (!clockRef.current) return;
        const rect = clockRef.current.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = clientX - cx;
        const dy = clientY - cy;
        let angle = Math.atan2(dy, dx) * (180 / Math.PI) + 90;
        if (angle < 0) angle += 360;

        // Snap to quarter-hour increments (0, 15, 30, 45)
        const rawMinute = Math.round(angle / 6) % 60;
        const snappedMinute = Math.round(rawMinute / 15) * 15;
        const minute = snappedMinute === 60 ? 0 : snappedMinute;

        // Determine hour from angle (for the hour hand which moves slower)
        const newHour = Math.floor(angle / 30) || 12;

        setClockMinute(minute);
        setClockHour(minute === 0 && snappedMinute === 60 ? (newHour % 12) + 1 : newHour > 12 ? newHour - 12 : newHour === 0 ? 12 : newHour);
    }, []);

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        setIsDragging(true);
        handleClockInteraction(e.clientX, e.clientY);
    }, [handleClockInteraction]);

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (isDragging) handleClockInteraction(e.clientX, e.clientY);
    }, [isDragging, handleClockInteraction]);

    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    const handleTouchStart = useCallback((e: React.TouchEvent) => {
        setIsDragging(true);
        const touch = e.touches[0];
        handleClockInteraction(touch.clientX, touch.clientY);
    }, [handleClockInteraction]);

    const handleTouchMove = useCallback((e: React.TouchEvent) => {
        if (isDragging) {
            const touch = e.touches[0];
            handleClockInteraction(touch.clientX, touch.clientY);
        }
    }, [isDragging, handleClockInteraction]);

    // Clock hand angles
    const minuteAngle = clockMinute * 6;
    const hourAngle = (clockHour % 12) * 30 + clockMinute * 0.5;
    const currentTime = getSanskritTime(clockHour, clockMinute);

    // ========== DAYS LOGIC ==========
    const days = timeData.filter(d => d.category === 'Days');
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

    const startNewDayRound = useCallback(() => {
        const newTarget = Math.floor(Math.random() * 7);
        setTargetDayIdx(newTarget);
        setPlacedToday(null);
        setPlacedYesterday(null);
        setPlacedTomorrow(null);
        setDayPhase('today');
        setShowDayFeedback(null);
    }, []);

    const handleDaySlotClick = useCallback((slotIdx: number) => {
        if (dayPhase === 'today') {
            if (slotIdx === targetDayIdx) {
                setPlacedToday(slotIdx);
                setDayPhase('yesterday');
                setShowDayFeedback('correct');
                setTimeout(() => setShowDayFeedback(null), 800);
            } else {
                setShowDayFeedback('wrong');
                setTimeout(() => setShowDayFeedback(null), 600);
            }
        } else if (dayPhase === 'yesterday') {
            const expectedYesterday = (targetDayIdx - 1 + 7) % 7;
            if (slotIdx === expectedYesterday) {
                setPlacedYesterday(slotIdx);
                setDayPhase('tomorrow');
                setShowDayFeedback('correct');
                setTimeout(() => setShowDayFeedback(null), 800);
            } else {
                setShowDayFeedback('wrong');
                setTimeout(() => setShowDayFeedback(null), 600);
            }
        } else if (dayPhase === 'tomorrow') {
            const expectedTomorrow = (targetDayIdx + 1) % 7;
            if (slotIdx === expectedTomorrow) {
                setPlacedTomorrow(slotIdx);
                setDayPhase('complete');
                setDayScore(s => s + 1);
                setDayRound(r => r + 1);
                setShowDayFeedback('correct');
                setTimeout(() => setShowDayFeedback(null), 800);
            } else {
                setShowDayFeedback('wrong');
                setTimeout(() => setShowDayFeedback(null), 600);
            }
        }
    }, [dayPhase, targetDayIdx]);

    const relativeWords = timeData.filter(d => d.category === 'Relative Time');
    const todayWord = relativeWords.find(w => w.englishMeaning === 'Today');
    const yesterdayWord = relativeWords.find(w => w.englishMeaning === 'Yesterday');
    const tomorrowWord = relativeWords.find(w => w.englishMeaning === 'Tomorrow');

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center p-8 gap-4" style={{ minHeight: '60vh' }}>
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}>
                    <Clock size={48} style={{ color: 'var(--primary)' }} />
                </motion.div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Loading Time & Days...</h3>
            </div>
        );
    }

    return (
        <div style={{ padding: '10px', maxWidth: '900px', margin: '0 auto' }}>
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
                    borderWidth: '1px',
                    borderStyle: 'solid',
                    borderColor: 'var(--border-soft)',
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
                            समयः वासरः च — Time & Days
                        </h1>
                        <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem', margin: 0 }}>
                            Drag the clock hands and master the weekdays!
                        </p>
                    </div>
                </div>
            </motion.div>

            {/* Tab Switcher */}
            <div className="flex justify-center" style={{ marginBottom: '20px', gap: '8px' }}>
                {[
                    { key: 'clock' as const, label: 'Interactive Clock', icon: <Clock size={16} /> },
                    { key: 'days' as const, label: 'Days Puzzle', icon: <Calendar size={16} /> },
                ].map(tab => (
                    <motion.button
                        key={tab.key}
                        whileHover={{ scale: 1.04 }}
                        whileTap={{ scale: 0.96 }}
                        onClick={() => setActiveTab(tab.key)}
                        style={{
                            padding: '12px 28px',
                            borderRadius: '100px',
                            borderWidth: '2px',
                            borderStyle: 'solid',
                            borderColor: activeTab === tab.key ? 'var(--primary)' : 'var(--border-soft)',
                            background: activeTab === tab.key ? 'var(--primary)' : 'transparent',
                            color: activeTab === tab.key ? '#fff' : 'var(--text-dim)',
                            fontWeight: 800,
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            transition: 'all 0.3s',
                            boxShadow: activeTab === tab.key ? '0 8px 24px rgba(var(--primary-rgb), 0.3)' : 'none',
                        }}
                    >
                        {tab.icon} {tab.label}
                    </motion.button>
                ))}
            </div>

            {/* ========== PART 1: INTERACTIVE CLOCK ========== */}
            <AnimatePresence mode="wait">
                {activeTab === 'clock' && (
                    <motion.div
                        key="clock"
                        initial={{ opacity: 0, x: -30 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 30 }}
                        transition={{ duration: 0.3 }}
                    >
                        <div style={{
                            borderRadius: '32px',
                            background: 'rgba(var(--bg-card-rgb), 0.6)',
                            backdropFilter: 'blur(12px)',
                            borderWidth: '1px',
                            borderStyle: 'solid',
                            borderColor: 'var(--border-soft)',
                            padding: '40px 20px',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            gap: '32px',
                        }}>
                            {/* Instruction */}
                            <div style={{ textAlign: 'center' }}>
                                <div className="devanagari" style={{ fontSize: '1.8rem', fontWeight: 900, color: 'var(--primary)', marginBottom: '4px' }}>
                                    कः समयः?
                                </div>
                                <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)', fontWeight: 600 }}>
                                    Drag the clock to set the time — watch the Sanskrit update live!
                                </div>
                            </div>

                            {/* SVG Clock */}
                            <div style={{ position: 'relative', userSelect: 'none', touchAction: 'none' }}>
                                <svg
                                    ref={clockRef}
                                    width="280"
                                    height="280"
                                    viewBox="0 0 280 280"
                                    onMouseDown={handleMouseDown}
                                    onMouseMove={handleMouseMove}
                                    onMouseUp={handleMouseUp}
                                    onMouseLeave={handleMouseUp}
                                    onTouchStart={handleTouchStart}
                                    onTouchMove={handleTouchMove}
                                    onTouchEnd={handleMouseUp}
                                    style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
                                >
                                    {/* Clock face */}
                                    <defs>
                                        <radialGradient id="clockGrad" cx="50%" cy="50%" r="50%">
                                            <stop offset="0%" stopColor="rgba(var(--bg-card-rgb), 1)" />
                                            <stop offset="100%" stopColor="rgba(var(--bg-main-rgb, 20, 20, 30), 1)" />
                                        </radialGradient>
                                        <filter id="clockShadow">
                                            <feDropShadow dx="0" dy="4" stdDeviation="8" floodOpacity="0.15" />
                                        </filter>
                                    </defs>

                                    {/* Outer ring */}
                                    <circle cx="140" cy="140" r="135" fill="none" stroke="var(--border-soft)" strokeWidth="2" />
                                    <circle cx="140" cy="140" r="130" fill="var(--bg-card)" filter="url(#clockShadow)" />

                                    {/* Hour markers */}
                                    {Array.from({ length: 12 }).map((_, i) => {
                                        const angle = ((i + 1) * 30 - 90) * (Math.PI / 180);
                                        const x1 = 140 + 112 * Math.cos(angle);
                                        const y1 = 140 + 112 * Math.sin(angle);
                                        const x2 = 140 + 122 * Math.cos(angle);
                                        const y2 = 140 + 122 * Math.sin(angle);
                                        const tx = 140 + 98 * Math.cos(angle);
                                        const ty = 140 + 98 * Math.sin(angle);
                                        return (
                                            <g key={i}>
                                                <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--text-dim)" strokeWidth="2.5" strokeLinecap="round" />
                                                <text x={tx} y={ty} textAnchor="middle" dominantBaseline="central" fill="var(--text-main)" fontSize="14" fontWeight="800">
                                                    {i + 1}
                                                </text>
                                            </g>
                                        );
                                    })}

                                    {/* Minute tick marks */}
                                    {Array.from({ length: 60 }).map((_, i) => {
                                        if (i % 5 === 0) return null;
                                        const angle = (i * 6 - 90) * (Math.PI / 180);
                                        const x1 = 140 + 118 * Math.cos(angle);
                                        const y1 = 140 + 118 * Math.sin(angle);
                                        const x2 = 140 + 122 * Math.cos(angle);
                                        const y2 = 140 + 122 * Math.sin(angle);
                                        return (
                                            <line key={`m${i}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--border-soft)" strokeWidth="1" />
                                        );
                                    })}

                                    {/* Quarter highlights (:15, :30, :45, :00) */}
                                    {[0, 15, 30, 45].map(m => {
                                        const angle = (m * 6 - 90) * (Math.PI / 180);
                                        const cx2 = 140 + 124 * Math.cos(angle);
                                        const cy2 = 140 + 124 * Math.sin(angle);
                                        const isActive = clockMinute === m;
                                        return (
                                            <circle key={`q${m}`} cx={cx2} cy={cy2} r={isActive ? 5 : 3} fill={isActive ? 'var(--primary)' : 'var(--text-light)'} opacity={isActive ? 1 : 0.4} />
                                        );
                                    })}

                                    {/* Hour hand */}
                                    <line
                                        x1="140" y1="140"
                                        x2={140 + 60 * Math.cos((hourAngle - 90) * Math.PI / 180)}
                                        y2={140 + 60 * Math.sin((hourAngle - 90) * Math.PI / 180)}
                                        stroke="var(--text-main)"
                                        strokeWidth="5"
                                        strokeLinecap="round"
                                    />

                                    {/* Minute hand */}
                                    <line
                                        x1="140" y1="140"
                                        x2={140 + 90 * Math.cos((minuteAngle - 90) * Math.PI / 180)}
                                        y2={140 + 90 * Math.sin((minuteAngle - 90) * Math.PI / 180)}
                                        stroke="var(--primary)"
                                        strokeWidth="3"
                                        strokeLinecap="round"
                                    />

                                    {/* Center dot */}
                                    <circle cx="140" cy="140" r="6" fill="var(--primary)" />
                                    <circle cx="140" cy="140" r="3" fill="var(--bg-card)" />
                                </svg>

                                {/* AM/PM indicator */}
                                <div style={{
                                    position: 'absolute',
                                    bottom: '-10px',
                                    left: '50%',
                                    transform: 'translateX(-50%)',
                                    display: 'flex',
                                    gap: '4px',
                                }}>
                                    <div style={{
                                        padding: '4px 12px',
                                        borderRadius: '8px',
                                        background: 'rgba(var(--primary-rgb), 0.1)',
                                        fontSize: '0.7rem',
                                        fontWeight: 800,
                                        color: 'var(--primary)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                    }}>
                                        <Sun size={12} /> / <Moon size={12} />
                                    </div>
                                </div>
                            </div>

                            {/* Sanskrit Time Display */}
                            <motion.div
                                key={`${clockHour}-${clockMinute}`}
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ duration: 0.25 }}
                                style={{
                                    textAlign: 'center',
                                    padding: '28px 40px',
                                    borderRadius: '24px',
                                    background: 'rgba(var(--primary-rgb), 0.06)',
                                    borderWidth: '1px',
                                    borderStyle: 'solid',
                                    borderColor: 'rgba(var(--primary-rgb), 0.15)',
                                    width: '100%',
                                    maxWidth: '480px'
                                }}
                            >
                                <div className="devanagari" style={{ fontSize: '2.2rem', fontWeight: 900, color: 'var(--primary)', marginBottom: '6px', lineHeight: 1.3 }}>
                                    {currentTime.sanskrit}
                                </div>
                                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>
                                    {currentTime.transliteration}
                                </div>
                                <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)' }}>
                                    {currentTime.english}
                                </div>
                                {currentTime.rule && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 5 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        style={{
                                            marginTop: '12px',
                                            padding: '8px 16px',
                                            borderRadius: '12px',
                                            background: 'rgba(245, 158, 11, 0.1)',
                                            fontSize: '0.78rem',
                                            fontWeight: 700,
                                            color: '#F59E0B',
                                        }}
                                    >
                                        📐 {currentTime.rule}
                                    </motion.div>
                                )}
                            </motion.div>

                            {/* Quick-set buttons */}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
                                {[
                                    { h: 1, m: 0, label: '1:00' },
                                    { h: 3, m: 15, label: '3:15' },
                                    { h: 6, m: 30, label: '6:30' },
                                    { h: 9, m: 45, label: '9:45' },
                                    { h: 12, m: 0, label: '12:00' },
                                ].map(preset => (
                                    <motion.button
                                        key={preset.label}
                                        whileHover={{ scale: 1.08 }}
                                        whileTap={{ scale: 0.94 }}
                                        onClick={() => { setClockHour(preset.h); setClockMinute(preset.m); }}
                                        style={{
                                            padding: '8px 18px',
                                            borderRadius: '100px',
                                            borderWidth: '1px',
                                            borderStyle: 'solid',
                                            borderColor: (clockHour === preset.h && clockMinute === preset.m) ? 'var(--primary)' : 'var(--border-soft)',
                                            background: (clockHour === preset.h && clockMinute === preset.m) ? 'rgba(var(--primary-rgb), 0.1)' : 'transparent',
                                            color: (clockHour === preset.h && clockMinute === preset.m) ? 'var(--primary)' : 'var(--text-dim)',
                                            fontWeight: 700,
                                            cursor: 'pointer',
                                            fontSize: '0.8rem',
                                        }}
                                    >
                                        {preset.label}
                                    </motion.button>
                                ))}
                            </div>

                            {/* Fractions reference cards */}
                            <div style={{ width: '100%', maxWidth: '560px' }}>
                                <h3 style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-light)', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '12px', textAlign: 'center' }}>
                                    Time Fraction Rules
                                </h3>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                                    {timeData.filter(d => d.category === 'Fractions').map(frac => (
                                        <motion.div
                                            key={frac.id}
                                            whileHover={{ y: -3 }}
                                            style={{
                                                padding: '14px 12px',
                                                borderRadius: '16px',
                                                background: 'rgba(var(--bg-card-rgb), 0.9)',
                                                borderWidth: '1px',
                                                borderStyle: 'solid',
                                                borderColor: 'var(--border-soft)',
                                                textAlign: 'center'
                                            }}
                                        >
                                            <div className="devanagari" style={{ fontSize: '0.95rem', fontWeight: 900, color: 'var(--primary)', marginBottom: '4px' }}>
                                                {frac.sanskrit}
                                            </div>
                                            <div style={{ fontSize: '0.6rem', fontWeight: 600, color: 'var(--text-main)' }}>
                                                {frac.englishMeaning}
                                            </div>
                                            {frac.rule && (
                                                <div style={{ fontSize: '0.55rem', color: 'var(--text-light)', marginTop: '4px', fontStyle: 'italic' }}>
                                                    {frac.rule}
                                                </div>
                                            )}
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}

                {/* ========== PART 2: DAYS TIMELINE PUZZLE ========== */}
                {activeTab === 'days' && (
                    <motion.div
                        key="days"
                        initial={{ opacity: 0, x: 30 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -30 }}
                        transition={{ duration: 0.3 }}
                    >
                        <div style={{
                            borderRadius: '32px',
                            background: 'rgba(var(--bg-card-rgb), 0.6)',
                            backdropFilter: 'blur(12px)',
                            borderWidth: '1px',
                            borderStyle: 'solid',
                            borderColor: 'var(--border-soft)',
                            padding: '40px 20px',
                        }}>
                            {/* Score & Round */}
                            <div className="flex justify-between items-center" style={{ marginBottom: '20px', padding: '0 10px' }}>
                                <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--text-light)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                                    Round {dayRound + 1}
                                </div>
                                <div style={{ fontWeight: 800, color: 'var(--primary)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <Sparkles size={16} /> {dayScore} correct
                                </div>
                            </div>

                            {/* Instruction */}
                            <motion.div
                                key={dayPhase}
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                style={{
                                    textAlign: 'center',
                                    marginBottom: '24px',
                                    padding: '16px 24px',
                                    borderRadius: '16px',
                                    background: 'rgba(var(--primary-rgb), 0.06)',
                                    borderWidth: '1px',
                                    borderStyle: 'solid',
                                    borderColor: 'rgba(var(--primary-rgb), 0.12)',
                                }}
                            >
                                {dayPhase === 'today' && (
                                    <div>
                                        <span className="devanagari" style={{ fontSize: '1.4rem', fontWeight: 900, color: 'var(--primary)' }}>
                                            {todayWord?.sanskrit || 'अद्य'} = Today
                                        </span>
                                        <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                                            Tap {dayNames[targetDayIdx]} to place <b>"Today"</b>
                                        </div>
                                    </div>
                                )}
                                {dayPhase === 'yesterday' && (
                                    <div>
                                        <span className="devanagari" style={{ fontSize: '1.4rem', fontWeight: 900, color: '#F59E0B' }}>
                                            {yesterdayWord?.sanskrit || 'ह्यः'} = Yesterday
                                        </span>
                                        <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                                            If today is {dayNames[targetDayIdx]}, tap <b>Yesterday</b>
                                        </div>
                                    </div>
                                )}
                                {dayPhase === 'tomorrow' && (
                                    <div>
                                        <span className="devanagari" style={{ fontSize: '1.4rem', fontWeight: 900, color: '#10B981' }}>
                                            {tomorrowWord?.sanskrit || 'श्वः'} = Tomorrow
                                        </span>
                                        <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                                            If today is {dayNames[targetDayIdx]}, tap <b>Tomorrow</b>
                                        </div>
                                    </div>
                                )}
                                {dayPhase === 'complete' && (
                                    <div>
                                        <span style={{ fontSize: '1.4rem', fontWeight: 900, color: '#4CAF50' }}>
                                            ✅ शाबाश! Perfect!
                                        </span>
                                        <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                                            All three placed correctly!
                                        </div>
                                    </div>
                                )}
                            </motion.div>

                            {/* Feedback flash */}
                            <AnimatePresence>
                                {showDayFeedback && (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.8 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.8 }}
                                        style={{
                                            textAlign: 'center',
                                            marginBottom: '16px',
                                            fontWeight: 900,
                                            fontSize: '1.2rem',
                                            color: showDayFeedback === 'correct' ? '#4CAF50' : '#FF5252'
                                        }}
                                    >
                                        {showDayFeedback === 'correct' ? '✓ Correct!' : '✗ Try again!'}
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Days Calendar Strip */}
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(7, 1fr)',
                                gap: '6px',
                                marginBottom: '32px',
                                padding: '0 4px'
                            }}>
                                {dayNames.map((name, idx) => {
                                    const dayItem = days[idx];
                                    const colors = DAY_COLORS[name] || { from: '#888', to: '#aaa', glow: 'rgba(0,0,0,0.1)' };
                                    const isToday = placedToday === idx;
                                    const isYesterday = placedYesterday === idx;
                                    const isTomorrow = placedTomorrow === idx;
                                    const isHighlighted = dayPhase === 'today' && idx === targetDayIdx;
                                    const isPlaced = isToday || isYesterday || isTomorrow;
                                    const isClickable = dayPhase !== 'complete';

                                    return (
                                        <motion.div
                                            key={name}
                                            whileHover={isClickable ? { scale: 1.06, y: -4 } : {}}
                                            whileTap={isClickable ? { scale: 0.96 } : {}}
                                            onClick={() => isClickable && handleDaySlotClick(idx)}
                                            style={{
                                                padding: '14px 6px',
                                                borderRadius: '16px',
                                                textAlign: 'center',
                                                cursor: isClickable ? 'pointer' : 'default',
                                                background: isPlaced
                                                    ? `linear-gradient(135deg, ${colors.from}, ${colors.to})`
                                                    : isHighlighted
                                                        ? 'rgba(var(--primary-rgb), 0.08)'
                                                        : 'rgba(var(--bg-card-rgb), 0.9)',
                                                borderWidth: '2px',
                                                borderStyle: isHighlighted && !isPlaced ? 'dashed' : 'solid',
                                                borderColor: isPlaced
                                                    ? 'transparent'
                                                    : isHighlighted
                                                        ? 'var(--primary)'
                                                        : 'var(--border-soft)',
                                                color: isPlaced ? '#fff' : 'var(--text-main)',
                                                boxShadow: isPlaced ? `0 8px 24px ${colors.glow}` : 'none',
                                                transition: 'all 0.3s',
                                                position: 'relative',
                                                minHeight: '100px',
                                                display: 'flex',
                                                flexDirection: 'column',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                gap: '4px'
                                            }}
                                        >
                                            {/* Placed label badge */}
                                            {isPlaced && (
                                                <motion.div
                                                    initial={{ scale: 0 }}
                                                    animate={{ scale: 1 }}
                                                    style={{
                                                        position: 'absolute',
                                                        top: '-8px',
                                                        right: '-4px',
                                                        background: '#fff',
                                                        borderRadius: '8px',
                                                        padding: '2px 6px',
                                                        fontSize: '0.55rem',
                                                        fontWeight: 900,
                                                        color: colors.from,
                                                        boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                                                    }}
                                                >
                                                    {isToday ? 'अद्य' : isYesterday ? 'ह्यः' : 'श्वः'}
                                                </motion.div>
                                            )}

                                            <div style={{ fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', opacity: 0.8 }}>
                                                {name.slice(0, 3)}
                                            </div>
                                            <div className="devanagari" style={{
                                                fontSize: '0.85rem',
                                                fontWeight: 900,
                                                lineHeight: 1.2,
                                            }}>
                                                {dayItem?.sanskrit || ''}
                                            </div>
                                            <div style={{ fontSize: '0.5rem', fontWeight: 600, opacity: 0.7 }}>
                                                {dayItem?.transliteration || ''}
                                            </div>
                                        </motion.div>
                                    );
                                })}
                            </div>

                            {/* Relative Time Words Reference */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'center',
                                gap: '12px',
                                marginBottom: '24px',
                                flexWrap: 'wrap'
                            }}>
                                {[
                                    { word: yesterdayWord, color: '#F59E0B', isDone: placedYesterday !== null },
                                    { word: todayWord, color: 'var(--primary)', isDone: placedToday !== null },
                                    { word: tomorrowWord, color: '#10B981', isDone: placedTomorrow !== null },
                                ].map((item, i) => (
                                    <motion.div
                                        key={i}
                                        animate={
                                            (dayPhase === 'yesterday' && i === 0) ||
                                            (dayPhase === 'today' && i === 1) ||
                                            (dayPhase === 'tomorrow' && i === 2)
                                                ? { scale: [1, 1.05, 1] }
                                                : {}
                                        }
                                        transition={{ repeat: Infinity, duration: 2 }}
                                        style={{
                                            padding: '14px 24px',
                                            borderRadius: '16px',
                                            background: item.isDone ? 'rgba(76, 175, 80, 0.08)' : 'rgba(var(--bg-card-rgb), 0.9)',
                                            borderWidth: '2px',
                                            borderStyle: 'solid',
                                            borderColor: item.isDone ? '#4CAF50' : item.color,
                                            textAlign: 'center',
                                            opacity: item.isDone ? 0.5 : 1,
                                            minWidth: '100px'
                                        }}
                                    >
                                        <div className="devanagari" style={{ fontSize: '1.3rem', fontWeight: 900, color: item.isDone ? '#4CAF50' : item.color }}>
                                            {item.isDone ? '✓ ' : ''}{item.word?.sanskrit || ''}
                                        </div>
                                        <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-dim)' }}>
                                            {item.word?.englishMeaning || ''}
                                        </div>
                                    </motion.div>
                                ))}
                            </div>

                            {/* Next Round / Complete */}
                            {dayPhase === 'complete' && (
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="flex justify-center gap-4"
                                    style={{ flexWrap: 'wrap' }}
                                >
                                    <button
                                        onClick={startNewDayRound}
                                        style={{
                                            padding: '14px 32px',
                                            borderRadius: '100px',
                                            borderWidth: '2px',
                                            borderStyle: 'solid',
                                            borderColor: 'var(--primary)',
                                            background: 'transparent',
                                            color: 'var(--primary)',
                                            fontWeight: 800,
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px'
                                        }}
                                    >
                                        <RotateCcw size={18} /> Next Round
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
                                </motion.div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
