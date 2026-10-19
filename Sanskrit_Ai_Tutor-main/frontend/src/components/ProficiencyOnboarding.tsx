"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

/**
 * One-off proficiency prompt for brand-new accounts.
 *
 * Whether the prompt is due is decided entirely by the server: the backend
 * stores an `onboarding_completed` flag per learner in SQLite, and this
 * component re-reads it on mount. Nothing is remembered in localStorage,
 * sessionStorage or a cookie, so a refresh, a new tab, a fresh login or a
 * cleared browser cache can never re-show the prompt to somebody who has
 * already answered, and can never hide it from somebody who has not.
 *
 * It renders nothing until an authenticated user exists, which is why it can be
 * mounted in the root layout without ever appearing on the login page.
 */

const OPTIONS = [
  {
    value: "beginner",
    label: "New to Sanskrit",
    description: "Starting from the alphabet. Devanagari and basic sentences are new to you.",
  },
  {
    value: "intermediate",
    label: "Intermediate",
    description: "You know the alphabet and basic sentences, and are working through cases, tenses and sandhi.",
  },
  {
    value: "advanced",
    label: "Advanced",
    description: "You are comfortable with compounds, participles and prosody and want harder material from the start.",
  },
] as const;

export default function ProficiencyOnboarding() {
  const { user, loading: authLoading, refreshUser } = useAuth();

  // Mounted-gated so the server render and the first client render both draw
  // nothing, which keeps the modal out of SSR entirely.
  const [mounted, setMounted] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    // No user means no session, so the prompt stays hidden. `done` is set as
    // soon as the server reports the learner onboarded, and the effect then
    // stops asking.
    if (!mounted || authLoading || !user) return;
    let cancelled = false;

    (async () => {
      try {
        const state = await api.user.getProficiency();
        if (cancelled) return;
        // Only a positive "you still owe an answer" opens the prompt. If the
        // request fails we know nothing, so we neither prompt nor block the
        // learner — the app stays usable.
        if (state && state.onboarding_completed === false) {
          setOpen(true);
        }
      } catch {
        // Leave the app usable: no prompt, no error banner.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [mounted, authLoading, user]);

  if (!mounted || !user || !open) return null;

  const choose = async (value: string) => {
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      await api.user.saveProficiency(value);
      // Only reached on success. A failed save leaves the dialog open and the
      // server still un-onboarded, so nothing is optimistically marked done and
      // a retry cannot initialise mastery twice.
      setOpen(false);
      void refreshUser();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "We could not save your choice. Please try again.";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      suppressHydrationWarning
      role="dialog"
      aria-modal="true"
      aria-labelledby="proficiency-title"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 2000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1.5rem",
        background: "rgba(15, 23, 42, 0.55)",
      }}
    >
      <div
        className="zen-card-static"
        style={{
          width: "100%",
          maxWidth: "560px",
          padding: "2rem",
          background: "var(--bg-card)",
          borderRadius: "20px",
          border: "1px solid var(--border-soft)",
          boxShadow: "0 30px 60px -12px rgba(0, 0, 0, 0.35)",
        }}
      >
        <h2
          id="proficiency-title"
          style={{
            margin: "0 0 0.5rem",
            fontSize: "1.35rem",
            color: "var(--text-main)",
            fontFamily: "'Marcellus', serif",
          }}
        >
          What is your current Sanskrit proficiency level?
        </h2>
        <p
          style={{
            margin: "0 0 1.5rem",
            fontSize: "0.88rem",
            lineHeight: 1.6,
            color: "var(--text-dim)",
          }}
        >
          This sets where your practice starts. You answer it once &mdash; it
          cannot be changed later, and it never affects other learners.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {OPTIONS.map((option) => (
            <button
              key={option.value}
              suppressHydrationWarning
              type="button"
              disabled={saving}
              onClick={() => choose(option.value)}
              style={{
                textAlign: "left",
                padding: "0.9rem 1rem",
                borderRadius: "12px",
                border: "1px solid var(--border-soft)",
                background: "var(--bg-main)",
                color: "var(--text-main)",
                cursor: saving ? "wait" : "pointer",
                opacity: saving ? 0.6 : 1,
                fontFamily: "inherit",
              }}
            >
              <div style={{ fontWeight: 700, fontSize: "0.98rem", marginBottom: "0.25rem" }}>
                {option.label}
              </div>
              <div style={{ fontSize: "0.8rem", lineHeight: 1.5, color: "var(--text-dim)" }}>
                {option.description}
              </div>
            </button>
          ))}
        </div>

        {error && (
          <p
            role="alert"
            style={{
              margin: "1rem 0 0",
              fontSize: "0.82rem",
              fontWeight: 600,
              color: "#e74c3c",
              background: "rgba(231, 76, 60, 0.08)",
              borderRadius: "10px",
              padding: "8px 12px",
            }}
          >
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
