"use client";

import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import ThinkingIndicator from "./ThinkingIndicator";
import { Message } from "./types";

interface MessageListProps {
  messages: Message[];
  isThinking: boolean;
  onPrefill: (text: string) => void;
}

const SUGGESTIONS = [
  { emoji: "⚡", label: "How transformers work",  text: "Explain how transformers work in AI"             },
  { emoji: "🔍", label: "Latest AI news",          text: "Search for the latest AI news today"            },
  { emoji: "🐍", label: "Async web scraper",       text: "Write a Python async web scraper"               },
  { emoji: "🏗",  label: "System design tips",     text: "What are the best practices for system design?" },
];

export default function MessageList({
  messages,
  isThinking,
  onPrefill,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  const isEmpty = messages.length === 0 && !isThinking;

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "32px 24px",
        display: "flex",
        flexDirection: "column",
        gap: 24,
      }}
    >
      {/* ── Empty state ──────────────────────────────────────── */}
      {isEmpty && (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            padding: 40,
            minHeight: "60vh",
          }}
        >
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: "50%",
              background:
                "radial-gradient(circle at 35% 35%, rgba(255,45,120,0.4), transparent 60%), " +
                "radial-gradient(circle at 65% 65%, rgba(155,31,239,0.3), transparent 60%), " +
                "rgba(18,18,26,0.6)",
              border: "1px solid rgba(255,45,120,0.25)",
              boxShadow:
                "0 0 40px rgba(255,45,120,0.15), 0 0 80px rgba(155,31,239,0.1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 28,
              animation: "orb-float 4s ease-in-out infinite",
              marginBottom: 8,
            }}
          >
            ✦
          </div>

          <div
            style={{
              fontSize: 20,
              fontWeight: 800,
              background:
                "linear-gradient(90deg, var(--text-hi) 40%, var(--pink-soft))",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            What can I help with?
          </div>

          <div
            style={{
              fontSize: 13,
              color: "var(--text-mid)",
              textAlign: "center",
              maxWidth: 320,
              lineHeight: 1.6,
            }}
          >
            Ask me anything — I can search the web, reason through complex
            topics, and remember our conversation.
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              justifyContent: "center",
              marginTop: 12,
            }}
          >
            {SUGGESTIONS.map((s) => (
              <button
                key={s.text}
                onClick={() => onPrefill(s.text)}
                style={{
                  padding: "8px 16px",
                  borderRadius: 99,
                  border: "1px solid var(--glass-edge)",
                  background: "var(--glass)",
                  fontSize: 12,
                  color: "var(--text-mid)",
                  cursor: "pointer",
                  fontFamily: "var(--font-ui)",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget;
                  el.style.borderColor = "var(--pink-dim)";
                  el.style.color = "var(--text-hi)";
                  el.style.background = "var(--pink-dim)";
                  el.style.boxShadow = "0 0 16px var(--pink-dim)";
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget;
                  el.style.borderColor = "var(--glass-edge)";
                  el.style.color = "var(--text-mid)";
                  el.style.background = "var(--glass)";
                  el.style.boxShadow = "none";
                }}
              >
                {s.emoji} {s.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Message list ─────────────────────────────────────── */}
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          message={msg}
        />
      ))}

      {/* ── Thinking indicator ───────────────────────────────── */}
      {isThinking && <ThinkingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
}