"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { motion } from "framer-motion";
import { 
  Users, 
  Settings, 
  ShieldAlert,
  Loader2
} from "lucide-react";

export default function Admin() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (!storedUser) {
      router.push("/");
      return;
    }
    const userData = JSON.parse(storedUser);
    if (userData.role !== 'admin') {
      router.push("/dashboard");
      return;
    }
    setUser(userData);
    setLoading(false);
  }, [router]);

  if (loading || !user) return null;

  return (
    <div className="page-layout">
      <Sidebar user={user} />
      
      <main className="main-content">
        <motion.header 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ marginBottom: '40px' }}
        >
          <div className="flex items-center gap-3">
             <ShieldAlert size={32} color="#e74c3c" />
             <h1 style={{ fontSize: '2.5rem' }}>Management Console</h1>
          </div>
          <p style={{ color: 'var(--text-dim)' }}>Administrator portal for user monitoring and content archival.</p>
        </motion.header>

        <div className="grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '30px', marginBottom: '40px' }}>
          {[
            { label: "Active Learners", value: "—", icon: Users, color: "#3498db" },
            { label: "Pending Modules", value: "—", icon: Settings, color: "var(--primary)" },
            { label: "System Health", value: "—", icon: ShieldAlert, color: "#27ae60" }
          ].map((stat, i) => (
            <motion.div 
              key={stat.label}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.1 }}
              className="zen-card"
              style={{ padding: '30px' }}
            >
               <div className="flex justify-between items-center">
                  <div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: '600', textTransform: 'uppercase' }}>{stat.label}</div>
                    <div style={{ fontSize: '1.8rem', fontWeight: '800', marginTop: '4px' }}>{stat.value}</div>
                  </div>
                  <div style={{ color: stat.color }}>
                    <stat.icon size={28} />
                  </div>
               </div>
            </motion.div>
          ))}
        </div>

        <section className="grid" style={{ gridTemplateColumns: '1.5fr 1fr', gap: '30px' }}>
          <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="zen-card" style={{ padding: '40px' }}>
            <h3 className="mb-6">Global Registry</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border-soft)' }}>
                    <th style={{ padding: '16px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>IDENTIFIER</th>
                    <th style={{ padding: '16px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>STANCE</th>
                    <th style={{ padding: '16px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>ACTIVITY</th>
                    <th style={{ padding: '16px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>COMMAND</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td colSpan={4} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.9rem' }}>
                      No user records to display — no admin reporting endpoint exists yet.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="zen-card" style={{ padding: '40px' }}>
            <h3 className="mb-8">Resource Injection</h3>
            {/* Honest empty state. The previous version rendered a Module Title
                input, a Cognitive Level select and a "Manifest Resource" button
                with no state binding, no onClick handler and no backend
                endpoint — it looked functional but did nothing when clicked. */}
            <div
              role="status"
              style={{
                padding: '24px',
                borderRadius: '16px',
                background: 'var(--bg-main)',
                border: '1px dashed var(--border-soft)',
                textAlign: 'center',
                color: 'var(--text-dim)',
                fontSize: '0.9rem',
                lineHeight: '1.6',
              }}
            >
              Content authoring is not available yet.
              <br />
              <span style={{ fontSize: '0.8rem' }}>
                No resource-creation endpoint exists, so the form that used to sit here
                was removed rather than left as a non-functional control.
              </span>
            </div>
          </motion.div>
        </section>
      </main>
    </div>
  );
}
