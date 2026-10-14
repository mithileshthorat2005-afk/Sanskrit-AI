"use client";
import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { 
  LayoutGrid, 
  Library, 
  Languages, 
  ShieldCheck, 
  BarChart3, 
  Settings, 
  LogOut,
  Sun,
  Moon,
  Dice5,
  Flame,
  ChevronRight,
  MessageCircle
} from "lucide-react";



/**
 * Authenticated user as stored in localStorage / provided by useAuth().
 * The full shape lives in @/context/AuthContext; only the fields this
 * component actually reads are declared here.
 */
interface SidebarUser {
  username?: string;
  role?: string;
  level?: string;
}

/** Shape of the GET /streak response (only the field the sidebar reads). */
interface StreakSummary {
  current_streak?: number;
  longest_streak?: number;
}

const Sidebar = ({ user }: { user: SidebarUser }) => {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuth();
  const [theme, setTheme] = useState('light');
  // Server-side streaks cached per account key. Previously this read the
  // GLOBAL localStorage key `sanskrit_streak`, which meant every account in
  // the same browser inherited the same streak and the sidebar disagreed
  // with the progress page (which reads /progress.current_streak).
  // Keyed by username so switching accounts shows that account's own value;
  // the display falls back to 0 (nothing shown) for a signed-out user or an
  // account that has not fetched yet.
  const [streakByUser, setStreakByUser] = useState<Record<string, number>>({});

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  useEffect(() => {
    const username: string | undefined = user?.username;
    // Signed out or still resolving: render nothing rather than calling
    // setState synchronously inside the effect body.
    if (!username) return;
    let alive = true;
    api.user
      .getStreak()
      .then((data: StreakSummary) => {
        // Async callback: updates the cache for this account only.
        if (alive) {
          setStreakByUser((prev) => ({
            ...prev,
            [username]: Number(data?.current_streak) || 0,
          }));
        }
      })
      .catch(() => {
        // No streak shown rather than falling back to another user's value.
        if (alive) setStreakByUser((prev) => ({ ...prev, [username]: 0 }));
      });
    return () => { alive = false; };
  }, [user?.username]);

  // Derived, not stored: guarantees a signed-out user can never display the
  // previous account's cached value, and every account sees its own.
  const streak = user?.username ? (streakByUser[user.username] ?? 0) : 0;

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  };

  const navItems = [
    { label: "Overview", path: "/dashboard", icon: LayoutGrid },
    { label: "Lessons", path: "/lessons", icon: Library },
    { label: "Translator", path: "/translation", icon: Languages },
    { label: "Grammar Checker", path: "/grammar", icon: ShieldCheck },
    { label: "Insights", path: "/progress", icon: BarChart3 },
    { label: "Play", path: "/game/menu", icon: Dice5 },
  ];

  if (user?.role === 'admin') {
    navItems.push({ label: "Admin", path: "/admin", icon: Settings });
  }

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  return (
    <motion.aside 
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="zen-card-static sidebar-container"
      style={{ maxHeight: 'calc(100vh - 32px)', overflowY: 'auto' }}
    >
      <div className="sidebar-top">
        <div className="sidebar-header flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-3" style={{ textDecoration: 'none', cursor: 'pointer' }}>
            <motion.div 
              className="logo-box"
              whileHover={{ rotate: 8, scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              🕉️
            </motion.div>
            <span className="logo-text">Sanskrita</span>
          </Link>
          <button onClick={toggleTheme} className="theme-toggle" aria-label="Toggle theme">
            <motion.div
              key={theme}
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </motion.div>
          </button>
        </div>
        
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.path;
            
            return (
              <Link 
                key={item.path} 
                href={item.path}
                onClick={(e) => {
                  if (pathname === item.path) {
                    e.preventDefault();
                  }
                }}
                className={`sidebar-link ${isActive ? 'active' : ''}`}
                style={{ cursor: 'pointer', zIndex: 10 }}
              >
                <Icon size={18} className="nav-icon" />
                <span style={{ flex: 1 }}>{item.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active-arrow"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.2 }}
                  >
                    <ChevronRight size={14} />
                  </motion.div>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="sidebar-bottom">
        {/* Streak indicator */}
        {streak > 0 && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{ 
              padding: '12px 16px', 
              background: 'linear-gradient(135deg, rgba(var(--primary-rgb), 0.08), rgba(var(--primary-rgb), 0.03))',
              borderRadius: 'var(--radius-md)', 
              border: '1px solid var(--border-soft)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}
          >
            <motion.div
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ repeat: Infinity, duration: 2 }}
            >
              <Flame size={18} style={{ color: '#EF4444' }} />
            </motion.div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-main)' }}>{streak} Day Streak</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>Keep going!</div>
            </div>
          </motion.div>
        )}

        <div className="user-info-card">
          <div className="user-name">{user?.username}</div>
          <div className="user-level">{user?.level || 'Beginner'} Path</div>
        </div>
        <button className="logout-btn flex items-center gap-2" onClick={handleLogout}>
          <LogOut size={16} /> Sign Out
        </button>
      </div>
    </motion.aside>
  );
};

export default Sidebar;
