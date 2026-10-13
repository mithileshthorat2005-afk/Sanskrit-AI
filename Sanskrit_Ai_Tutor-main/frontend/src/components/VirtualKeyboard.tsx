import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface VirtualKeyboardProps {
    onKeyPress: (char: string) => void;
    onBackspace: () => void;
    onClose?: () => void;
}

const DEVANAGARI_LAYOUT = {
    vowels: ['अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ऋ', 'ए', 'ऐ', 'ओ', 'औ', 'अं', 'अः'],
    consonants: [
        'क', 'ख', 'ग', 'घ', 'ङ',
        'च', 'छ', 'ज', 'झ', 'ञ',
        'ट', 'ठ', 'ड', 'ढ', 'ण',
        'त', 'थ', 'द', 'ध', 'न',
        'प', 'फ', 'ब', 'भ', 'म',
        'य', 'र', 'ल', 'व', 'श', 'ष', 'स', 'ह',
        'क्ष', 'त्र', 'ज्ञ'
    ],
    matras: ['ा', 'ि', 'ी', 'ु', 'ू', 'ृ', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः', '्'], // Last one is Halant
    numbers: ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९']
};

export default function VirtualKeyboard({ onKeyPress, onBackspace, onClose }: VirtualKeyboardProps) {
    const [activeTab, setActiveTab] = useState<'consonants' | 'vowels' | 'matras' | 'numbers'>('consonants');

    const renderKeys = (characters: string[]) => {
        return characters.map((char, index) => (
            <motion.button
                key={index}
                whileHover={{ scale: 1.05, backgroundColor: 'var(--border-soft)' }}
                whileTap={{ scale: 0.95 }}
                onClick={(e) => {
                    e.preventDefault();
                    onKeyPress(char);
                }}
                style={{
                    padding: '12px 8px',
                    fontSize: '1.4rem',
                    background: 'var(--bg-main)',
                    border: '1px solid var(--border-soft)',
                    borderRadius: '12px',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    color: 'var(--text-main)',
                    fontFamily: '"Noto Sans Devanagari", sans-serif',
                    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                    boxShadow: 'var(--shadow)',
                }}
            >
                {char}
            </motion.button>
        ));
    };

    return (
        <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="zen-card"
            style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-soft)',
                borderRadius: '24px',
                padding: '24px',
                boxShadow: '0 20px 50px rgba(0,0,0,0.1)',
                width: '100%',
                maxWidth: '650px',
                margin: '10px auto',
                zIndex: 50,
            }}
        >
            {/* Header and Controls */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {(['consonants', 'vowels', 'matras', 'numbers'] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={(e) => { e.preventDefault(); setActiveTab(tab); }}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '10px',
                                background: activeTab === tab ? 'var(--primary)' : 'var(--bg-main)',
                                color: activeTab === tab ? '#ffffff' : 'var(--text-dim)',
                                cursor: 'pointer',
                                fontWeight: '700',
                                fontSize: '0.75rem',
                                textTransform: 'uppercase',
                                letterSpacing: '1px',
                                transition: 'all 0.3s',
                                border: activeTab === tab ? 'none' : '1px solid var(--border-soft)',
                            }}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                {onClose && (
                    <button 
                        onClick={onClose} 
                        style={{ 
                            border: 'none', 
                            background: 'var(--bg-main)', 
                            color: 'var(--text-light)',
                            cursor: 'pointer', 
                            width: '32px',
                            height: '32px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '0.8rem'
                        }}
                    >
                        ✕
                    </button>
                )}
            </div>

            {/* Keyboard Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(55px, 1fr))',
                gap: '10px',
                marginBottom: '24px'
            }}>
                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeTab}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 10 }}
                        transition={{ duration: 0.2 }}
                        style={{ display: 'contents' }}
                    >
                        {renderKeys(DEVANAGARI_LAYOUT[activeTab])}
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* Action Keys (Space, Purnaviram, Backspace) */}
            <div style={{ display: 'flex', gap: '12px' }}>
                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={(e) => { e.preventDefault(); onKeyPress(' '); }}
                    style={{ 
                        flex: 2, 
                        padding: '16px', 
                        borderRadius: '16px', 
                        border: '1px solid var(--border-soft)', 
                        background: 'var(--bg-main)',
                        color: 'var(--text-main)',
                        fontWeight: '600',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px'
                    }}
                >
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px' }}>Space</span>
                    <span style={{ fontSize: '1.1rem' }}>अंतरम्</span>
                </motion.button>
                <motion.button
                    whileHover={{ scale: 1.05, backgroundColor: 'var(--primary)', color: '#fff' }}
                    whileTap={{ scale: 0.95 }}
                    onClick={(e) => { e.preventDefault(); onKeyPress('।'); }}
                    style={{ 
                        flex: 1,
                        padding: '16px', 
                        borderRadius: '16px', 
                        border: '1px solid var(--border-soft)', 
                        background: 'var(--bg-main)',
                        color: 'var(--primary)', 
                        fontWeight: '700',
                        cursor: 'pointer',
                        fontSize: '1.6rem',
                        transition: 'all 0.3s'
                    }}
                >
                    <span title="Purnaviram (Full stop)">।</span>
                </motion.button>
                <motion.button
                    whileHover={{ scale: 1.02, backgroundColor: '#e74c3c', color: '#fff' }}
                    whileTap={{ scale: 0.98 }}
                    onClick={(e) => { e.preventDefault(); onBackspace(); }}
                    style={{ 
                        flex: 1,
                        padding: '16px', 
                        borderRadius: '16px', 
                        border: 'none', 
                        background: 'rgba(231, 76, 60, 0.1)', 
                        color: '#e74c3c', 
                        fontWeight: '700',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        transition: 'all 0.3s'
                    }}
                >
                    ⌫ DELETE
                </motion.button>
            </div>
        </motion.div>
    );
}
