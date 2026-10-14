"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Sidebar from "@/components/Sidebar";
import { motion } from "framer-motion";
import { 
  BarChart3, 
  Target, 
  TrendingUp, 
  Medal,
  Dna,
  Zap
} from "lucide-react";

/** Per-user quiz aggregates, read only from persisted quiz_attempts rows. */
interface QuizSummary {
  attempts?: number;
  average_score?: number | null;
  best_score?: number | null;
  last_score?: number | null;
  last_submitted_at?: string | null;
  lessons_attempted?: number;
  perfect_attempts?: number;
  questions_correct?: number;
  questions_answered?: number;
}

/** Shape of GET /progress (legacy fields plus persisted completion/streak). */
interface ProgressData {
  username?: string;
  /** Real curriculum size from the lesson catalog — replaces the legacy
   *  hardcoded `total_lessons: 20` in the per-user progress JSON. */
  total_lessons?: number;
  completed?: number;
  in_progress?: number;
  streak_days?: number;
  current_streak?: number;
  longest_streak?: number;
  completed_lesson_ids?: (string | number)[];
  lessons_completed?: number;
  /** Persisted, user-scoped statistics (see GET /progress). The legacy
   *  `avg_score` field was removed from the API: nothing ever wrote it, so it
   *  was permanently 0. */
  quiz_attempts?: number;
  quiz_average_score?: number;
  grammar_activity_count?: number;
  grammar_average_score?: number;
  quiz?: QuizSummary;
  points?: number;
}

/** Skill mastery rows returned under GET /dashboard's `mastery` key. */
interface MasterySkill {
  mastery?: number;
  attempts?: number;
  correct?: number;
}

/** Shape of GET /dashboard (only the mastery fields this page reads). */
interface DashboardData {
  mastery?: {
    average?: number;
    mastered_skills?: number;
    skills?: Record<string, MasterySkill>;
  };
}

export default function Progress() {
  const { user, loading: authLoading } = useAuth();
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (!user) return;
    let isMounted = true;

    const fetchProgress = async () => {
      try {
        const [progressData, dashboardData] = await Promise.all([
          api.user.getProgress(),
          api.user.getPersistentDashboard().catch(() => null),
        ]);
        if (isMounted) {
          setProgress(progressData);
          setDashboard(dashboardData);
          setFetchError(null);
        }
      } catch (err) {
        // Surface the failure instead of leaving a silent blank screen.
        console.error(err);
        if (isMounted) {
          setFetchError(
            err instanceof Error ? err.message : "Could not load your progress."
          );
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchProgress();

    return () => { isMounted = false; };
  }, [user]);

  if (authLoading || loading || !user) return null;

  const quizAttempted = (progress?.quiz_attempts ?? 0) > 0;
  const grammarAttempted = (progress?.grammar_activity_count ?? 0) > 0;
  // Real per-attempt aggregates from GET /progress → `quiz`.
  const quiz = progress?.quiz;

  const stats = [
    // "Moving to Vidvan" claimed a proficiency progression the app does not
    // track; the card now states only what the profile actually holds.
    { label: "Current Rank", value: user.level.toUpperCase(), desc: "From your account profile", icon: Medal, color: "var(--primary)" },
    { label: "Daily Streak", value: `${progress?.current_streak ?? progress?.streak_days ?? 0} days`, desc: "Consecutive active days", icon: Target, color: "#3498db" },
    // Real average of THIS user's submitted quiz scores; honest empty state
    // when there are no attempts (previously a permanently-0 `avg_score`).
    { label: "Quiz Accuracy", value: quizAttempted ? `${Math.round(progress?.quiz_average_score ?? 0)}%` : 'No attempts yet', desc: "Average of submitted quiz scores", icon: Zap, color: "var(--accent)" },
  ];

  return (
    <div className="page-layout">
      <Sidebar user={user} />
      
      <main className="main-content">
        <motion.header 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ marginBottom: '40px' }}
        >
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Learning Insights</h1>
          <p style={{ color: 'var(--text-dim)' }}>Visualizing your evolution through the linguistic matrix.</p>
        </motion.header>

        {fetchError && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="zen-card"
            role="alert"
            style={{
              padding: '18px 24px',
              marginBottom: '28px',
              border: '1px solid rgba(192, 90, 43, 0.35)',
              color: 'var(--primary)',
              fontSize: '0.9rem'
            }}
          >
            <strong>Progress data unavailable:</strong> {fetchError}
          </motion.div>
        )}

        <section className="grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '30px', marginBottom: '40px' }}>
          {stats.map((stat, i) => {
            const Icon = stat.icon;
            return (
              <motion.div 
                key={stat.label}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="zen-card"
                style={{ padding: '40px', textAlign: 'center' }}
              >
                <div style={{ width: '60px', height: '60px', borderRadius: '50%', background: 'var(--bg-main)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', color: stat.color }}>
                  <Icon size={28} />
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '1px' }}>{stat.label}</div>
                <div style={{ fontSize: '2rem', fontWeight: '800', margin: '8px 0' }}>{stat.value}</div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>{stat.desc}</p>
              </motion.div>
            );
          })}
        </section>

        <div className="grid" style={{ gridTemplateColumns: '1.5fr 1fr', gap: '30px' }}>
          
          <motion.section 
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="zen-card"
            style={{ padding: '40px' }}
          >
            <div className="flex items-center gap-3 mb-10">
              <TrendingUp size={20} color="var(--primary)" />
              <h3 style={{ margin: 0 }}>Progress Streams</h3>
            </div>
            
            <div className="flex flex-col gap-10">
              {[
                {
                  label: "Foundations",
                  sub: `Lessons Completed (of ${progress?.total_lessons ?? 0})`,
                  // Real curriculum size from the catalog, not the hardcoded
                  // 20 that shipped in the legacy progress JSON.
                  val: progress?.total_lessons
                    ? Math.round(
                        ((progress?.lessons_completed ?? progress?.completed ?? 0) /
                          progress.total_lessons) * 100
                      )
                    : null,
                  empty: 'No curriculum loaded'
                },
                { label: "Overall Mastery", sub: "Average BKT Mastery", val: dashboard?.mastery?.average !== undefined ? Math.round(dashboard.mastery.average * 100) : null, empty: 'No attempts yet' },
                // Average of THIS user's own grammar-check scores, gated on a
                // real attempt count. Never the general quiz average
                // relabelled as grammar accuracy.
                { label: "Grammar Accuracy", sub: "Average of your grammar checks", val: grammarAttempted ? Math.round(progress?.grammar_average_score ?? 0) : null, empty: 'No attempts yet' }
              ].map((item, i) => (
                <div key={item.label}>
                  <div className="flex justify-between items-end mb-3">
                    <div>
                      <h4 style={{ fontSize: '1rem', color: 'var(--text-main)', marginBottom: '2px' }}>{item.label}</h4>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>{item.sub}</p>
                    </div>
                    <span style={{ fontWeight: '700', color: 'var(--primary)' }}>
                      {item.val === null ? item.empty : `${item.val}%`}
                    </span>
                  </div>
                  <div style={{ height: '8px', background: 'var(--bg-main)', borderRadius: '10px', overflow: 'hidden' }}>
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${item.val ?? 0}%` }}
                      transition={{ duration: 1, delay: 0.5 + i * 0.1 }}
                      style={{ height: '100%', background: 'var(--primary)', borderRadius: '10px' }}
                    ></motion.div>
                  </div>
                </div>
              ))}
            </div>
          </motion.section>

          <motion.section 
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="zen-card"
            style={{ padding: '40px' }}
          >
            <div className="flex items-center gap-3 mb-8">
              <Dna size={20} color="var(--primary)" />
              <h3 style={{ margin: 0 }}>Skill Mastery</h3>
            </div>
            
            <div className="flex flex-col gap-5">
              {[
                { label: "Overall Mastery", val: dashboard?.mastery?.average !== undefined ? `${Math.round(dashboard.mastery.average * 100)}%` : 'No attempts yet', icon: "📊" },
                { label: "Mastered Skills", val: dashboard?.mastery?.mastered_skills !== undefined ? `${dashboard.mastery.mastered_skills} of ${dashboard?.mastery?.skills ? Object.keys(dashboard.mastery.skills).length : 0}` : 'No attempts yet', icon: "🎓" },
                { label: "Grammar Accuracy", val: grammarAttempted ? `${Math.round(progress?.grammar_average_score ?? 0)}%` : 'No attempts yet', icon: "✍️" }
              ].map((skill) => (
                <div key={skill.label} className="flex items-center justify-between p-4" style={{ background: 'var(--bg-main)', borderRadius: '14px' }}>
                  <div className="flex items-center gap-4">
                    <span style={{ fontSize: '1.2rem' }}>{skill.icon}</span>
                    <span style={{ fontWeight: '600', fontSize: '0.9rem' }}>{skill.label}</span>
                  </div>
                  <div style={{ fontWeight: '700', fontSize: '0.9rem' }}>{skill.val}</div>
                </div>
              ))}
            </div>

            {/* The "Next session: Tomorrow, 8 AM" card was removed: the app
                has no scheduler, so a session time was invented. */}
          </motion.section>
        </div>

        {/* Quiz Performance — every figure is aggregated from this user's own
            persisted quiz_attempts rows. Nothing here is estimated or
            defaulted; an account with no submissions gets the empty state. */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="zen-card"
          style={{ padding: '40px', marginTop: '30px' }}
        >
          <div className="flex items-center gap-3 mb-8">
            <Zap size={20} color="var(--accent)" />
            <h3 style={{ margin: 0 }}>Quiz Performance</h3>
          </div>

          {quiz?.attempts ? (
            <div
              className="grid"
              style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '16px' }}
            >
              {[
                { label: "Attempts submitted", value: `${quiz.attempts}` },
                { label: "Average score", value: `${Math.round(quiz.average_score ?? 0)}%` },
                { label: "Best score", value: `${Math.round(quiz.best_score ?? 0)}%` },
                { label: "Most recent score", value: `${Math.round(quiz.last_score ?? 0)}%` },
                {
                  label: "Lessons attempted",
                  value: `${quiz.lessons_attempted} of ${progress?.total_lessons ?? 0}`
                },
                {
                  label: "Questions correct",
                  value: `${quiz.questions_correct} of ${quiz.questions_answered}`
                }
              ].map((cell) => (
                <div key={cell.label} style={{ background: 'var(--bg-main)', borderRadius: '14px', padding: '18px' }}>
                  <div
                    style={{
                      fontSize: '0.72rem',
                      textTransform: 'uppercase',
                      letterSpacing: '1px',
                      color: 'var(--text-dim)',
                      fontWeight: 700
                    }}
                  >
                    {cell.label}
                  </div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: '6px' }}>
                    {cell.value}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', margin: 0 }}>
              No quiz submitted yet. Submit a lesson quiz and your real scores will appear here.
            </p>
          )}
        </motion.section>
      </main>
    </div>
  );
}
