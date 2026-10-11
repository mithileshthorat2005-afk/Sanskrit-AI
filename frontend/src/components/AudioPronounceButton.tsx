// frontend/src/components/AudioPronounceButton.tsx
"use client";

import { useState, useEffect } from "react";
import { Volume2, VolumeX } from "lucide-react";
import { speak, stop, isSpeaking, hasSanskritVoice } from "@/lib/audioPronunciation";

/**
 * Reusable button that plays Sanskrit text using the Web Speech API.
 * - Clicking while idle starts playback.
 * - Clicking while speaking stops playback.
 */
export default function AudioPronounceButton({
  text,
  size = 18,
  className = "",
}: {
  text: string;
  size?: number;
  className?: string;
}) {
  const [playing, setPlaying] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(false);

  useEffect(() => {
    const updateVoiceAvailability = () => setVoiceAvailable(hasSanskritVoice());
    updateVoiceAvailability();
    window.speechSynthesis?.addEventListener("voiceschanged", updateVoiceAvailability);
    return () => window.speechSynthesis?.removeEventListener("voiceschanged", updateVoiceAvailability);
  }, []);

  // Sync state if speech stops externally.
  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      if (!isSpeaking()) setPlaying(false);
    }, 300);
    return () => clearInterval(id);
  }, [playing]);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!voiceAvailable) return;
    if (playing) {
      stop();
      setPlaying(false);
    } else {
      speak(text, () => setPlaying(false));
      setPlaying(true);
    }
  };

  if (!text?.trim()) return null;

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={!voiceAvailable}
      className={className}
      aria-label={voiceAvailable ? (playing ? "Stop Sanskrit pronunciation" : "Play Sanskrit pronunciation") : "Sanskrit speech voice is not available in this browser"}
      title={voiceAvailable ? (playing ? "Stop pronunciation" : "Play pronunciation") : "A Sanskrit speech voice is not available in this browser"}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "4px",
        borderRadius: "50%",
        border: "none",
        background: "transparent",
        color: playing ? "var(--primary)" : "var(--text-light)",
        cursor: voiceAvailable ? "pointer" : "not-allowed",
        opacity: voiceAvailable ? 1 : 0.45,
        flexShrink: 0,
      }}
    >
      {playing ? <VolumeX size={size} /> : <Volume2 size={size} />}
    </button>
  );
}

