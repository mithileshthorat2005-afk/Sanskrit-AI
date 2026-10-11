// frontend/src/app/translation/page.tsx
"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import { useSanskritTransliteration } from "@/hooks/useSanskritTransliteration";
import WordSuggestions from "@/components/WordSuggestions";
import { motion, AnimatePresence } from "framer-motion";
import { Languages, ArrowRightLeft, Database, Globe, Loader2, BookMarked, Sparkles, Info, Zap } from "lucide-react";
import AudioPronounceButton from "@/components/AudioPronounceButton";

export default function Translation() {
  const [user, setUser] = useState<any>(null);
  const [suggestionsPrefix, setSuggestionsPrefix] = useState("");
  const [inputText, setInputText] = useState("");
  const [results, setResults] = useState<any>(null);
  const [direction, setDirection] = useState("en_to_sa");
  const [useApi, setUseApi] = useState(true);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  // Enable transliteration only when direction is sa_to_en (user typing Sanskrit)
  const shouldTransliterate = direction === 'sa_to_en';
  const transliteration = useSanskritTransliteration(
    inputText,
    setInputText,
    shouldTransliterate
  );

  useEffect(() => {
    let userData: any = null;
    try {
      const storedUser = localStorage.getItem("user");
      if (storedUser) userData = JSON.parse(storedUser);
    } catch (e) {
      console.error(e);
    }
    if (!userData) {
      userData = { username: "demo", level: "beginner", role: "student" };
      localStorage.setItem("user", JSON.stringify(userData));
    }
    setUser(userData);
  }, [router]);

  const handleTranslate = async () => {
    if (!inputText) return;
    setLoading(true);
    setResults(null);
    try {
      const res = await api.tools.translate({ text: inputText, direction, use_api: useApi });
      setResults(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const swapDirection = () => {
    setDirection(prev => prev === 'en_to_sa' ? 'sa_to_en' : 'en_to_sa');
    setInputText("");
    setResults(null);
    setSuggestionsPrefix("");
  };

  if (!user) return null;

  return (
    <div className="page-layout">
      <Sidebar user={user} />

      <main className="main-content">
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="zen-card"
          style={{ marginBottom: '40px', padding: '40px', borderRadius: '30px' }}
        >
          <div className="flex items-center gap-3 mb-4">
             <motion.div
                whileHover={{ rotate: 180 }}
                className="logo-box"
                style={{ background: 'var(--accent)' }}
             >
                <Languages size={20} />
             </motion.div>
             <span style={{ color: 'var(--accent)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '2px', fontSize: '0.75rem' }}>Neural Linguistic Bridge</span>
          </div>
          <h1 style={{ fontSize: '3.5rem', marginBottom: '12px', letterSpacing: '-2px', fontWeight: '800' }}>Divine Translator</h1>
          <p style={{ color: 'var(--text-dim)', fontSize: '1.2rem', maxWidth: '650px', lineHeight: '1.6' }}>
            Seamlessly deconstruct and reassemble meanings across the cultural divide between English and Sanskrit.
          </p>
        </motion.header>

        <div className="grid" style={{ gridTemplateColumns: '1.6fr 1fr', alignItems: 'start', gap: '40px' }}>

          <div className="flex flex-col gap-8">
            <motion.div
               layout
               initial={{ opacity: 0, scale: 0.98 }}
               animate={{ opacity: 1, scale: 1 }}
               className="zen-card overflow-hidden"
               style={{ padding: '0', border: 'none', boxShadow: '0 20px 50px rgba(0,0,0,0.08)' }}
            >
              {/* Header Bar */}
              <div className="translator-header">
                <div className="translator-lang-selector">
                  <motion.span
                    animate={{ color: direction === 'en_to_sa' ? 'var(--primary)' : 'var(--text-light)' }}
                    className={`translator-lang-label ${direction === 'en_to_sa' ? 'active' : 'inactive'}`}
                  >ENGLISH</motion.span>

                  <motion.button
                    whileHover={{ scale: 1.1, rotate: 180 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={swapDirection}
                    className="translator-swap-btn"
                  >
                    <ArrowRightLeft size={16} />
                  </motion.button>

                  <motion.span
                    animate={{ color: direction === 'sa_to_en' ? 'var(--primary)' : 'var(--text-light)' }}
                    className={`translator-lang-label ${direction === 'sa_to_en' ? 'active' : 'inactive'}`}
                  >SANSKRIT</motion.span>
                </div>

                <div className="translator-toggle-group">
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={useApi}
                      onChange={(e) => setUseApi(e.target.checked)}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                  <span
                    className={`translator-toggle-label ${useApi ? 'on' : ''}`}
                    onClick={() => setUseApi(!useApi)}
                  >AI ENGINE</span>
                </div>
              </div>

              {/* Textarea and Suggestions Container */}
              <div className="translator-input-area">
                <textarea
                  className={`translator-textarea ${direction === 'sa_to_en' ? 'devanagari-input' : ''}`}
                  placeholder={direction === 'en_to_sa' ? "Type English words..." : "Type in Roman (e.g., 'namaste') → instantly converts to Devanagari"}
                  value={shouldTransliterate ? transliteration.value : inputText}
                  onChange={(e) => {
                    if (shouldTransliterate) {
                      transliteration.onChange(e.target.value);
                      setSuggestionsPrefix(e.target.value);
                    } else {
                      setInputText(e.target.value);
                    }
                  }}
                />

                {/* Suggestions Dropdown */}
                <WordSuggestions
                  prefix={shouldTransliterate ? suggestionsPrefix : ""}
                  onSelect={(word) => {
                    if (shouldTransliterate) {
                      transliteration.onChange(word);
                      setSuggestionsPrefix(word);
                    }
                  }}
                  enabled={shouldTransliterate && inputText.length > 0}
                />

                <div className="translator-bottom-bar">
                  <div className="translator-hint flex items-center gap-2">
                    {direction === 'sa_to_en' ? (
                      <>
                        <span>✨ Real-time Roman → Devanagari conversion active</span>
                        {(shouldTransliterate ? transliteration.value : inputText).trim() && (
                          <span className="inline-flex items-center gap-1 ml-2">
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Listen to input:</span>
                            <AudioPronounceButton text={shouldTransliterate ? transliteration.value : inputText} size={16} />
                          </span>
                        )}
                      </>
                    ) : null}
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="btn-primary"
                    onClick={handleTranslate}
                    disabled={loading || !inputText}
                    style={{ padding: '14px 36px', borderRadius: '18px', fontSize: '1rem' }}
                  >
                    {loading ? <Loader2 className="animate-spin" size={20} /> : <Zap size={20} fill="currentColor" />}
                    <span>{loading ? "Translating..." : "Translate"}</span>
                  </motion.button>
                </div>
              </div>
            </motion.div>

            {/* Results Display */}
            <AnimatePresence mode="wait">
              {results && (
                <motion.div
                  initial={{ opacity: 0, y: 40 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                  className="flex flex-col gap-8"
                >
                  <div className="flex items-center justify-between" style={{ padding: '0 20px' }}>
                    <div className="flex items-center gap-3" style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontWeight: '800' }}>
                      {results.source === 'database' ? <Database size={16} /> : <Globe size={16} />}
                      <span style={{ textTransform: 'uppercase', letterSpacing: '2px' }}>
                        Source: {results.source === 'database' ? 'Internal Registry' : 'Neural Expansion Engine'}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-6">
                    {results.results.length > 0 ? (
                      results.results.map((res: any, i: number) => {
                        const devanagariWords = (res.devanagari || "")
                          .split(/\s+/)
                          .map((w: string) => w.trim())
                          .filter((w: string) => w.length > 0);

                        return (
                          <motion.div
                            key={i}
                            initial={{ opacity: 0, x: -30 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.1, duration: 0.5 }}
                            className="zen-card overflow-hidden group"
                            style={{ border: 'none', boxShadow: '0 15px 40px rgba(0,0,0,0.04)' }}
                          >
                            <div className="flex items-stretch">
                              <div style={{ flex: 1, padding: '48px' }}>

                                {direction === 'en_to_sa' ? (
                                  // English -> Sanskrit Mode
                                  <>
                                    <div className="flex items-center gap-6 mb-3">
                                      <h2 className="devanagari" style={{ fontSize: '4.5rem', lineHeight: 1, color: 'var(--primary)' }}>{res.devanagari}</h2>
                                      <AudioPronounceButton text={res.devanagari} size={28} title={`Play complete sentence: ${res.devanagari}`} />
                                    </div>

                                    {/* Individual Word Pronunciation when multiple words exist */}
                                    {devanagariWords.length > 1 && (
                                      <div className="flex flex-wrap items-center gap-2 mb-4">
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>Words:</span>
                                        {devanagariWords.map((word: string, widx: number) => (
                                          <span
                                            key={widx}
                                            style={{
                                              display: 'inline-flex',
                                              alignItems: 'center',
                                              gap: '4px',
                                              padding: '4px 10px',
                                              borderRadius: '8px',
                                              background: 'var(--bg-main)',
                                              border: '1px solid var(--border-soft)',
                                              fontSize: '1rem',
                                            }}
                                            className="devanagari"
                                          >
                                            <span>{word}</span>
                                            <AudioPronounceButton text={word} size={14} title={`Pronounce word: ${word}`} />
                                          </span>
                                        ))}
                                      </div>
                                    )}

                                    <p style={{ fontStyle: 'italic', color: 'var(--text-dim)', fontSize: '1.4rem', marginBottom: '32px', opacity: 0.7 }}>{res.sanskrit}</p>

                                    <div className="flex flex-wrap gap-4 items-center">
                                      <span style={{ background: 'var(--primary)', padding: '8px 16px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: '900', color: 'white', textTransform: 'uppercase', letterSpacing: '1px' }}>
                                        {res.word_type}
                                      </span>
                                      <span style={{ fontWeight: '800', fontSize: '1.6rem', color: 'var(--text-main)', letterSpacing: '-0.5px' }}>
                                        {res.meanings.join(' • ')}
                                      </span>
                                    </div>
                                  </>
                                ) : (
                                  // Sanskrit -> English Mode
                                  <>
                                    <div className="flex items-center gap-6 mb-2">
                                      <span style={{ background: 'rgba(var(--primary-rgb), 0.1)', padding: '6px 14px', borderRadius: '10px', fontSize: '0.75rem', fontWeight: '900', color: 'var(--primary)', textTransform: 'uppercase' }}>
                                        Translation Result
                                      </span>
                                    </div>
                                    <h2 style={{ fontSize: '4rem', fontWeight: '900', color: 'var(--text-main)', marginBottom: '16px', letterSpacing: '-2px' }}>
                                      {res.english || res.meanings[0]}
                                    </h2>
                                    <div className="flex items-center gap-4 mb-4">
                                       <span className="devanagari" style={{ fontSize: '2rem', color: 'var(--primary)' }}>{res.devanagari}</span>
                                       <AudioPronounceButton text={res.devanagari} size={22} title={`Play complete translation: ${res.devanagari}`} />
                                       <span style={{ color: 'var(--text-light)', fontSize: '1.2rem' }}>— {res.sanskrit}</span>
                                    </div>

                                    {/* Individual Word Pronunciation when multiple words exist */}
                                    {devanagariWords.length > 1 && (
                                      <div className="flex flex-wrap items-center gap-2 mb-6">
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>Words:</span>
                                        {devanagariWords.map((word: string, widx: number) => (
                                          <span
                                            key={widx}
                                            style={{
                                              display: 'inline-flex',
                                              alignItems: 'center',
                                              gap: '4px',
                                              padding: '4px 10px',
                                              borderRadius: '8px',
                                              background: 'var(--bg-main)',
                                              border: '1px solid var(--border-soft)',
                                              fontSize: '1rem',
                                            }}
                                            className="devanagari"
                                          >
                                            <span>{word}</span>
                                            <AudioPronounceButton text={word} size={14} title={`Pronounce word: ${word}`} />
                                          </span>
                                        ))}
                                      </div>
                                    )}

                                    <div className="flex items-center gap-4">
                                       <span style={{ fontSize: '0.9rem', color: 'var(--text-dim)', border: '1px solid var(--border-soft)', padding: '6px 12px', borderRadius: '8px' }}>{res.word_type}</span>
                                       <div className="flex gap-2">
                                          {res.meanings.slice(1).map((m: string, mi: number) => (
                                            <span key={mi} style={{ color: 'var(--text-light)', fontSize: '1rem' }}>• {m}</span>
                                          ))}
                                       </div>
                                    </div>
                                  </>
                                )}
                              </div>

                              {res.example && (
                                <div className="p-10" style={{ width: '360px', background: 'rgba(var(--primary-rgb), 0.02)', borderLeft: '1px solid var(--border-soft)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                                  <div className="flex items-center justify-between gap-3 mb-6 text-dim" style={{ fontSize: '0.75rem', fontWeight: '900', textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--primary)' }}>
                                    <div className="flex items-center gap-2">
                                      <Sparkles size={16} />
                                      <span>Context Matrix</span>
                                    </div>
                                    <AudioPronounceButton text={res.example} size={18} title="Pronounce example sentence" />
                                  </div>
                                  <p style={{ fontSize: '1.2rem', lineHeight: '1.7', color: 'var(--text-main)', fontStyle: 'italic', position: 'relative', paddingLeft: '20px' }}>
                                    <span style={{ position: 'absolute', left: 0, top: 0, fontSize: '2rem', color: 'var(--border-soft)', lineHeight: 1 }}>"</span>
                                    {res.example}
                                    <span style={{ fontSize: '2rem', color: 'var(--border-soft)', lineHeight: 1 }}>"</span>
                                  </p>
                                </div>
                              )}
                            </div>
                          </motion.div>
                        );
                      })
                    ) : (
                      <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="zen-card"
                        style={{ padding: '80px', textAlign: 'center', background: 'rgba(var(--primary-rgb), 0.02)', border: '2px dashed var(--border-soft)' }}
                      >
                        <div style={{ fontSize: '4rem', marginBottom: '24px' }}>🕯️</div>
                        <h3 style={{ fontSize: '1.8rem', fontWeight: '800', marginBottom: '16px', color: 'var(--text-main)' }}>Void of Results</h3>
                        <p style={{ color: 'var(--text-dim)', maxWidth: '400px', margin: '0 auto', fontSize: '1.1rem', lineHeight: '1.6' }}>We couldn't find a direct translation in our local registry. Turn on the AI Engine switch above for a deeper linguistic search.</p>
                      </motion.div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <aside className="flex flex-col gap-8">
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="zen-card overflow-hidden"
              style={{ padding: '0', border: '1px solid var(--border-soft)', boxShadow: '0 30px 60px rgba(var(--primary-rgb), 0.05)', borderRadius: '30px' }}
            >
              <div className="p-8 border-b" style={{ borderColor: 'var(--border-soft)', background: 'rgba(var(--primary-rgb), 0.08)' }}>
                <div className="flex items-center gap-3" style={{ color: 'var(--primary)' }}>
                   <BookMarked size={22} strokeWidth={2.5} />
                   <h4 style={{ margin: 0, fontSize: '0.8rem', fontWeight: '900', textTransform: 'uppercase', letterSpacing: '2px' }}>DAILY INSIGHT</h4>
                </div>
              </div>
              <div className="p-12 text-center" style={{ background: 'var(--bg-card)' }}>
                <motion.div
                  animate={{ y: [0, -10, 0] }}
                  transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                  className="flex items-center justify-center gap-3"
                >
                  <h2 className="devanagari" style={{ fontSize: '3.5rem', marginBottom: '15px', color: 'var(--primary)' }}>शाश्वत</h2>
                  <AudioPronounceButton text="शाश्वत" size={24} title="Pronounce: शाश्वत" />
                </motion.div>
                <p style={{ fontWeight: '900', color: 'var(--text-main)', fontSize: '1.4rem', letterSpacing: '1px' }}>SHASHWAT</p>
                <div style={{ height: '2px', width: '50px', background: 'var(--primary)', margin: '24px auto', borderRadius: '2px' }}></div>
                <p style={{ fontSize: '1.1rem', color: 'var(--text-dim)', lineHeight: '1.8', maxWidth: '220px', margin: '0 auto' }}>
                  "That which is eternal, unchanging, and transcends time."
                </p>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
              className="zen-card"
              style={{ padding: '40px', background: 'var(--primary)', color: 'white', border: 'none', boxShadow: '0 20px 40px rgba(var(--primary-rgb), 0.2)' }}
            >
              <div className="flex items-center gap-3 mb-8">
                 <div style={{ padding: '8px', background: 'rgba(255,255,255,0.2)', borderRadius: '10px' }}>
                    <Info size={18} />
                 </div>
                 <h4 style={{ fontSize: '0.8rem', fontWeight: '900', textTransform: 'uppercase', letterSpacing: '2px' }}>HOW TO TRANSLATE</h4>
              </div>

              <div className="flex flex-col gap-6">
                 <div className="flex gap-4">
                    <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 'bold' }}>1</div>
                    <p style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.9)', lineHeight: '1.5' }}>Enter text in Devanagari or standard English transliteration.</p>
                 </div>
                 <div className="flex gap-4">
                    <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 'bold' }}>2</div>
                    <p style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.9)', lineHeight: '1.5' }}>Enable the AI Engine for deeper results if the local registry is insufficient.</p>
                 </div>
              </div>
            </motion.div>
          </aside>
        </div>
      </main>
    </div>
  );
}
