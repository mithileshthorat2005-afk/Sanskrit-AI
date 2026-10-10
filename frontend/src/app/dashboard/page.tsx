"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, API_BASE_URL, DashboardResponse } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import DailyStreak from "@/components/DailyStreak";
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
  // Ensure all 7 of these state declarations exist at the very top!
  const [user, setUser] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [recommendation, setRecommendation] = useState<any>(null);
  const [loadingRecommendation, setLoadingRecommendation] = useState(true);
  const [loading, setLoading] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const router = useRouter();

  // Daily quote based on day of year
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000);
  const dailyQuote = SANSKRIT_QUOTES[dayOfYear % SANSKRIT_QUOTES.length];

  // EFFECT 1: Load User & Dashboard Stats (Strictly mounted, no router dependency)
  useEffect(() => {
    let isMounted = true;
    const storedUser = localStorage.getItem("user");

    // FIX 1: If no user exists, DO NOT create a fake one. Kick to login.
    if (!storedUser) {
      window.location.href = "/"; 
      return;
    }

    let userData: any = null;
    try {
      userData = JSON.parse(storedUser);
    } catch (e) {
      localStorage.removeItem("user");
      window.location.href = "/";
      return;
    }

    // FIX 2: If the new backend requires an access token and we don't have one, kick to login.
    if (!userData.access_token && !localStorage.getItem("access_token")) {
      localStorage.removeItem("user");
      window.location.href = "/";
      return;
    }

    if (isMounted) setUser(userData);

    const fetchData = async () => {
      try {
        const [dashStats, recentActivities] = await Promise.all([
          api.user.getDashboardStats(userData.username),
          api.user.getActivities(userData.username)
        ]);
        if (isMounted) {
          setStats(dashStats || { words_learned: 0, lessons_completed: 0, points: 450 });
          setActivities(Array.isArray(recentActivities) ? recentActivities : []);
        }
      } catch (err: any) {
        console.error("Failed to fetch dashboard data", err);
        // FIX 3: If backend rejects the token (401 Unauthorized), wipe the poisoned data
        if (err?.message?.includes("401") || err?.response?.status === 401 || String(err).includes("401")) {
          localStorage.removeItem("user");
          localStorage.removeItem("access_token");
          window.location.href = "/";
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchData();

    return () => { isMounted = false; };
  }, []); // Runs exactly once

  // EFFECT 2: Load BKT Recommendation directly (bypassing api.ts to prevent promise hangs)
  useEffect(() => {
    let isMounted = true;
    if (!user?.username) return;

    // Ensure we start in a loading state
    setLoadingRecommendation(true);

    const fetchRecommendation = async () => {
      try {
        // Direct fetch to bypass any api.ts wrapper bugs
        const response = await fetch(`${API_BASE_URL}/recommendation/${user.username}`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (isMounted) {
          // Safely extract the recommendation regardless of how the backend wraps it
          const rec = data?.recommendation || data?.data || data;
          setRecommendation(rec);
        }
      } catch (err) {
        console.error("Failed to fetch recommendation:", err);
        if (isMounted) {
          setRecommendation(null); // Fallback to "All lessons mastered" on error
        }
      } finally {
        if (isMounted) {
          setLoadingRecommendation(false); // Guarantees the loading text disappears
        }
      }
    };

    fetchRecommendation();

    return () => { isMounted = false; };
  }, [user?.username]);


  if (loading || !user) {
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
            { label: "Lessons completed", value: stats?.lessons_completed || 0, icon: BookOpen, gradient: "linear-gradient(135deg, #3B82F6, #1D4ED8)" },
            { label: "Quiz attempts", value: stats?.quiz_attempts || 0, icon: Target, gradient: "linear-gradient(135deg, #E85D04, #FF9100)" },
            { label: "Grammar activities", value: stats?.grammar_activity_count || 0, icon: Flame, gradient: "linear-gradient(135deg, #EF4444, #DC2626)" },
            { label: "Active learning days", value: stats?.active_learning_days || 0, icon: Trophy, gradient: "linear-gradient(135deg, #F59E0B, #D97706)" },
            { label: "Average mastery", value: `${Math.round((dashboard?.mastery?.average || 0) * 100)}%`, icon: Zap, gradient: "linear-gradient(135deg, #0F766E, #14B8A6)" }
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

            <div className="flex flex-col gap-4">
              {(activities.length > 0 ? activities : (dashboard?.recent_activity || [])).map((activity: any, i: number) => (
                <div key={i} className="flex justify-between items-center p-4" style={{ borderBottom: '1px solid var(--border-soft)' }}>
                  <div className="flex items-center gap-4">
                    <div style={{ fontSize: '0.8rem', padding: '6px 12px', borderRadius: '8px', background: 'var(--bg-main)', color: 'var(--text-dim)' }}>
                      {activity.type || activity.action || 'Activity'}
                    </div>
                    <div>
                      <div style={{ fontWeight: '600', fontSize: '0.95rem' }}>{activity.detail || activity.details || activity.action || 'Activity'}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>{activity.type || activity.action || 'activity'}</div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', fontSize: '0.85rem' }}>
                    <div style={{ color: 'var(--primary)', fontWeight: '600' }}>{activity.score_percent ?? activity.score ?? 'Completed'}</div>
                    <div style={{ color: 'var(--text-light)' }}>{activity.occurred_at || activity.timestamp || ''}</div>
                  </div>
                </div>
              ))}
            </div>
          </motion.section>

          {/* Next Recommended Module */}
          {!loadingRecommendation ? (
            recommendation && (recommendation.title || recommendation.name) ? (
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
                    {recommendation.title || recommendation.name}
                  </h2>
                  <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', marginBottom: '20px', lineHeight: '1.6' }}>
                    {recommendation.description || recommendation.content}
                  </p>
                  
                  <div className="flex items-center gap-3 mb-6">
                    <span className="badge badge-primary">⏱️ {recommendation.duration || recommendation.estimated_time || 15} mins</span>
                    <span className="badge badge-primary">🔱 {recommendation.level || 'Beginner'}</span>
                  </div>
                </div>
                
                <motion.button 
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="btn-primary w-full" 
                  onClick={() => router.push(`/lessons?lesson=${recommendation.id || recommendation.lesson_id}`)}
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
