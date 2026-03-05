"use client";

import { useRef, useEffect } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  isStreaming: boolean;
  prefillValue?: string;
}

export default function ChatInput({
  value,
  onChange,
  onSend,
  isStreaming,
  prefillValue,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea as content grows
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, [value]);

  // Focus input when a suggestion chip is clicked
  useEffect(() => {
    if (prefillValue) {
      textareaRef.current?.focus();
    }
  }, [prefillValue]);

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && value.trim()) onSend();
    }
  }

  return (
    <div
      style={{
        flexShrink: 0,
        padding: "16px 24px 24px",
        position: "relative",
      }}
    >
      {/* Top fade */}
      <div
        style={{
          position: "absolute",
          top: -40, left: 0, right: 0,
          height: 40,
          background: "linear-gradient(0deg, var(--bg-void), transparent)",
          pointerEvents: "none",
        }}
      />

      {/* Input shell */}
      <div
        style={{
          position: "relative",
          background: "rgba(18,18,26,0.85)",
          backdropFilter: "blur(20px) saturate(1.5)",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--glass-edge)",
          transition: "border-color 0.25s ease, box-shadow 0.25s ease",
        }}
        onFocus={() => {
          const el = document.getElementById("input-shell");
          if (el) {
            el.style.borderColor = "rgba(255,45,120,0.45)";
            el.style.boxShadow =
              "0 0 0 3px rgba(255,45,120,0.08), 0 0 30px rgba(255,45,120,0.1)";
          }
        }}
        onBlur={() => {
          const el = document.getElementById("input-shell");
          if (el) {
            el.style.borderColor = "var(--glass-edge)";
            el.style.boxShadow = "none";
          }
        }}
        id="input-shell"
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask anything…"
          rows={1}
          disabled={isStreaming}
          style={{
            width: "100%",
            minHeight: 52,
            maxHeight: 180,
            padding: "16px 60px 16px 18px",
            background: "transparent",
            border: "none",
            outline: "none",
            color: "var(--text-hi)",
            fontFamily: "var(--font-ui)",
            fontSize: 14,
            lineHeight: 1.6,
            resize: "none",
            display: "block",
            opacity: isStreaming ? 0.5 : 1,
          }}
        />

        {/* Send button */}
        <div
          style={{
            position: "absolute",
            right: 10,
            bottom: 10,
          }}
        >
          <button
            onClick={() => { if (!isStreaming && value.trim()) onSend(); }}
            disabled={isStreaming || !value.trim()}
            style={{
              width: 36,
              height: 36,
              borderRadius: "var(--radius-sm)",
              border: "none",
              background:
                isStreaming || !value.trim()
                  ? "rgba(255,45,120,0.3)"
                  : "linear-gradient(135deg, var(--pink) 0%, #9b1fef 100%)",
              color: "#fff",
              cursor: isStreaming || !value.trim() ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.2s ease",
              boxShadow:
                isStreaming || !value.trim()
                  ? "none"
                  : "0 0 12px var(--pink-glow)",
            }}
            onMouseEnter={(e) => {
              if (isStreaming || !value.trim()) return;
              e.currentTarget.style.transform = "scale(1.08)";
              e.currentTarget.style.boxShadow = "0 0 20px var(--pink)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "scale(1)";
              e.currentTarget.style.boxShadow = "0 0 12px var(--pink-glow)";
            }}
          >
            <Send size={15} />
          </button>
        </div>
      </div>

      {/* Hint row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "6px 4px 0",
          fontSize: 10,
          color: "var(--text-lo)",
          fontFamily: "var(--font-mono)",
        }}
      >
        <span>Enter to send · Shift+Enter for newline</span>
        <span
          style={{
            padding: "2px 8px",
            borderRadius: 99,
            background: "var(--pink-dim)",
            color: "var(--pink-soft)",
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            border: "1px solid rgba(255,45,120,0.2)",
          }}
        >
          llama-3.3-70b
        </span>
      </div>
    </div>
  );
}