// frontend/src/lib/audioPronunciation.ts
"use client";

// Simple wrapper around the Web Speech API for Sanskrit pronunciation.
// It selects an appropriate voice (if available) and provides utilities
// to speak, stop, and query playing state. All functions are safe‑guards
// for environments where speechSynthesis is unavailable.

export type SpeechStatus = "idle" | "speaking";

let currentUtterance: SpeechSynthesisUtterance | null = null;
let status: SpeechStatus = "idle";

function getSanskritVoice(): SpeechSynthesisVoice | null {
  if (typeof window === "undefined" || !window.speechSynthesis) return null;
  const voices = window.speechSynthesis.getVoices();
  // Only an explicitly Sanskrit browser voice is suitable for this content.
  const sanskrit = voices.find((v) => {
    const language = v.lang.toLowerCase();
    return language === "sa" || language === "sa-in" || language.startsWith("sa-");
  });
  if (sanskrit) return sanskrit;
  // Do not substitute a Hindi or default voice: neither is Sanskrit.
  // No suitable Indic voice found – fall back to default.
  return null;
}

export function hasSanskritVoice(): boolean {
  return getSanskritVoice() !== null;
}

export function speak(text: string, onEnd?: () => void) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  const voice = getSanskritVoice();
  if (!voice) {
    onEnd?.();
    return;
  }
  // Cancel any previous speech.
  stop();

  const utter = new SpeechSynthesisUtterance(text);
  utter.voice = voice;
  // Slightly adjust pitch/rate for clearer Sanskrit pronunciation.
  utter.rate = 0.9;
  utter.pitch = 1.0;

  utter.onend = () => {
    status = "idle";
    currentUtterance = null;
    if (onEnd) onEnd();
  };
  utter.onerror = () => {
    status = "idle";
    currentUtterance = null;
    if (onEnd) onEnd();
  };

  currentUtterance = utter;
  status = "speaking";
  window.speechSynthesis.speak(utter);
}

export function stop() {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  if (currentUtterance) {
    window.speechSynthesis.cancel();
    currentUtterance = null;
  }
  status = "idle";
}

export function isSpeaking(): boolean {
  return status === "speaking";
}
