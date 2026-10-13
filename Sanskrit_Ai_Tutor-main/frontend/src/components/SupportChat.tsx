"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import { 
  MessageCircle, 
  X,
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

interface SupportChatProps {
  autoOpen?: boolean;
  isOpen?: boolean;
  onOpen?: () => void;
  onClose?: () => void;
}

/**
 * Fixed-position support chatbot for Sanskrit AI Tutor.
 * Floating button at bottom-right, panel anchors bottom-right above the button.
 * Users can only select from predefined questions - no free-text input.
 * Uses the existing Groq API from the backend translator integration.
 */
export default function SupportChat({ autoOpen = false, isOpen: propIsOpen, onOpen: propOnOpen, onClose: propOnClose }: SupportChatProps = {}) {
  // Use prop isOpen if provided (controlled mode), otherwise manage internal state
  const [isOpen, setIsOpen] = useState<boolean>(!!propIsOpen);
  const shouldUseProp = !!propIsOpen;
  
  const { user, token, loading: authLoading, login, signup, logout } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fixed predefined questions about actual Sanskrit AI Tutor features
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>(() => {
    return [
      "How do I use the Sanskrit Grammar Checker?",
      "How do I translate English into Sanskrit?",
      "How do I use lessons and quizzes?",
      "How can I track my learning progress?",
      "How do I use Sanskrit pronunciation and audio?",
      "What should I do if a feature is not working?",
    ];
  });

  // Ref for the floating button
  const floatingRef = useRef<HTMLDivElement>(null);
  // Ref for the chat panel
  const panelRef = useRef<HTMLDivElement>(null);

  // Set fixed bottom-right position
  const [buttonPosition, setButtonPosition] = useState({ x: 0, y: 0 });
  const [panelPosition, setPanelPosition] = useState({ x: 0, y: 0 });

  // Initialize positions from localStorage or defaults
  useEffect(() => {
    const saved = localStorage.getItem("supportChatPosition");
    if (saved) {
      const { x, y } = JSON.parse(saved);
      setButtonPosition({ x, y });
      setPanelPosition({ x: x - 240, y: y - 320 }); // panel offset from button
    } else {
      // Default to bottom-right of viewport with margins
      setButtonPosition({ x: window.innerWidth - 60, y: window.innerHeight - 60 });
      setPanelPosition({ x: window.innerWidth - 280, y: window.innerHeight - 380 });
    }
  }, []);

  // Save positions on close
  useEffect(() => {
    if (!isOpen) {
      const save = () => {
        localStorage.setItem("supportChatPosition", JSON.stringify(buttonPosition));
      };
      if (floatingRef.current) {
        floatingRef.current.addEventListener("mouseup", save);
      }
      setTimeout(save, 100); // small delay to ensure UI is updated
    }
  }, [isOpen, buttonPosition]);

  // Toggle open/close
  const toggle = useCallback(() => {
    if (shouldUseProp) {
      setIsOpen(!isOpen);
      if (!isOpen && propOnClose) propOnClose();
      if (isOpen && propOnOpen) propOnOpen();
    } else {
      setIsOpen(!isOpen);
    }
  }, [isOpen, shouldUseProp, propOnOpen, propOnClose]);

  // Send predefined question to the backend and show answer
  const sendPredefinedQuestion = useCallback(async (question: string) => {
    if (!question.trim() || isSending) return;

    setIsSending(true);
    setError(null);

    // Add user message
    setMessages(prev => [...prev, { role: "user", content: question, timestamp: Date.now() }]);

    try {
      const response = await apiRequest("/support/chat", {
        method: "POST",
        body: JSON.stringify({
          message: question,
          history: messages.map(m => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      // Add assistant message response
      setMessages(prev => [...prev, { role: "assistant", content: response.response, timestamp: Date.now() }]);
    } catch (err: any) {
      console.error("Support chat error:", err);
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I'm having trouble connecting to the AI service. Please try again later.", timestamp: Date.now() }]);
      setError(err?.response?.data?.detail || err.message || "Unknown error");
    } finally {
      setIsSending(false);
    }
  }, [messages]);

  // Distinguish click from drag (short timeout)
  const [clickTimeout, setClickTimeout] = useState<number | null>(null);

  const handleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (clickTimeout) {
      clearTimeout(clickTimeout);
    }
    setClickTimeout(window.setTimeout(() => {
      toggle();
    }, 150));
  }, [toggle]);

  // Close on overlay click
  const handleOverlayClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      toggle();
    }
  }, [toggle]);

  // Keyboard accessibility - Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Update panel position when button position changes
  useEffect(() => {
    setPanelPosition({
      x: buttonPosition.x - 240,
      y: buttonPosition.y - 320,
    });
  }, [buttonPosition]);

  // Format timestamp to relative time
  const formatTimestamp = useCallback((ts: number) => {
    const diff = Date.now() - ts;
    if (diff < 1000) return "just now";
    if (diff < 60000) return `${Math.round(diff / 1000)}s ago`;
    if (diff < 3600000) return `${Math.round(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.round(diff / 3600000)}h ago`;
    return `${Math.round(diff / 86400000)}d ago`;
  }, []);

  if (authLoading) {
    return null;
  }

  return (
    <div>
      {/* Floating button - fixed at bottom-right */}
      <div
        ref={floatingRef}
        className="support-floating-button fixed bottom-4 right-4 cursor-grab select-none transition-transform duration-200 ease-in-out"
        style={{
          transform: isOpen ? "scale(1.05)" : "scale(1)",
          zIndex: 10000,
        }}
        onMouseDown={(e) => {
          e.preventDefault();
          setIsOpen(!isOpen);
        }}
        onTouchStart={(e) => {
          e.preventDefault();
          setIsOpen(!isOpen);
        }}
        onClick={handleClick}
      >
        <motion.div
          className="support-button bg-primary text-white rounded-full p-2 flex items-center justify-center hover:bg-primary/90 hover:scale-105 transition-transform duration-150"
          role="button"
          aria-label="Open support chat"
        >
          {isOpen ? <X size={20} /> : <MessageCircle size={20} />}
        </motion.div>
      </div>

      {/* Chat panel - appears when open, anchored bottom-right */}
      {isOpen && (
        <div
          ref={panelRef}
          className="support-panel fixed right-4 bottom-20 z-50 bg-bg/90 backdrop-blur-md rounded-2xl shadow-2xl max-w-lg flex flex-col"
          style={{
            maxHeight: 'min(600px, calc(100dvh - 100px))',
            width: '90%',
            maxWidth: '400px',
            zIndex: 10001,
          }}
          onClick={handleOverlayClick}
        >
          {/* Panel container with fade-in */}
          <motion.div
            className="support-panel-container bg-white rounded-2xl overflow-hidden flex flex-col"
            animate={{ opacity: 1, transition: { duration: 0.3 } }}
            exit={{ opacity: 0, transition: { duration: 0.2 } }}
          >
            {/* Header */}
            <div className="support-panel-header px-4 py-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageCircle className="text-primary" size={20} />
                  <span className="font-medium">Sanskrit Tutor Support</span>
                </div>
                <button
                  onClick={toggle}
                  className="support-close text-gray-500 hover:text-red-500"
                  aria-label="Close support chat"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="support-messages flex-1 overflow-y-auto px-4 py-3">
              {messages.map((msg, idx) => (
                <div
                  key={msg.timestamp}
                  className={`support-message ${msg.role === 'user' ? 'support-message-user' : 'support-message-assistant'}`}
                >
                  <div className="support-message-content max-w-[85%]">{msg.content}</div>
                  <div className="support-message-time text-xs text-gray-500">{formatTimestamp(msg.timestamp)}</div>
                </div>
              ))}

              {isSending && (
                <div className="support-message support-message-assistant py-2">
                  <div className="support-message-content flex items-center">
                    <div className="typing-indicator bg-light flex items-center gap-2 px-3 rounded-full" style={{ minWidth: '100px' }}>
                      <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                      <span>Typing...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Predefined questions - always show as selectable options */}
            {suggestedQuestions.length > 0 && (
              <div className="support-suggestions px-4 py-2 border-t border-border">
                <div className="text-xs text-gray-500">Quick questions:</div>
                <div className="flex gap-1">
                  {suggestedQuestions.map((q, i) => (
                    <button
                      key={i}
                      className="support-suggestion-btn rounded-sm bg-light px-2 py-1 text-sm text-gray-700 hover:text-primary hover:bg-white transition-colors"
                      onClick={() => sendPredefinedQuestion(q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input area - intentionally hidden: no free-text input */}
            {/* This interface only supports predefined questions above */}
          </motion.div>
        </div>
      )}
    </div>
  );
}