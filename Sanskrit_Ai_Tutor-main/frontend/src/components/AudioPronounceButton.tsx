// frontend/src/components/AudioPronounceButton.tsx
"use client";

import React, { useState, useEffect } from "react";
import { Volume2, VolumeX } from "lucide-react";
import {
  speak,
  stop,
  isSpeaking,
  canPlayAudio,
  getSpeechVoiceInfo,
  getPronounceableText,
  VoiceInfo
} from "@/lib/audioPronunciation";

export interface AudioPronounceButtonProps {
  text: string;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
  title?: string;
  label?: string;
}

/**
 * Reusable button that plays Sanskrit text using the Web Speech API.
 * - Clicking while idle starts playback.
 * - Clicking while speaking stops playback.
 * - Accurately reports voice status without silently misrepresenting speech engines.
 */
export default function AudioPronounceButton({
  text,
  size = 18,
  className = "",
  style,
  title: customTitle,
  label,
}: AudioPronounceButtonProps) {
  const [playing, setPlaying] = useState(false);
  const [voiceInfo, setVoiceInfo] = useState<VoiceInfo>({
    isSupported: true,
    hasSanskritVoice: false,
    hasIndicVoice: false,
    selectedVoice: null,
    voiceName: "Detecting...",
    voiceLang: "",
    isApproximate: true,
    statusMessage: "Initializing speech engine..."
  });

  useEffect(() => {
    const updateVoiceInfo = () => {
      setVoiceInfo(getSpeechVoiceInfo());
    };

    updateVoiceInfo();

    if (typeof window !== "undefined" && window.speechSynthesis) {
      if ("onvoiceschanged" in window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = updateVoiceInfo;
      }
      window.speechSynthesis.addEventListener?.("voiceschanged", updateVoiceInfo);
    }

    return () => {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.removeEventListener?.("voiceschanged", updateVoiceInfo);
      }
    };
  }, []);

  // Sync state if speech stops externally or finishes naturally
  useEffect(() => {
    if (!playing) return;
    const intervalId = setInterval(() => {
      if (!isSpeaking()) {
        setPlaying(false);
      }
    }, 250);
    return () => clearInterval(intervalId);
  }, [playing]);

  const speakableText = getPronounceableText(text);
  if (!speakableText) return null;

  const isSupported = canPlayAudio() && voiceInfo.isSupported;

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!isSupported) return;

    if (playing) {
      stop();
      setPlaying(false);
    } else {
      setPlaying(true);
      speak(
        speakableText,
        () => setPlaying(false),
        () => setPlaying(false)
      );
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      e.stopPropagation();
      handleClick(e as unknown as React.MouseEvent);
    }
  };

  // Determine honest, informative tooltip
  const getTooltip = () => {
    if (customTitle) return customTitle;
    if (!isSupported) {
      return "Speech synthesis is not supported in this browser.";
    }
    if (playing) {
      return `Stop playing pronunciation of "${speakableText}"`;
    }
    if (voiceInfo.hasSanskritVoice) {
      return `Play Sanskrit pronunciation (Native Sanskrit voice: ${voiceInfo.voiceName})`;
    }
    if (voiceInfo.hasIndicVoice) {
      return `Play Sanskrit pronunciation (Indic phonetic engine: ${voiceInfo.voiceName}; browser lacks native Sanskrit voice)`;
    }
    return `Play Sanskrit pronunciation (Speech synthesis: sa-IN locale)`;
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      disabled={!isSupported}
      className={className}
      aria-label={getTooltip()}
      title={getTooltip()}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: label ? "6px" : undefined,
        padding: "4px",
        borderRadius: "50%",
        border: "none",
        background: playing ? "rgba(var(--primary-rgb), 0.12)" : "transparent",
        color: playing ? "var(--primary)" : "var(--text-light)",
        cursor: isSupported ? "pointer" : "not-allowed",
        opacity: isSupported ? 1 : 0.45,
        flexShrink: 0,
        transition: "all 0.2s ease",
        ...style,
      }}
    >
      {playing ? (
        <VolumeX size={size} style={{ color: "var(--primary)" }} />
      ) : (
        <Volume2 size={size} />
      )}
      {label && (
        <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{label}</span>
      )}
    </button>
  );
}

