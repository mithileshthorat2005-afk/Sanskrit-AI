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
  History,
  Medal,
  Dna,
  Zap,
  Star
} from "lucide-react";

export default function Progress() {
  const { user, loading: authLoading } = useAuth();
  const [progress, setProgress] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (!user) return;
    let isMounted = true;

    const fetchProgress = async () => {
      try {
        const data = await api.user.getProgress();
        if (isMounted) setProgress(data);
      } catch (err) {
        console.error(err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchProgress();

    return () => { isMounted = false; };
  }, [user]);

  if (authLoading || loading || !user) return null;

  const stats = [
    { label: "Current Rank", value: user.level.toUpperCase(), desc: "Moving to Vidvan", icon: Medal, color: "var(--primary)" },
    { label: "Daily Streak", value: `${progress?.current_streak ?? progress?.streak_days ?? 0} days`, desc: "Consistency build grit", icon: Target, color: "#3498db" },
    { label: "Accuracy", value: `${progress?.avg_score || 0}%`, desc: "Recitation precision", icon: Zap, color: "var(--accent)" },
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
                { label: "Foundations", sub: "Alphabet & Basics", val: Math.round((progress?.completed || 0) / (progress?.total_lessons || 10) * 100) },
                { label: "Morphology", sub: "Noun & Verb Forms", val: 42 },
                { label: "Syntax", sub: "Sentence Building", val: 18 }
              ].map((item, i) => (
                <div key={item.label}>
                  <div className="flex justify-between items-end mb-3">
                    <div>
                      <h4 style={{ fontSize: '1rem', color: 'var(--text-main)', marginBottom: '2px' }}>{item.label}</h4>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>{item.sub}</p>
                    </div>
                    <span style={{ fontWeight: '700', color: 'var(--primary)' }}>{item.val}%</span>
                  </div>
                  <div style={{ height: '8px', background: 'var(--bg-main)', borderRadius: '10px', overflow: 'hidden' }}>
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${item.val}%` }}
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
                { label: "Reading", stars: 4, icon: "📖" },
                { label: "Writing", stars: 3, icon: "✍️" },
                { label: "Speaking", stars: 2, icon: "🗣️" },
                { label: "Prosody", stars: 1, icon: "💎" }
              ].map((skill, i) => (
                <div key={skill.label} className="flex items-center justify-between p-4" style={{ background: 'var(--bg-main)', borderRadius: '14px' }}>
                  <div className="flex items-center gap-4">
                    <span style={{ fontSize: '1.2rem' }}>{skill.icon}</span>
                    <span style={{ fontWeight: '600', fontSize: '0.9rem' }}>{skill.label}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {[1,2,3,4,5].map(s => (
                      <Star key={s} size={14} fill={s <= skill.stars ? 'var(--primary)' : 'none'} color={s <= skill.stars ? 'var(--primary)' : 'var(--text-light)'} />
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '40px', padding: '20px', background: 'rgba(192, 90, 43, 0.05)', borderRadius: '16px', textAlign: 'center' }}>
               <History size={20} style={{ color: 'var(--primary)', marginBottom: '8px' }} />
               <p style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>Next session: <strong>Tomorrow, 8 AM</strong></p>
            </div>
          </motion.section>
        </div>
      </main>
    </div>
  );
}
