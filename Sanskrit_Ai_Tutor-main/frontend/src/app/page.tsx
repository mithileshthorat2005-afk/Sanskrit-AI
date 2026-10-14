"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import { LogIn, UserPlus, Sparkles, BookOpen, Globe, Sun, Moon, GraduationCap, Users, Brain } from "lucide-react";

export default function Home() {
  const { user, login, signup, loading: authLoading } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("student");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState('light');
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.push("/dashboard");
    }
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, [router, user]);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  };

  // Mirrors backend/modules/auth.py::password_policy_error so the user sees the
  // problem while typing instead of after submitting. The server is still the
  // authority — this only avoids a pointless round trip.
  const PASSWORD_MIN_LENGTH = 8;
  const passwordRules = [
    { id: "len",   label: `At least ${PASSWORD_MIN_LENGTH} characters`,        required: true,  met: password.length >= PASSWORD_MIN_LENGTH },
    { id: "lower", label: "A lowercase letter",                              required: true,  met: /[a-z]/.test(password) },
    { id: "upper", label: "An uppercase letter",                             required: false, met: /[A-Z]/.test(password) },
    { id: "digit", label: "A number",                                        required: false, met: /\d/.test(password) },
    { id: "spec",  label: "A special character (e.g. ! ? - _)",              required: false, met: /[^A-Za-z0-9]/.test(password) },
  ];
  const passwordProblem = isLogin
    ? null
    : passwordRules
        .filter((rule) => rule.required && !rule.met)
        .map((rule) => rule.label.toLowerCase())
        .join(" and ") || null;
  const signupBlocked = !isLogin && (passwordProblem !== null || password !== confirmPassword);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        await login(username, password);
        router.push("/dashboard");
      } else {
        if (passwordProblem) {
          throw new Error(
            `Password too weak: add ${passwordProblem}. Adding an uppercase letter, a number or a special character is strongly recommended.`
          );
        }
        if (password !== confirmPassword) {
          throw new Error("Passwords do not match");
        }
        await signup(username, password, role);
        setIsLogin(true);
        setError("Account created! Please login.");
      }
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const floatingGlyphs = ["अ", "क", "ग", "म", "न", "स", "त", "प", "र", "ल"];

  return (
    <main style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      flexDirection: 'column', 
      padding: '2rem', 
      background: 'var(--bg-main)',
      transition: 'background 0.4s ease',
      position: 'relative',
      overflow: 'hidden'
    }}>
      
      {/* Floating Devanagari Glyphs Background */}
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
        {floatingGlyphs.map((glyph, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{ 
              opacity: [0, 0.06, 0],
              y: [0, -60, -120],
              x: [0, Math.sin(i) * 20],
            }}
            transition={{ 
              duration: 8 + i * 2,
              repeat: Infinity,
              delay: i * 1.5,
              ease: "easeInOut"
            }}
            style={{ 
              position: 'absolute',
              fontFamily: "'Noto Serif Devanagari', serif",
              fontSize: `${3 + i * 0.8}rem`,
              color: 'var(--primary)',
              left: `${5 + i * 9}%`,
              top: `${50 + (i % 3) * 15}%`,
              userSelect: 'none',
            }}
          >
            {glyph}
          </motion.div>
        ))}
      </div>

      {/* Header */}
      <header style={{ padding: '1rem 0', position: 'relative', zIndex: 1 }}>
        <div className="flex justify-between items-center">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <motion.div 
              whileHover={{ rotate: 12, scale: 1.1 }}
              style={{ 
                width: '44px', 
                height: '44px', 
                background: 'linear-gradient(135deg, var(--primary), #FF9100)', 
                borderRadius: '14px', 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center', 
                color: '#fff', 
                fontSize: '1.3rem',
                boxShadow: '0 8px 20px rgba(var(--primary-rgb), 0.35)'
              }}
            >
              🕉️
            </motion.div>
            <h2 style={{ fontSize: '1.5rem', margin: 0, color: 'var(--text-main)', fontFamily: "'Marcellus', serif" }}>SanskritaAI</h2>
          </div>
          <div className="flex items-center" style={{ gap: '1.5rem' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-dim)', cursor: 'pointer', fontWeight: 600 }}>About</span>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-dim)', cursor: 'pointer', fontWeight: 600 }}>Curriculum</span>
            <button suppressHydrationWarning onClick={toggleTheme} className="theme-toggle" aria-label="Toggle theme" style={{ padding: '8px' }}>
              {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            </button>
          </div>
        </div>
      </header>

      <div className="flex items-center justify-between" style={{ flex: 1, gap: '4rem', position: 'relative', zIndex: 1, flexWrap: 'wrap' }}>
        
        {/* Left Side: Hero Content */}
        <motion.div 
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          style={{ maxWidth: '560px', flex: 1, minWidth: '300px' }}
        >
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="devanagari" 
            style={{ fontSize: '1.1rem', marginBottom: '1rem', letterSpacing: '0.08em', opacity: 0.9 }}
          >
            नमस्ते • Welcome to the Future of Sanskrit
          </motion.div>
          <h1 style={{ fontSize: '3.2rem', lineHeight: '1.1', marginBottom: '1.5rem', color: 'var(--text-main)', fontFamily: "'Marcellus', serif" }}>
            Unlock Ancient Wisdom with{' '}
            <span style={{ 
              background: 'linear-gradient(135deg, var(--primary), var(--accent-gold))',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              Modern Ease.
            </span>
          </h1>
          <p style={{ fontSize: '1.1rem', color: 'var(--text-dim)', marginBottom: '2.5rem', lineHeight: '1.8' }}>
            A distraction-free, intelligent environment designed for the modern learner. Master Sanskrit grammar and vocabulary through adaptive paths that evolve with you.
          </p>
          
          {/* Feature Pills */}
          <div className="flex flex-wrap" style={{ gap: '1rem', marginBottom: '2.5rem' }}>
            <motion.div 
              whileHover={{ scale: 1.05, y: -2 }}
              className="flex items-center gap-2" 
              style={{ 
                color: 'var(--accent)', 
                fontWeight: '700', 
                fontSize: '0.85rem',
                padding: '8px 16px',
                borderRadius: '12px',
                background: 'rgba(var(--accent-rgb), 0.08)',
                border: '1px solid rgba(var(--accent-rgb), 0.15)'
              }}
            >
              <Sparkles size={16} /> AI Guided
            </motion.div>
            <motion.div 
              whileHover={{ scale: 1.05, y: -2 }}
              className="flex items-center gap-2" 
              style={{ 
                color: 'var(--secondary)', 
                fontWeight: '700', 
                fontSize: '0.85rem',
                padding: '8px 16px',
                borderRadius: '12px',
                background: 'rgba(var(--secondary-rgb), 0.08)',
                border: '1px solid rgba(var(--secondary-rgb), 0.15)'
              }}
            >
              <BookOpen size={16} /> 20+ Lessons
            </motion.div>
            <motion.div 
              whileHover={{ scale: 1.05, y: -2 }}
              className="flex items-center gap-2" 
              style={{ 
                color: 'var(--primary)', 
                fontWeight: '700', 
                fontSize: '0.85rem',
                padding: '8px 16px',
                borderRadius: '12px',
                background: 'var(--primary-light)',
                border: '1px solid var(--border-soft)'
              }}
            >
              <Globe size={16} /> Global Access
            </motion.div>
          </div>

          {/* Stats Row */}
          <div className="flex" style={{ gap: '2rem' }}>
            {[
              { num: "20+", label: "Lessons", icon: GraduationCap },
              { num: "1000+", label: "Words", icon: Brain },
              { num: "∞", label: "Practice", icon: Users },
            ].map((stat, i) => (
              <motion.div 
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + i * 0.15 }}
              >
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1.2 }}>{stat.num}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Right Side: Auth Card */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="zen-card-static"
          style={{ 
            width: '100%', 
            maxWidth: '420px', 
            padding: '2.5rem',
            boxShadow: '0 30px 60px -12px rgba(var(--primary-rgb), 0.12), 0 18px 36px -18px rgba(0,0,0,0.15)',
          }}
        >
          <div className="flex mb-8" style={{ borderBottom: '1px solid var(--border-soft)', gap: 0 }}>
            <button 
              suppressHydrationWarning
              onClick={() => setIsLogin(true)} 
              style={{ 
                flex: 1, 
                background: 'none', 
                border: 'none',
                color: isLogin ? 'var(--primary)' : 'var(--text-light)', 
                borderBottom: isLogin ? '2px solid var(--primary)' : '2px solid transparent', 
                padding: '15px', 
                fontSize: '1rem', 
                cursor: 'pointer', 
                transition: 'all 0.3s', 
                fontWeight: isLogin ? '700' : '400',
                fontFamily: 'inherit'
              }}
            >
              <span className="flex items-center justify-center gap-2"><LogIn size={16} /> Sign In</span>
            </button>
            <button 
              suppressHydrationWarning
              onClick={() => setIsLogin(false)} 
              style={{ 
                flex: 1, 
                background: 'none', 
                border: 'none',
                color: !isLogin ? 'var(--primary)' : 'var(--text-light)', 
                borderBottom: !isLogin ? '2px solid var(--primary)' : '2px solid transparent', 
                padding: '15px', 
                fontSize: '1rem', 
                cursor: 'pointer', 
                transition: 'all 0.3s', 
                fontWeight: !isLogin ? '700' : '400',
                fontFamily: 'inherit'
              }}
            >
              <span className="flex items-center justify-center gap-2"><UserPlus size={16} /> Register</span>
            </button>
          </div>

          <AnimatePresence mode="wait">
            <motion.form 
              key={isLogin ? 'login' : 'signup'}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              onSubmit={handleSubmit} 
              className="flex flex-col gap-6"
            >
              <div className="flex flex-col gap-2">
                <input 
                  suppressHydrationWarning
                  type="text" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Username"
                  required
                />
              </div>

              <div className="flex flex-col gap-2">
                <input 
                  suppressHydrationWarning
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  required
                />
              </div>

              {!isLogin && (
                <>
                  {/* Password guidance, shown only while creating an account.
                      The first two rules are compulsory and block submission;
                      the rest are advice the user may ignore. */}
                  <div
                    style={{
                      border: `1px solid ${password && passwordProblem ? "rgba(231, 76, 60, 0.45)" : "var(--border-soft)"}`,
                      background:
                        password && passwordProblem
                          ? "rgba(231, 76, 60, 0.06)"
                          : "rgba(127, 127, 127, 0.05)",
                      borderRadius: "12px",
                      padding: "12px 14px",
                    }}
                  >
                    <p
                      style={{
                        fontSize: "0.78rem",
                        fontWeight: 700,
                        marginBottom: "8px",
                        color: "var(--text-main, var(--text-dim))",
                      }}
                    >
                      Create a strong password
                    </p>
                    <ul
                      style={{
                        listStyle: "none",
                        padding: 0,
                        margin: 0,
                        display: "flex",
                        flexDirection: "column",
                        gap: "4px",
                      }}
                    >
                      {passwordRules.map((rule) => (
                        <li
                          key={rule.id}
                          style={{
                            fontSize: "0.75rem",
                            display: "flex",
                            alignItems: "center",
                            gap: "7px",
                            color: rule.met
                              ? "var(--accent)"
                              : rule.required
                                ? "#e74c3c"
                                : "var(--text-dim)",
                          }}
                        >
                          <span aria-hidden="true" style={{ width: "0.9em", display: "inline-block" }}>
                            {rule.met ? "✓" : rule.required ? "✕" : "○"}
                          </span>
                          <span>
                            {rule.label}
                            {rule.required ? " — required" : " — optional"}
                          </span>
                        </li>
                      ))}
                    </ul>
                    {password && passwordProblem && (
                      <p
                        role="alert"
                        style={{ fontSize: "0.75rem", color: "#e74c3c", margin: "8px 0 0", fontWeight: 600 }}
                      >
                        Password too weak: add {passwordProblem}.
                      </p>
                    )}
                  </div>

                  <input 
                    suppressHydrationWarning
                    type="password" 
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm Password"
                    required
                  />
                  <select value={role} onChange={(e) => setRole(e.target.value)}>
                    <option value="student">Learning Path: Student</option>
                    <option value="teacher">Learning Path: Educator</option>
                  </select>
                </>
              )}

              {error && (
                <motion.p 
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{ 
                    color: error.includes('created') ? 'var(--accent)' : '#e74c3c', 
                    fontSize: '0.85rem', 
                    textAlign: 'center',
                    padding: '8px 12px',
                    borderRadius: '10px',
                    background: error.includes('created') ? 'rgba(var(--accent-rgb), 0.08)' : 'rgba(231, 76, 60, 0.08)',
                  }}
                >
                  {error}
                </motion.p>
              )}

              <button suppressHydrationWarning type="submit" className="btn-primary" disabled={loading || signupBlocked}>
                {loading ? "Please wait..." : isLogin ? "Go to Dashboard" : "Create My Account"}
              </button>

              {isLogin && (
                <div style={{ textAlign: 'center' }}>
                  <button 
                    suppressHydrationWarning
                    type="button" 
                    onClick={async () => { 
                      setUsername("demo"); 
                      setPassword("demo123"); 
                      setLoading(true);
                      try {
                        await login("demo", "demo123");
                        router.push("/dashboard");
                      } finally {
                        setLoading(false);
                      }
                    }} 
                    style={{ 
                      background: 'none', 
                      color: 'var(--text-dim)', 
                      border: 'none', 
                      cursor: 'pointer', 
                      fontSize: '0.85rem',
                      fontFamily: 'inherit',
                      textDecoration: 'none',
                      fontWeight: 600,
                      transition: 'color 0.2s'
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--primary)')}
                    onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-dim)')}
                  >
                    ✨ Quick-start as Guest
                  </button>
                </div>
              )}
            </motion.form>
          </AnimatePresence>
        </motion.div>

      </div>

      <footer style={{ padding: '2rem 0', textAlign: 'center', color: 'var(--text-light)', fontSize: '0.8rem', position: 'relative', zIndex: 1 }}>
        🕉️ Pavitram Sanskritam • Designed with serenity in mind
      </footer>
    </main>
  );
}
