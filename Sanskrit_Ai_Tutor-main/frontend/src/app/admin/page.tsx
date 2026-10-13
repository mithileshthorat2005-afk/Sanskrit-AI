"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { motion } from "framer-motion";
import { 
  Users, 
  Settings, 
  PlusCircle, 
  Trash2, 
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
            { label: "Active Learners", value: "1,240", icon: Users, color: "#3498db" },
            { label: "Pending Modules", value: "4", icon: Settings, color: "var(--primary)" },
            { label: "System Health", value: "Optimal", icon: ShieldAlert, color: "#27ae60" }
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
                  {[
                    { id: "aryaman_99", role: "Student", status: "Active" },
                    { id: "ved_prakash", role: "Teacher", status: "Idle" },
                    { id: "soma_dev", role: "Student", status: "Active" }
                  ].map((learner, i) => (
                    <tr key={learner.id} style={{ borderBottom: '1px solid var(--border-soft)' }}>
                      <td style={{ padding: '16px', fontWeight: '600' }}>{learner.id}</td>
                      <td style={{ padding: '16px', fontSize: '0.9rem' }}>{learner.role}</td>
                      <td style={{ padding: '16px' }}>
                        <span style={{ padding: '4px 10px', borderRadius: '20px', fontSize: '0.75rem', background: '#eafaf1', color: '#27ae60' }}>{learner.status}</span>
                      </td>
                      <td style={{ padding: '16px' }}>
                        <button style={{ background: 'none', border: 'none', color: '#e74c3c', cursor: 'pointer' }}><Trash2 size={16} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="zen-card" style={{ padding: '40px' }}>
            <h3 className="mb-8">Resource Injection</h3>
            <div className="flex flex-col gap-6">
               <div>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-dim)', display: 'block', marginBottom: '8px' }}>Module Title</label>
                  <input type="text" placeholder="e.g. Advaita Philosophy" style={{ width: '100%' }} />
               </div>
               <div>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-dim)', display: 'block', marginBottom: '8px' }}>Cognitive Level</label>
                  <select style={{ width: '100%' }}>
                    <option>Beginner</option>
                    <option>Intermediate</option>
                    <option>Advanced</option>
                  </select>
               </div>
               <button className="btn-primary" style={{ width: '100%', marginTop: '10px' }}>
                 <PlusCircle size={18} /> Manifest Resource
               </button>
            </div>
          </motion.div>
        </section>
      </main>
    </div>
  );
}
