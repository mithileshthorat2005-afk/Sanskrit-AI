"use client";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Sidebar from "@/components/Sidebar";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Clock,
  ArrowLeft,
  Play,
  CheckCircle2,
  Lock,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  GraduationCap,
  Award,
  Target,
  Menu,
  X
} from "lucide-react";
import GreetingsLesson from "@/components/lessons/GreetingsLesson";
import NumbersLesson from "@/components/lessons/NumbersLesson";
import SelfIntroLesson from "@/components/lessons/SelfIntroLesson";
import PronounsLesson from "@/components/lessons/PronounsLesson";
import VerbsLesson from "@/components/lessons/VerbsLesson";
import NounsLesson from "@/components/lessons/NounsLesson";
import FamilyLesson from "@/components/lessons/FamilyLesson";
import QuestionWordsLesson from "@/components/lessons/QuestionWordsLesson";
import TimeLesson from "@/components/lessons/TimeLesson";
import VibhaktiLesson from "@/components/lessons/VibhaktiLesson";
import SandhiLesson from "@/components/lessons/SandhiLesson";
import TensesLesson from "@/components/lessons/TensesLesson";
import MoodsLesson from "@/components/lessons/MoodsLesson";
import PronounsExtendedLesson from "@/components/lessons/PronounsExtendedLesson";
import UpasargaLesson from "@/components/lessons/UpasargaLesson";
import VoiceLesson from "@/components/lessons/VoiceLesson";
import IndeclinablesLesson from "@/components/lessons/IndeclinablesLesson";
import ParticiplesLesson from "@/components/lessons/ParticiplesLesson";
import ReadingCompositionLesson from "@/components/lessons/ReadingCompositionLesson";
import Samasa1Lesson from "@/components/lessons/Samasa1Lesson";
import Samasa2Lesson from "@/components/lessons/Samasa2Lesson";
import Participles2Lesson from "@/components/lessons/Participles2Lesson";
import StriPratyayaLesson from "@/components/lessons/StriPratyayaLesson";
import ChandasLesson from "@/components/lessons/ChandasLesson";

// ─── Lesson Component Registry ────────────────────────────
const LESSON_COMPONENTS: Record<number, React.ComponentType<{ onBack: () => void }>> = {
  2: GreetingsLesson,
  3: NumbersLesson,
  4: SelfIntroLesson,
  5: PronounsLesson,
  6: VerbsLesson,
  7: NounsLesson,
  8: FamilyLesson,
  9: QuestionWordsLesson,
  10: TimeLesson,
  11: VibhaktiLesson,
  12: SandhiLesson,
  13: TensesLesson,
  14: MoodsLesson,
  15: PronounsExtendedLesson,
  16: UpasargaLesson,
  17: VoiceLesson,
  18: IndeclinablesLesson,
  19: ParticiplesLesson,
  20: ReadingCompositionLesson,
  21: Samasa1Lesson,
  22: Samasa2Lesson,
  23: Participles2Lesson,
  24: StriPratyayaLesson,
  25: ChandasLesson,
};

// Level configuration
const LEVEL_CONFIG = {
  beginner: {
    label: "Beginner",
    icon: GraduationCap,
    color: "#3B82F6",
    bgColor: "rgba(59, 130, 246, 0.08)",
    description: "Foundations of Sanskrit script, basic vocabulary, and simple sentence construction."
  },
  intermediate: {
    label: "Intermediate",
    icon: Target,
    color: "#8B5CF6",
    bgColor: "rgba(139, 92, 246, 0.08)",
    description: "Systematic grammar: declensions, sandhi, tenses, moods, and extended vocabulary."
  },
  advanced: {
    label: "Advanced",
    icon: Award,
    color: "#10B981",
    bgColor: "rgba(16, 185, 129, 0.08)",
    description: "Literary Sanskrit: compounds, advanced participles, feminine formation, and prosody."
  }
};

const getLevelBadge = (level: string) => {
  const config = LEVEL_CONFIG[level as keyof typeof LEVEL_CONFIG];
  return config || LEVEL_CONFIG.beginner;
};

// ─── Alphabet Flashcards (Lesson 1) ───────────────────────
const AlphabetFlashcards = () => {
  const [vowelImages, setVowelImages] = useState<string[]>([]);
  const [consonantImages, setConsonantImages] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlphabets = async () => {
      try {
        const [vResponse, cResponse] = await Promise.all([
          fetch('/api/alphabets?type=vowels'),
          fetch('/api/alphabets?type=consonants')
        ]);
        const [vData, cData] = await Promise.all([vResponse.json(), cResponse.json()]);
        if (vData.images) setVowelImages(vData.images);
        if (cData.images) setConsonantImages(cData.images);
      } finally {
        setLoading(false);
      }
    };
    fetchAlphabets();
  }, []);

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-40 gap-6">
      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2 }} className="text-[var(--primary)]">
        <Sparkles size={60} />
      </motion.div>
      <p className="text-[var(--text-dim)] font-medium">Preparing visual aids...</p>
    </div>
  );

  return (
    <div className="flex flex-col gap-12 mt-12 pb-20 max-w-6xl mx-auto">
      <AnimatePresence>
        <motion.div
          key="vowels-section"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          className="zen-card overflow-hidden border border-[var(--border-soft)] shadow-2xl relative"
        >
          <div className="bg-gradient-to-r from-[var(--primary)] to-transparent p-10 flex items-center justify-between border-b border-[var(--border-soft)]">
            <div className="flex items-center gap-6">
              <div className="w-16 h-16 bg-white/20 backdrop-blur-md rounded-3xl flex items-center justify-center text-white font-bold text-4xl shadow-xl ring-1 ring-white/30">अ</div>
              <div>
                <h3 className="text-3xl font-bold text-white tracking-tight">Sanskrit Vowels</h3>
                <p className="text-white/70 text-sm font-semibold tracking-[4px] uppercase mt-1">Swaras (Foundations)</p>
              </div>
            </div>
          </div>
          <div className="p-10 bg-[var(--bg-card)]">
            {vowelImages.length > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                {vowelImages.map((src, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.1 }}
                    className="relative group p-4 bg-[var(--bg-main)] rounded-[32px] border border-[var(--border-soft)] shadow-inner"
                  >
                    <img
                      src={src}
                      alt="Sanskrit Vowels"
                      className="w-full h-auto rounded-2xl shadow-lg group-hover:scale-[1.01] transition-transform duration-500"
                      style={{ maxHeight: '600px', objectFit: 'contain' }}
                    />
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="p-32 text-center bg-[var(--bg-main)] rounded-[40px] border-4 border-dashed border-[var(--border-soft)]">
                <p className="text-[var(--text-light)] text-xl font-bold italic tracking-wide">Manuscripts for vowels arriving soon...</p>
              </div>
            )}
          </div>
        </motion.div>

        <motion.div
          key="consonants-section"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="zen-card overflow-hidden border border-[var(--border-soft)] shadow-2xl relative"
        >
          <div className="bg-gradient-to-r from-[var(--primary)] to-transparent p-10 flex items-center justify-between border-b border-[var(--border-soft)]">
            <div className="flex items-center gap-6">
              <div className="w-16 h-16 bg-white/20 backdrop-blur-md rounded-3xl flex items-center justify-center text-white font-bold text-4xl shadow-xl ring-1 ring-white/30">क</div>
              <div>
                <h3 className="text-3xl font-bold text-white tracking-tight">Sanskrit Consonants</h3>
                <p className="text-white/70 text-sm font-semibold tracking-[4px] uppercase mt-1">Vyanjanas (Structures)</p>
              </div>
            </div>
          </div>
          <div className="p-10 bg-[var(--bg-card)]">
            {consonantImages.length > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                {consonantImages.map((src, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.1 }}
                    className="relative group p-4 bg-[var(--bg-main)] rounded-[32px] border border-[var(--border-soft)] shadow-inner"
                  >
                    <img
                      src={src}
                      alt="Sanskrit Consonants"
                      className="w-full h-auto rounded-2xl shadow-lg group-hover:scale-[1.01] transition-transform duration-500"
                      style={{ maxHeight: '600px', objectFit: 'contain' }}
                    />
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="p-32 text-center bg-[var(--bg-main)] rounded-[40px] border-4 border-dashed border-[var(--border-soft)]">
                <p className="text-[var(--text-light)] text-xl font-bold italic tracking-wide">Consonant charts currently being prepared...</p>
              </div>
            )}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

// ─── Main Lessons Page ────────────────────────────────────
export default function Lessons() {
  const { user, loading: authLoading } = useAuth();
  const [lessons, setLessons] = useState<any[]>([]);
  const [masteryMap, setMasteryMap] = useState<Record<number, number>>({});
  const [masteryLoading, setMasteryLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedLesson, setSelectedLesson] = useState<any>(null);
  const [completedIds, setCompletedIds] = useState<string[]>([]);
  const [completing, setCompleting] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, number>>({});
  const [quizResult, setQuizResult] = useState<any>(null);
  const [quizSubmitting, setQuizSubmitting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeLevel, setActiveLevel] = useState<string>("all");
  const router = useRouter();

  // Reset per-lesson quiz state whenever a different lesson is opened.
  useEffect(() => {
    setQuizAnswers({});
    setQuizResult(null);
  }, [selectedLesson?.id]);

  useEffect(() => {
    if (!user) return;

    const fetchLessons = async () => {
      try {
        const [data, progress] = await Promise.all([
          api.lessons.getAll(),
          api.user.getProgress().catch(() => null),
        ]);
        const lessonList = Array.isArray(data) ? data : [];
        setLessons(lessonList);
        if (progress?.completed_lesson_ids) {
          setCompletedIds(progress.completed_lesson_ids.map(String));
        }
        // Honor deep links such as /lessons?lesson=11 from the dashboard
        // recommendation card.
        const params = new URLSearchParams(window.location.search);
        const deepLinkedId = params.get("lesson");
        if (deepLinkedId) {
          const target = lessonList.find((l: any) => String(l.id) === String(deepLinkedId));
          if (target) setSelectedLesson(target);
        }
      } catch (err) {
        console.error(err);
        setLoadError("Could not reach the backend. Start it with \"python main.py\" and reload.");
      } finally {
        setLoading(false);
      }
    };

    fetchLessons();
  }, [router, user]);

  useEffect(() => {
    const fetchMastery = async () => {
      if (user?.username) {
        try {
          const data = await api.user.getBKTMastery();
          setMasteryMap(data.mastery);
        } catch (err) {
          console.error("Failed to fetch mastery", err);
        } finally {
          setMasteryLoading(false);
        }
      }
    };
    fetchMastery();
  }, [user]);

  const showToast = useCallback((message: string) => {
    setToast(message);
    setTimeout(() => setToast(null), 3000);
  }, []);

  const handleMarkComplete = async () => {
    if (!selectedLesson || !user || completing) return;
    setCompleting(true);
    try {
      // Explicit completion only persists progress. BKT mastery is updated
      // separately by real quiz/grammar attempts, never by this button.
      const res = await api.user.completeLesson(selectedLesson.id);
      setCompletedIds((prev) =>
        prev.includes(String(selectedLesson.id)) ? prev : [...prev, String(selectedLesson.id)]
      );
      showToast(`✨ Lesson complete! (${res.completed ?? completedIds.length + 1} done)`);
    } catch (err) {
      console.error(err);
      showToast("Failed to record progress");
    } finally {
      setCompleting(false);
    }
  };

  const handleQuizSubmit = async () => {
    if (!selectedLesson || !user || quizSubmitting) return;
    const questions = selectedLesson.quiz || [];
    if (Object.keys(quizAnswers).length !== questions.length) {
      showToast("Answer all quiz questions first");
      return;
    }
    setQuizSubmitting(true);
    try {
      const res = await api.user.submitQuiz({
        lesson_id: String(selectedLesson.id),
        answers: quizAnswers,
      });
      setQuizResult(res);
      if (res.score_percent === 100) {
        setCompletedIds((prev) =>
          prev.includes(String(selectedLesson.id)) ? prev : [...prev, String(selectedLesson.id)]
        );
      }
      showToast(
        res.score_percent === 100
          ? `✨ Perfect! Lesson mastered (${res.score_percent}%)`
          : `Quiz scored ${res.score_percent}% — try again for mastery`
      );
    } catch (err: any) {
      console.error(err);
      showToast(err?.message || "Quiz submission failed");
    } finally {
      setQuizSubmitting(false);
    }
  };

  const handleNext = () => {
    const currentIndex = lessons.findIndex(l => l.id === selectedLesson.id);
    if (currentIndex < lessons.length - 1) {
      setSelectedLesson(lessons[currentIndex + 1]);
    }
  };

  const handlePrev = () => {
    const currentIndex = lessons.findIndex(l => l.id === selectedLesson.id);
    if (currentIndex > 0) {
      setSelectedLesson(lessons[currentIndex - 1]);
    }
  };

  // Group lessons by level
  const groupedLessons = lessons.reduce((acc: any, lesson: any) => {
    const level = lesson.level || 'beginner';
    if (!acc[level]) acc[level] = [];
    acc[level].push(lesson);
    return acc;
  }, {});

  Object.keys(groupedLessons).forEach(level => {
    groupedLessons[level].sort((a: any, b: any) => a.id - b.id);
  });

  const getFilteredLessons = () => {
    if (activeLevel === "all") return lessons;
    return lessons.filter(l => l.level === activeLevel);
  };

  const getCompletionCount = (level: string) => {
    const levelLessons = lessons.filter(l => l.level === level);
    const completed = levelLessons.filter(l => completedIds.includes(String(l.id)));
    return { total: levelLessons.length, completed: completed.length };
  };

  if (!user || loading) return (
    <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-main)' }}>
      <motion.div
        animate={{ opacity: [0.4, 1, 0.4], scale: [0.98, 1.02, 0.98] }}
        transition={{ repeat: Infinity, duration: 2 }}
        style={{ fontSize: '1.2rem', color: 'var(--text-dim)', fontWeight: 600 }}
      >
        Preparing Curriculum...
      </motion.div>
    </div>
  );

  // ─── Lesson Detail View ─────────────────────────────────
  if (selectedLesson) {
    const LessonComponent = LESSON_COMPONENTS[selectedLesson.id];
    const hasCustomComponent = selectedLesson.id === 1 || !!LessonComponent;
    const currentIndex = lessons.findIndex(l => l.id === selectedLesson.id);
    const isFirst = currentIndex === 0;
    const isLast = currentIndex === lessons.length - 1;

    return (
      <div className="page-layout">
        {/* Mobile menu button */}
        <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className={`sidebar-overlay ${mobileMenuOpen ? 'open' : ''}`} onClick={() => setMobileMenuOpen(false)} />
        <div className={mobileMenuOpen ? 'open' : ''} style={mobileMenuOpen ? {} : {}}>
          <Sidebar user={user} />
        </div>
        <main className="main-content">
          <button className="flex items-center gap-2 mb-8" style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontWeight: '600', fontFamily: 'inherit', fontSize: '0.95rem' }} onClick={() => setSelectedLesson(null)}>
            <ArrowLeft size={18} /> Back to Modules
          </button>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="zen-card-static"
            style={{ padding: '48px', maxWidth: '1000px', margin: '0 auto' }}
          >
            {/* Level badge + difficulty */}
            <div className="flex items-center gap-3" style={{ marginBottom: '16px' }}>
              <span style={{
                background: selectedLesson.level === 'beginner' ? 'rgba(39, 174, 96, 0.08)' : selectedLesson.level === 'advanced' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(192, 90, 43, 0.08)',
                color: selectedLesson.level === 'beginner' ? '#27ae60' : selectedLesson.level === 'advanced' ? '#10B981' : 'var(--primary)',
                padding: '6px 14px',
                borderRadius: '10px',
                fontSize: '0.8rem',
                fontWeight: '700',
                textTransform: 'uppercase',
                letterSpacing: '1px'
              }}>
                {selectedLesson.level} Path
              </span>
              {selectedLesson.difficulty && (
                <div className="difficulty-bar">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <div key={i} className={`difficulty-dot ${i < selectedLesson.difficulty ? 'active' : ''}`} />
                  ))}
                </div>
              )}
            </div>

            <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>{selectedLesson.title}</h1>
            <div className="flex flex-wrap" style={{ gap: '20px', color: 'var(--text-light)', marginBottom: '32px' }}>
              <div className="flex items-center gap-1"><Clock size={16} /> {selectedLesson.duration} minutes</div>
              <div className="flex items-center gap-1"><BookOpen size={16} /> Concept Study</div>
            </div>

            <div style={{ fontSize: '1.15rem', lineHeight: '2', color: 'var(--text-main)', padding: '32px', background: 'var(--bg-main)', borderRadius: '20px', marginBottom: '32px' }}>
              {!hasCustomComponent && selectedLesson.content}

              {selectedLesson.id === 1 ? (
                <AlphabetFlashcards />
              ) : LessonComponent ? (
                <LessonComponent onBack={() => setSelectedLesson(null)} />
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="devanagari"
                  style={{ fontSize: '3rem', textAlign: 'center', marginTop: '60px', color: 'var(--primary)' }}
                >
                  {"सत्यं वद। धर्मं चर।"}
                  <p style={{ fontSize: '1.2rem', color: 'var(--text-dim)', marginTop: '20px' }}>
                    Advanced lesson content coming soon!
                  </p>
                </motion.div>
              )}
            </div>

            {selectedLesson.quiz && selectedLesson.quiz.length > 0 && (
              <div style={{ padding: '32px', background: 'var(--bg-main)', borderRadius: '20px', marginBottom: '32px', border: '1px solid var(--border-soft)' }}>
                <h3 style={{ fontSize: '1.3rem', marginBottom: '8px' }}>Lesson Quiz</h3>
                <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', marginBottom: '24px' }}>
                  Score 100% to master this lesson. Attempts update your skill mastery.
                </p>
                <div className="flex flex-col gap-6">
                  {selectedLesson.quiz.map((q: any) => (
                    <div key={q.id}>
                      <p style={{ fontWeight: 700, marginBottom: '12px' }}>{q.question}</p>
                      <div className="flex flex-wrap gap-3">
                        {(q.options || []).map((opt: string, oi: number) => {
                          const qid = String(q.id);
                          const isSelected = quizAnswers[qid] === oi;
                          return (
                            <button
                              key={oi}
                              onClick={() => setQuizAnswers((prev) => ({ ...prev, [qid]: oi }))}
                              style={{
                                padding: '10px 20px',
                                borderRadius: '12px',
                                border: isSelected ? '2px solid var(--primary)' : '1px solid var(--border-soft)',
                                background: isSelected ? 'var(--primary)' : 'var(--bg-card)',
                                color: isSelected ? '#fff' : 'var(--text-main)',
                                fontWeight: 700,
                                cursor: 'pointer',
                              }}
                            >
                              {opt}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
                {quizResult && (
                  <p style={{ marginTop: '20px', fontWeight: 700, color: quizResult.score_percent === 100 ? '#27ae60' : 'var(--primary)' }}>
                    Scored {quizResult.score_percent}% ({quizResult.correct_answers}/{quizResult.total_questions} correct)
                    {quizResult.mastery ? ` — mastery ${Math.round(quizResult.mastery.mastery * 100)}%` : ''}
                  </p>
                )}
                <button
                  className="btn-secondary"
                  onClick={handleQuizSubmit}
                  disabled={quizSubmitting}
                  style={{ marginTop: '20px' }}
                >
                  {quizSubmitting ? "Submitting..." : "Submit Quiz"}
                </button>
              </div>
            )}

            <div className="flex justify-between items-center flex-wrap gap-4" style={{ marginTop: '32px' }}>
              <div className="flex gap-3">
                <button
                  className="btn-secondary"
                  onClick={handlePrev}
                  disabled={isFirst}
                >
                  <ChevronLeft size={18} /> Previous
                </button>
                <button
                  className="btn-secondary"
                  onClick={handleNext}
                  disabled={isLast}
                >
                  Next <ChevronRight size={18} />
                </button>
              </div>

              <button
                className="btn-primary"
                onClick={handleMarkComplete}
                disabled={completing || (selectedLesson.quiz?.length > 0 && quizResult?.score_percent !== 100)}
                title={selectedLesson.quiz?.length > 0 && quizResult?.score_percent !== 100 ? "Score 100% on the quiz above to complete this lesson" : undefined}
                style={selectedLesson.quiz?.length > 0 && quizResult?.score_percent !== 100 ? { opacity: 0.5, cursor: 'not-allowed' } : undefined}
              >
                {completing ? "Saving..." : completedIds.includes(String(selectedLesson.id)) ? "Completed ✓" : "Mark as Complete"} <CheckCircle2 size={18} />
              </button>
            </div>
          </motion.div>
        </main>

        <AnimatePresence>
          {toast && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.95 }}
              className="toast toast-success"
            >
              <CheckCircle2 size={20} /> {toast}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  // ─── Lesson Grid View ───────────────────────────────────
  return (
    <div className="page-layout">
      <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
        {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
      </button>
      <div className={`sidebar-overlay ${mobileMenuOpen ? 'open' : ''}`} onClick={() => setMobileMenuOpen(false)} />
      <Sidebar user={user} />

      <main className="main-content">
        <header style={{ marginBottom: '48px' }}>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Learning Modules</h1>
          <p style={{ color: 'var(--text-dim)' }}>Select a step in your journey. We recommend starting with the foundations.</p>
        </header>

        {loadError && lessons.length === 0 && (
          <div className="zen-card-static" style={{ padding: '40px', textAlign: 'center', border: '1px solid rgba(192, 90, 43, 0.3)' }}>
            <p style={{ color: 'var(--primary)', fontWeight: 700 }}>{loadError}</p>
          </div>
        )}

        {/* Level Filter Tabs */}
        <div className="flex gap-3" style={{ marginBottom: '40px', flexWrap: 'wrap' }}>
          <button
            onClick={() => setActiveLevel("all")}
            style={{
              padding: '10px 24px',
              borderRadius: '100px',
              background: activeLevel === "all" ? 'var(--primary)' : 'var(--bg-card)',
              color: activeLevel === "all" ? '#fff' : 'var(--text-dim)',
              border: '1px solid var(--border-soft)',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s',
              fontSize: '0.9rem',
            }}
          >
            All ({lessons.length})
          </button>
          {Object.entries(LEVEL_CONFIG).map(([key, config]) => {
            const count = lessons.filter(l => l.level === key).length;
            const isActive = activeLevel === key;
            return (
              <button
                key={key}
                onClick={() => setActiveLevel(isActive ? "all" : key)}
                style={{
                  padding: '10px 24px',
                  borderRadius: '100px',
                  background: isActive ? config.color : 'var(--bg-card)',
                  color: isActive ? '#fff' : 'var(--text-dim)',
                  border: '1px solid var(--border-soft)',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: isActive ? `0 4px 16px ${config.color}44` : 'none',
                }}
              >
                <config.icon size={16} />
                {config.label} ({count})
              </button>
            );
          })}
        </div>

        {/* Level Sections */}
        {activeLevel === "all" ? (
          Object.entries(LEVEL_CONFIG).map(([levelKey, config]) => {
            const levelLessons = groupedLessons[levelKey] || [];
            if (levelLessons.length === 0) return null;
            const { total, completed } = getCompletionCount(levelKey);
            const progress = total > 0 ? Math.round((completed / total) * 100) : 0;

            return (
              <motion.div
                key={levelKey}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ marginBottom: '48px' }}
              >
                <div className="flex items-center justify-between flex-wrap gap-4 mb-4">
                  <div className="flex items-center gap-3">
                    <div style={{
                      padding: '10px',
                      borderRadius: '14px',
                      background: config.bgColor,
                      color: config.color,
                    }}>
                      <config.icon size={24} />
                    </div>
                    <div>
                      <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        {config.label} Level
                      </h2>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-dim)', maxWidth: '500px' }}>
                        {config.description}
                      </p>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-dim)' }}>
                      {completed}/{total} Complete
                    </div>
                    <div style={{
                      width: '120px',
                      height: '6px',
                      background: 'var(--border-soft)',
                      borderRadius: '4px',
                      marginTop: '4px',
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        width: `${progress}%`,
                        height: '100%',
                        background: config.color,
                        borderRadius: '4px',
                        transition: 'width 0.6s ease',
                      }} />
                    </div>
                  </div>
                </div>

                <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '24px' }}>
                  {levelLessons.map((lesson: any, i: number) => (
                    <motion.div
                      key={lesson.id}
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      whileHover={{ y: -6, scale: 1.01 }}
                      className="zen-card"
                      style={{ padding: '0', cursor: 'pointer', overflow: 'hidden', borderLeft: `4px solid ${config.color}` }}
                      onClick={() => setSelectedLesson(lesson)}
                    >
                      <div style={{ padding: '28px' }}>
                        <div className="flex justify-between items-start mb-4">
                          <div className="flex items-center gap-2">
                            <span style={{
                              fontSize: '0.65rem',
                              padding: '3px 10px',
                              borderRadius: '8px',
                              background: config.bgColor,
                              color: config.color,
                              fontWeight: '700',
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px',
                            }}>
                              {config.label}
                            </span>
                            <span style={{ color: 'var(--text-light)', fontSize: '0.8rem' }}>
                              ⏱️ {lesson.duration}m
                            </span>
                          </div>
                          <span style={{
                            fontSize: '0.7rem',
                            color: 'var(--text-light)',
                            fontWeight: '600',
                          }}>
                            #{lesson.id}
                          </span>
                        </div>
                        <h3 style={{ fontSize: '1.3rem', marginBottom: '8px', color: 'var(--text-main)' }}>
                          {lesson.title}
                        </h3>
                        <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', lineHeight: '1.5' }}>
                          {lesson.description}
                        </p>
                        
                        <div className="flex justify-between items-center mt-4">
                          {!masteryLoading && masteryMap[lesson.id] !== undefined && (
                            <div style={{ flex: 1, marginRight: '12px' }}>
                              <div style={{ height: '4px', background: 'var(--border-soft)', borderRadius: '4px', overflow: 'hidden' }}>
                                <motion.div 
                                  initial={{ width: 0 }}
                                  animate={{ width: `${masteryMap[lesson.id] * 100}%` }}
                                  transition={{ duration: 0.6 }}
                                  style={{ 
                                    height: '100%', 
                                    background: masteryMap[lesson.id] >= 0.7 ? 'var(--accent)' : 'var(--primary)',
                                    borderRadius: '4px',
                                  }} 
                                />
                              </div>
                              <div style={{ fontSize: '0.65rem', color: 'var(--text-light)', marginTop: '2px' }}>
                                {Math.round(masteryMap[lesson.id] * 100)}% Mastery
                              </div>
                            </div>
                          )}
                          <div className="flex items-center gap-2" style={{ color: config.color, fontWeight: '700', fontSize: '0.85rem' }}>
                            <Play size={16} fill={config.color} /> Start Lesson
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                  
                  {/* Advanced/Coming Soon Locks */}
                  {levelKey === 'advanced' && lessons.length <= 25 && (
                    <motion.div
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="zen-card-static flex items-center justify-center"
                      style={{ border: '2px dashed var(--border-soft)', background: 'transparent', minHeight: '200px' }}
                    >
                      <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Lock size={28} style={{ marginBottom: '16px', color: 'var(--text-light)', opacity: 0.5 }} />
                        <p style={{ color: 'var(--text-light)', fontSize: '0.9rem', fontWeight: 600 }}>More advanced modules in development...</p>
                      </div>
                    </motion.div>
                  )}
                </div>
              </motion.div>
            );
          })
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '24px' }}>
              {getFilteredLessons().map((lesson: any, i: number) => {
                const config = getLevelBadge(lesson.level);
                return (
                  <motion.div
                    key={lesson.id}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    whileHover={{ y: -6, scale: 1.01 }}
                    className="zen-card"
                    style={{ padding: '0', cursor: 'pointer', overflow: 'hidden', borderLeft: `4px solid ${config.color}` }}
                    onClick={() => setSelectedLesson(lesson)}
                  >
                    <div style={{ padding: '28px' }}>
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center gap-2">
                          <span style={{
                            fontSize: '0.65rem',
                            padding: '3px 10px',
                            borderRadius: '8px',
                            background: config.bgColor,
                            color: config.color,
                            fontWeight: '700',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px',
                          }}>
                            {config.label}
                          </span>
                          <span style={{ color: 'var(--text-light)', fontSize: '0.8rem' }}>
                            ⏱️ {lesson.duration}m
                          </span>
                        </div>
                        <span style={{
                          fontSize: '0.7rem',
                          color: 'var(--text-light)',
                          fontWeight: '600',
                        }}>
                          #{lesson.id}
                        </span>
                      </div>
                      <h3 style={{ fontSize: '1.3rem', marginBottom: '8px', color: 'var(--text-main)' }}>
                        {lesson.title}
                      </h3>
                      <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', lineHeight: '1.5' }}>
                        {lesson.description}
                      </p>
                      
                      <div className="flex justify-between items-center mt-4">
                        {!masteryLoading && masteryMap[lesson.id] !== undefined && (
                          <div style={{ flex: 1, marginRight: '12px' }}>
                            <div style={{ height: '4px', background: 'var(--border-soft)', borderRadius: '4px', overflow: 'hidden' }}>
                              <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: `${masteryMap[lesson.id] * 100}%` }}
                                transition={{ duration: 0.6 }}
                                style={{ 
                                  height: '100%', 
                                  background: masteryMap[lesson.id] >= 0.7 ? 'var(--accent)' : 'var(--primary)',
                                  borderRadius: '4px',
                                }} 
                              />
                            </div>
                            <div style={{ fontSize: '0.65rem', color: 'var(--text-light)', marginTop: '2px' }}>
                              {Math.round(masteryMap[lesson.id] * 100)}% Mastery
                            </div>
                          </div>
                        )}
                        <div className="flex items-center gap-2" style={{ color: config.color, fontWeight: '700', fontSize: '0.85rem' }}>
                          <Play size={16} fill={config.color} /> Start Lesson
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
