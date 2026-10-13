"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Sidebar from "@/components/Sidebar";
import DailyStreak from "@/components/DailyStreak";
import AudioPronounceButton from "@/components/AudioPronounceButton";
import { motion } from "framer-motion";
import {
  Trophy,
  Flame,
  Target,
  BookOpen,
  History,
  Sparkles,
  Zap,
  Menu,
  X,
  ArrowRight
} from "lucide-react";

// Sanskrit motivational quotes that rotate
const SANSKRIT_QUOTES = [
  { sanskrit: "विद्या ददाति विनयम्", transliteration: "Vidyā dadāti vinayam", meaning: "Knowledge gives humility" },
  { sanskrit: "सत्यमेव जयते", transliteration: "Satyameva jayate", meaning: "Truth alone triumphs" },
  { sanskrit: "अहिंसा परमो धर्मः", transliteration: "Ahiṃsā paramo dharmaḥ", meaning: "Non-violence is the highest duty" },
  { sanskrit: "वसुधैव कुटुम्बकम्", transliteration: "Vasudhaiva kuṭumbakam", meaning: "The world is one family" },
  { sanskrit: "योगः कर्मसु कौशलम्", transliteration: "Yogaḥ karmasu kauśalam", meaning: "Yoga is skill in action" },
  { sanskrit: "धर्मो रक्षति रक्षितः", transliteration: "Dharmo rakṣati rakṣitaḥ", meaning: "Dharma protects those who protect it" },
];

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [recommendation, setRecommendation] = useState<any>(null);
  const [loadingRecommendation, setLoadingRecommendation] = useState(true);
  const [loading, setLoading] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const router = useRouter();

  // Daily quote based on day of year
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000);
  const dailyQuote = SANSKRIT_QUOTES[dayOfYear % SANSKRIT_QUOTES.length];

  // Load Dashboard Stats
  useEffect(() => {
    if (!user) return;
    let isMounted = true;

    const fetchData = async () => {
      try {
        const [dashStats, recentActivities] = await Promise.all([
          api.user.getDashboardStats().catch(() => null),
          api.user.getActivities().catch(() => [])
        ]);
        if (isMounted) {
          setStats(dashStats || { words_learned: 0, lessons_completed: 0, points: 450 });
          setActivities(Array.isArray(recentActivities) ? recentActivities : []);
        }
      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchData();

    return () => { isMounted = false; };
  }, [user]);

  // Load BKT Recommendation
  useEffect(() => {
    if (!user) return;
    let isMounted = true;

    const fetchRecommendation = async () => {
      try {
        const data = await api.user.getRecommendation();
        if (isMounted) setRecommendation(data.recommendation);
      } catch (err) {
        console.error("Failed to fetch recommendation", err);
      } finally {
        if (isMounted) setLoadingRecommendation(false);
      }
    };

    fetchRecommendation();

    return () => { isMounted = false; };
  }, [user]);

  if (authLoading || loading || !user) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-main)', flexDirection: 'column', gap: '16px' }}>
        <motion.div
          animate={{ rotate: 360, scale: [1, 1.1, 1] }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
          style={{ fontSize: '2.5rem' }}
        >
          🕉️
        </motion.div>
        <motion.p
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
          style={{ color: 'var(--text-dim)', fontWeight: 600, fontSize: '0.9rem' }}
        >
          Loading your sanctuary...
        </motion.p>
      </div>
    );
  }

  return (
    <div className="page-layout">
      {/* Mobile menu */}
      <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
        {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
      </button>
      <div className={`sidebar-overlay ${mobileMenuOpen ? 'open' : ''}`} onClick={() => setMobileMenuOpen(false)} />
      <Sidebar user={user} />

      <main className="main-content">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -15 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ marginBottom: '32px' }}
        >
          <div className="flex items-center justify-between flex-wrap gap-4 mb-2">
            <div>
              <div className="badge badge-primary mb-2">
                <Sparkles size={14} /> Sanskrit Learning Space
              </div>
              <h1 className="devanagari" style={{ fontSize: '2.4rem', fontWeight: 700, margin: 0 }}>
                शुभस्य संवर्धनं, {user.username}
              </h1>
            </div>
          </div>
          <p style={{ color: 'var(--text-dim)', fontSize: '1rem', margin: 0 }}>
            Welcome back to your personalized sanctuary for Sanskrit mastery.
          </p>
        </motion.header>

        {/* Daily Inspirational Quote */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          style={{
            marginBottom: '28px',
            padding: '20px 28px',
            borderRadius: 'var(--radius-lg)',
            background: 'linear-gradient(135deg, rgba(var(--primary-rgb), 0.06), rgba(var(--primary-rgb), 0.02))',
            border: '1px solid var(--border-soft)',
            display: 'flex',
            alignItems: 'center',
            gap: '20px',
            flexWrap: 'wrap'
          }}
        >
          <motion.div
            animate={{ y: [0, -4, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="devanagari"
            style={{ fontSize: '1.5rem', fontWeight: 700 }}
          >
            {dailyQuote.sanskrit}
          </motion.div>
          <AudioPronounceButton text={dailyQuote.sanskrit} size={20} title="Listen to Sanskrit quote" />
          <div style={{ height: '24px', width: '1px', background: 'var(--border-soft)' }} />
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-dim)', fontStyle: 'italic' }}>
              {dailyQuote.transliteration}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-main)', fontWeight: 600 }}>
              "{dailyQuote.meaning}"
            </div>
          </div>
        </motion.div>

        {/* Daily Streak Section */}
        <div style={{ marginBottom: '28px' }}>
          <DailyStreak />
        </div>

        {/* Stats Grid */}
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', marginBottom: '28px', gap: '16px' }}>
          {[
            { label: "Vocabulary", value: stats?.words_learned || 0, icon: BookOpen, gradient: "linear-gradient(135deg, #3B82F6, #1D4ED8)" },
            { label: "Lessons Done", value: stats?.lessons_completed || 0, icon: Target, gradient: "linear-gradient(135deg, #E85D04, #FF9100)" },
            { label: "Level", value: user.level === 'beginner' ? '25%' : '60%', icon: Flame, gradient: "linear-gradient(135deg, #EF4444, #DC2626)" },
            { label: "Merits & XP", value: stats?.points || 450, icon: Trophy, gradient: "linear-gradient(135deg, #F59E0B, #D97706)" }
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="zen-card"
              style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}
            >
              <motion.div
                whileHover={{ scale: 1.1, rotate: 5 }}
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '14px',
                  background: stat.gradient,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                  boxShadow: '0 8px 18px -4px rgba(0,0,0,0.15)',
                  flexShrink: 0
                }}
              >
                <stat.icon size={22} />
              </motion.div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1.2 }}>
                  {stat.value}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600, marginTop: '2px' }}>
                  {stat.label}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Content Layout */}
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
          {/* Recent Activity */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="zen-card-static"
            style={{ padding: '28px' }}
          >
            <div className="flex items-center gap-3 mb-6">
              <div style={{ padding: '8px', background: 'var(--primary-light)', borderRadius: '12px', color: 'var(--primary)' }}>
                <History size={20} />
              </div>
              <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>Recent Activity</h3>
            </div>

            <div className="flex flex-col gap-3">
              {activities.length > 0 ? (
                activities.map((activity, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex justify-between items-center"
                    style={{
                      borderRadius: '14px',
                      background: 'var(--bg-main)',
                      border: '1px solid var(--border-soft)',
                      padding: '14px 16px',
                      transition: 'border-color 0.2s'
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div style={{
                        fontSize: '0.7rem',
                        padding: '4px 8px',
                        borderRadius: '8px',
                        background: 'var(--primary-light)',
                        color: 'var(--primary)',
                        fontWeight: 700
                      }}>
                        {activity.action.split(' ')[0]}
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-main)' }}>{activity.action}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{activity.details}</div>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', fontSize: '0.8rem' }}>
                      <div style={{ color: 'var(--primary)', fontWeight: 800 }}>{activity.score}</div>
                      <div style={{ color: 'var(--text-light)', fontSize: '0.7rem' }}>{activity.timestamp}</div>
                    </div>
                  </motion.div>
                ))
              ) : (
                <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>No recent activity logged yet.</p>
              )}
            </div>
          </motion.section>

          {/* Next Recommended Module */}
          {!loadingRecommendation ? (
            recommendation ? (
              <motion.section
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="zen-card-static"
                style={{
                  padding: '28px',
                  background: 'linear-gradient(135deg, var(--bg-card) 0%, var(--primary-light) 100%)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}
              >
                <div>
                  <div className="flex items-center gap-2 mb-4" style={{ color: 'var(--primary)' }}>
                    <Zap size={18} />
                    <span style={{ fontSize: '0.8rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Recommended Path
                    </span>
                  </div>
                  <h2 className="devanagari" style={{ fontSize: '1.6rem', fontWeight: 800, marginBottom: '10px', color: 'var(--text-main)' }}>
                    {recommendation.title}
                  </h2>
                  <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', marginBottom: '20px', lineHeight: '1.6' }}>
                    {recommendation.description || recommendation.content}
                  </p>

                  <div className="flex items-center gap-3 mb-6">
                    <span className="badge badge-primary">⏱️ {recommendation.duration || 25} mins</span>
                    <span className="badge badge-primary">🔱 {recommendation.level || 'Intermediate'}</span>
                  </div>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="btn-primary w-full"
                  onClick={() => router.push(`/lessons?lesson=${recommendation.id}`)}
                >
                  Continue Learning <ArrowRight size={18} />
                </motion.button>
              </motion.section>
            ) : (
              <div className="zen-card-static" style={{ padding: '28px', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-dim)' }}>All lessons mastered! Check back for new content.</p>
              </div>
            )
          ) : (
            <div className="zen-card-static" style={{ padding: '28px', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-dim)' }}>Loading recommendation...</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
