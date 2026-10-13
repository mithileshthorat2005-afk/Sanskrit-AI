import React, { useState, useRef } from 'react';
import VirtualKeyboard from './VirtualKeyboard'; // Make sure the path is correct

interface SanskritInputProps {
    value: string;
    onChange: (val: string) => void;
    placeholder?: string;
    style?: React.CSSProperties;
    className?: string;
    showLabel?: boolean;
}

export default function SanskritInput({ 
    value, 
    onChange, 
    placeholder = "Type in English, or use the virtual keyboard for Hindi/Sanskrit...",
    style,
    className = "",
    showLabel = true
}: SanskritInputProps) {
    const [showKeyboard, setShowKeyboard] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const normalizeSanskrit = (input: string) => {
        const matraMap: { [key: string]: string } = {
            'अ': '',
            'आ': 'ा',
            'इ': 'ि',
            'ई': 'ी',
            'उ': 'ु',
            'ऊ': 'ू',
            'ऋ': 'ृ',
            'ए': 'े',
            'ऐ': 'ै',
            'ओ': 'ो',
            'औ': 'ौ',
        };

        let result = input;
        // Handle Halant + Vowel -> Matra (e.g., न् + अ -> न, न् + आ -> ना)
        for (const [vowel, matra] of Object.entries(matraMap)) {
            const pattern = new RegExp(`्${vowel}`, 'g');
            result = result.replace(pattern, matra);
        }
        return result;
    };

    const handleKeyPress = (char: string) => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;

        // Insert char then normalize
        const rawText = value.substring(0, start) + char + value.substring(end);
        const normalized = normalizeSanskrit(rawText);
        
        onChange(normalized);

        // Adjust cursor position
        const lengthDiff = rawText.length - normalized.length;
        setTimeout(() => {
            textarea.selectionStart = textarea.selectionEnd = start + char.length - lengthDiff;
            textarea.focus();
        }, 0);
    };

    const handleNativeChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newVal = normalizeSanskrit(e.target.value);
        onChange(newVal);
    };

    const handleBackspace = () => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;

        if (start !== end) {
            onChange(value.substring(0, start) + value.substring(end));
            setTimeout(() => {
                textarea.selectionStart = textarea.selectionEnd = start;
                textarea.focus();
            }, 0);
        } else if (start > 0) {
            onChange(value.substring(0, start - 1) + value.substring(end));
            setTimeout(() => {
                textarea.selectionStart = textarea.selectionEnd = start - 1;
                textarea.focus();
            }, 0);
        }
    };

    return (
        <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>

            {/* Header & Toggle Button */}
            <div style={{ display: 'flex', justifyContent: showLabel ? 'space-between' : 'flex-end', marginBottom: '12px' }}>
                {showLabel && (
                    <label style={{ fontWeight: '700', fontSize: '1rem', color: 'var(--text-main)', letterSpacing: '-0.2px' }}>
                        Enter Text (पाठम् लिखतु)
                    </label>
                )}
                <button
                    onClick={() => setShowKeyboard(!showKeyboard)}
                    style={{
                        padding: '10px 20px',
                        background: showKeyboard ? '#e74c3c' : 'var(--primary)',
                        color: 'white',
                        borderRadius: '12px',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: '700',
                        fontSize: '0.8rem',
                        textTransform: 'uppercase',
                        letterSpacing: '1px',
                        transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                        boxShadow: '0 8px 20px rgba(var(--primary-rgb), 0.15)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }}
                >
                    {showKeyboard ? '✕ Close Keyboard' : '⌨️ Devanagari Keyboard'}
                </button>
            </div>

            {/* The Actual Text Box */}
            <textarea
                ref={textareaRef}
                value={value}
                onChange={handleNativeChange}
                onClick={() => {
                    if (textareaRef.current) textareaRef.current.focus();
                }}
                placeholder={placeholder}
                style={{
                    width: '100%',
                    minHeight: '150px',
                    padding: '24px',
                    fontSize: '1.25rem',
                    borderRadius: '24px',
                    border: '1.5px solid var(--border-soft)',
                    background: 'var(--bg-card)',
                    color: 'var(--text-main)',
                    fontFamily: '"Noto Sans Devanagari", sans-serif',
                    resize: 'none',
                    flex: 1,
                    boxShadow: 'var(--shadow)',
                    ...style
                }}
                className={`focus:outline-none focus:border-primary ${className}`}
            />

            {/* Render the Keyboard conditionally */}
            {showKeyboard && (
                <div style={{ marginTop: '20px' }}>
                    <VirtualKeyboard
                        onKeyPress={handleKeyPress}
                        onBackspace={handleBackspace}
                        onClose={() => setShowKeyboard(false)}
                    />
                </div>
            )}

        </div>
    );
}
