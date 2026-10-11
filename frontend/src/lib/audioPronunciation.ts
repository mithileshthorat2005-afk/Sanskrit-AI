// frontend/src/lib/audioPronunciation.ts
"use client";

// Web Speech API utility for Sanskrit pronunciation.
// Provides voice detection, realistic Indic/Devanagari phonetics fallback disclosure,
// numeral-to-spoken word mappings, and resilient utterance lifecycle handling.

export type SpeechStatus = "idle" | "speaking";

export interface VoiceInfo {
  isSupported: boolean;
  hasSanskritVoice: boolean;
  hasIndicVoice: boolean;
  selectedVoice: SpeechSynthesisVoice | null;
  voiceName: string;
  voiceLang: string;
  isApproximate: boolean;
  statusMessage: string;
}

let currentUtterance: SpeechSynthesisUtterance | null = null;
let status: SpeechStatus = "idle";

/**
 * Standard Sanskrit numeral spoken words.
 * In Sanskrit tradition, isolated digits and numerals correspond to specific Sanskrit words.
 */
export const SANSKRIT_NUMERAL_WORDS: Record<string, string> = {
  "०": "शून्यम्",
  "१": "एकम्",
  "२": "द्वे",
  "३": "त्रीणि",
  "४": "चत्वारि",
  "५": "पञ्च",
  "६": "षट्",
  "७": "सप्त",
  "८": "अष्ट",
  "९": "नव",
  "१०": "दश",
  "0": "शून्यम्",
  "1": "एकम्",
  "2": "द्वे",
  "3": "त्रीणि",
  "4": "चत्वारि",
  "5": "पञ्च",
  "6": "षट्",
  "7": "सप्त",
  "8": "अष्ट",
  "9": "नव",
  "10": "दश",
};

/**
 * Maps raw characters or punctuation to their speakable Sanskrit equivalents:
 * - Single numerals -> authentic Sanskrit spoken names
 * - Solitary purna virama ('।' or '॥') -> empty (pause symbol, not a spoken word)
 * - Sentences and words -> returned cleanly for speech synthesis
 */
export function getPronounceableText(text: string): string {
  if (!text) return "";
  const trimmed = text.trim();
  if (SANSKRIT_NUMERAL_WORDS[trimmed]) {
    return SANSKRIT_NUMERAL_WORDS[trimmed];
  }
  // Punctuation marks alone do not have spoken lexical readings
  if (trimmed === "।" || trimmed === "॥" || trimmed === "." || trimmed === ",") {
    return "";
  }
  return trimmed;
}

/**
 * Analyzes browser voices to identify explicit Sanskrit or Indic (Devanagari) voices.
 * Adheres strictly to non-silent fallback rules: if an Indic voice is selected,
 * the UI is informed that this is an Indic phonetic engine rather than native classical Sanskrit.
 */
export function getSpeechVoiceInfo(): VoiceInfo {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    return {
      isSupported: false,
      hasSanskritVoice: false,
      hasIndicVoice: false,
      selectedVoice: null,
      voiceName: "Unavailable",
      voiceLang: "",
      isApproximate: false,
      statusMessage: "Web Speech API is not supported in this browser."
    };
  }

  const voices = window.speechSynthesis.getVoices();

  // Tier 1: Explicit Sanskrit voice (e.g. sa, sa-IN, sa_IN, or name containing Sanskrit)
  const sanskritVoice = voices.find((v) => {
    const lang = (v.lang || "").toLowerCase();
    const name = (v.name || "").toLowerCase();
    return (
      lang === "sa" ||
      lang === "sa-in" ||
      lang === "sa_in" ||
      lang.startsWith("sa-") ||
      lang.startsWith("sa_") ||
      name.includes("sanskrit") ||
      name.includes("संस्कृत")
    );
  });

  if (sanskritVoice) {
    return {
      isSupported: true,
      hasSanskritVoice: true,
      hasIndicVoice: false,
      selectedVoice: sanskritVoice,
      voiceName: sanskritVoice.name,
      voiceLang: sanskritVoice.lang,
      isApproximate: false,
      statusMessage: `Native Sanskrit voice: ${sanskritVoice.name} (${sanskritVoice.lang})`
    };
  }

  // Tier 2: Indic / Devanagari voice (e.g. Hindi or Marathi which share the Devanagari script phonemes)
  // Transparently classified as an approximate phonetic fallback.
  const indicVoice = voices.find((v) => {
    const lang = (v.lang || "").toLowerCase();
    const name = (v.name || "").toLowerCase();
    return (
      lang === "hi-in" ||
      lang === "hi_in" ||
      lang.startsWith("hi-") ||
      lang === "hi" ||
      lang === "mr-in" ||
      lang === "mr_in" ||
      lang.startsWith("mr-") ||
      name.includes("hindi") ||
      name.includes("marathi")
    );
  });

  if (indicVoice) {
    return {
      isSupported: true,
      hasSanskritVoice: false,
      hasIndicVoice: true,
      selectedVoice: indicVoice,
      voiceName: indicVoice.name,
      voiceLang: indicVoice.lang,
      isApproximate: true,
      statusMessage: `Indic Devanagari phonetic engine: ${indicVoice.name} (${indicVoice.lang}) [No native Sanskrit voice detected in browser]`
    };
  }

  // Tier 3: Speech synthesis available, using sa-IN locale tag
  return {
    isSupported: true,
    hasSanskritVoice: false,
    hasIndicVoice: false,
    selectedVoice: null,
    voiceName: "System Default (sa-IN)",
    voiceLang: "sa-IN",
    isApproximate: true,
    statusMessage: "Browser speech synthesis with 'sa-IN' locale (No dedicated Sanskrit voice enumerated)"
  };
}

export function hasSanskritVoice(): boolean {
  return getSpeechVoiceInfo().hasSanskritVoice;
}

export function canPlayAudio(): boolean {
  if (typeof window === "undefined" || !window.speechSynthesis) return false;
  return true;
}

/**
 * Speaks the provided Sanskrit text, letter, or numeral.
 * Cancels any active utterance, resumes synthesis if stalled,
 * sets language parameters, and provides completion/error callbacks.
 */
export function speak(
  text: string,
  onEnd?: () => void,
  onError?: (err: unknown) => void
) {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    onEnd?.();
    return;
  }

  const cleanText = getPronounceableText(text);
  if (!cleanText) {
    onEnd?.();
    return;
  }

  // Stop any active utterance before initiating a new one
  stop();

  try {
    const voiceInfo = getSpeechVoiceInfo();
    const utter = new SpeechSynthesisUtterance(cleanText);

    if (voiceInfo.selectedVoice) {
      utter.voice = voiceInfo.selectedVoice;
      utter.lang = voiceInfo.selectedVoice.lang || "sa-IN";
    } else {
      utter.lang = "sa-IN";
    }

    // Deliberate cadence suited for Sanskrit pronunciation
    utter.rate = 0.85;
    utter.pitch = 1.0;

    let finished = false;
    let watchdogTimer: NodeJS.Timeout | null = null;

    const cleanup = () => {
      if (finished) return;
      finished = true;
      status = "idle";
      currentUtterance = null;
      if (watchdogTimer) clearTimeout(watchdogTimer);
    };

    utter.onstart = () => {
      status = "speaking";
    };

    utter.onend = () => {
      cleanup();
      if (onEnd) onEnd();
    };

    utter.onerror = (e) => {
      console.warn("[SanskritAudio] Speech synthesis error:", e);
      cleanup();
      if (onError) onError(e);
      if (onEnd) onEnd();
    };

    currentUtterance = utter;
    status = "speaking";

    // 15-second watchdog timer to guarantee recovery if onend fails to fire in browser
    watchdogTimer = setTimeout(() => {
      if (status === "speaking" && currentUtterance === utter) {
        console.warn("[SanskritAudio] Watchdog reset active utterance.");
        cleanup();
        if (onEnd) onEnd();
      }
    }, 15000);

    // Unpause synthesis if WebKit/Blink is in a paused state
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }

    window.speechSynthesis.speak(utter);
  } catch (err) {
    console.error("[SanskritAudio] Failed to speak utterance:", err);
    status = "idle";
    currentUtterance = null;
    if (onError) onError(err);
    if (onEnd) onEnd();
  }
}

export function stop() {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  try {
    window.speechSynthesis.cancel();
  } catch (e) {
    console.warn("[SanskritAudio] Error cancelling speech:", e);
  }
  currentUtterance = null;
  status = "idle";
}

export function isSpeaking(): boolean {
  return status === "speaking" || (typeof window !== "undefined" && Boolean(window.speechSynthesis?.speaking));
}
