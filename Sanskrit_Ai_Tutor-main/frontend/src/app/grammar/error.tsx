"use client";

// Route-level error boundary for /grammar (Next.js App Router `error.tsx`).
//
// A render-time exception inside the checker used to blank the whole app shell
// because the route had no boundary. This catches it, shows a readable message,
// and offers a retry without losing the sidebar/shell.
import { useEffect } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, RotateCcw } from "lucide-react";

export default function GrammarError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Grammar route error:", error);
  }, [error]);

  return (
    <div className="page-layout">
      <main className="main-content">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="zen-card"
          role="alert"
          style={{
            padding: '36px',
            marginTop: '60px',
            border: '1px solid rgba(192, 90, 43, 0.35)',
          }}
        >
          <div
            className="flex items-center gap-3"
            style={{ color: 'var(--primary)', marginBottom: '12px' }}
          >
            <AlertTriangle size={22} />
            <h2 style={{ margin: 0, fontSize: '1.3rem' }}>Something went wrong in the grammar checker</h2>
          </div>

          <p style={{ color: 'var(--text-dim)', fontSize: '0.95rem', marginBottom: '24px' }}>
            The analysis could not be displayed. Nothing was saved or scored for this attempt.
            Your previous analyses are still available.
          </p>

          <button
            className="btn-primary"
            onClick={reset}
            style={{
              padding: '12px 26px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <RotateCcw size={16} />
            <span>Try again</span>
          </button>

          {error?.digest && (
            <div style={{ marginTop: '20px', fontSize: '0.75rem', color: 'var(--text-light)' }}>
              Reference: {error.digest}
            </div>
          )}
        </motion.div>
      </main>
    </div>
  );
}
