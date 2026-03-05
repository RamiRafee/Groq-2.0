"use client";

import { Plus } from "lucide-react";
import { Conversation } from "./types";

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onNewChat: () => void;
  onSelectConv: (id: string) => void;
}

export default function Sidebar({
  conversations,
  activeId,
  onNewChat,
  onSelectConv,
}: SidebarProps) {
  return (
    <aside
      style={{
        width: 280,
        minWidth: 280,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: "rgba(13,13,18,0.8)",
        backdropFilter: "blur(24px) saturate(1.4)",
        borderRight: "1px solid var(--glass-edge)",
        position: "relative",
        overflow: "hidden",
        zIndex: 2,
      }}
    >
      {/* Pink left-edge glow */}
      <div
        style={{
          position: "absolute",
          top: 0, left: 0,
          width: 1, height: "100%",
          background:
            "linear-gradient(180deg, transparent 0%, var(--pink) 40%, var(--pink-soft) 60%, transparent 100%)",
          opacity: 0.5,
          pointerEvents: "none",
        }}
      />

      {/* ── Header ─────────────────────────────────────────── */}
      <div
        style={{
          padding: "28px 20px 20px",
          borderBottom: "1px solid var(--glass-edge)",
          flexShrink: 0,
        }}
      >
        {/* Logo */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 18,
          }}
        >
          <div
            style={{
              width: 32, height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg, var(--pink) 0%, #9b1fef 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 0 16px var(--pink-glow), 0 0 32px rgba(155,31,239,0.3)",
              animation: "pulse-logo 3s ease-in-out infinite",
              flexShrink: 0,
            }}
          >
            <svg
              width="18" height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>

          <span
            style={{
              fontSize: 17,
              fontWeight: 800,
              letterSpacing: "0.04em",
              background: "linear-gradient(90deg, #fff 30%, var(--pink-soft))",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            AGENTUI
          </span>
        </div>

        {/* New chat button */}
        <button
          onClick={onNewChat}
          style={{
            width: "100%",
            padding: "10px 14px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--pink-dim)",
            background: "var(--pink-dim)",
            color: "var(--pink-soft)",
            fontFamily: "var(--font-ui)",
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            transition: "all 0.2s ease",
            position: "relative",
            overflow: "hidden",
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget;
            el.style.background = "rgba(255,45,120,0.18)";
            el.style.borderColor = "var(--pink-glow)";
            el.style.boxShadow = "0 0 20px var(--pink-dim)";
            el.style.color = "#fff";
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget;
            el.style.background = "var(--pink-dim)";
            el.style.borderColor = "var(--pink-dim)";
            el.style.boxShadow = "none";
            el.style.color = "var(--pink-soft)";
          }}
        >
          <Plus size={14} />
          New Conversation
        </button>
      </div>

      {/* ── Section label ──────────────────────────────────── */}
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          color: "var(--text-lo)",
          padding: "16px 20px 8px",
          flexShrink: 0,
        }}
      >
        Recent
      </div>

      {/* ── History list ───────────────────────────────────── */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "0 10px 16px",
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        {conversations.map((conv) => {
          const isActive = conv.id === activeId;
          return (
            <div
              key={conv.id}
              onClick={() => onSelectConv(conv.id)}
              style={{
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
                border: isActive
                  ? "1px solid rgba(255,45,120,0.25)"
                  : "1px solid transparent",
                background: isActive ? "var(--pink-dim)" : "transparent",
                position: "relative",
                overflow: "hidden",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                if (isActive) return;
                const el = e.currentTarget;
                el.style.background = "var(--glass)";
                el.style.borderColor = "var(--glass-edge)";
              }}
              onMouseLeave={(e) => {
                if (isActive) return;
                const el = e.currentTarget;
                el.style.background = "transparent";
                el.style.borderColor = "transparent";
              }}
            >
              {/* Active left bar */}
              {isActive && (
                <div
                  style={{
                    position: "absolute",
                    left: 0, top: "20%",
                    height: "60%", width: 2,
                    background: "var(--pink)",
                    borderRadius: "0 2px 2px 0",
                    boxShadow: "0 0 8px var(--pink)",
                  }}
                />
              )}

              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: isActive ? "#fff" : "var(--text-hi)",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  lineHeight: 1.4,
                }}
              >
                {conv.title}
              </div>

              <div
                style={{
                  fontSize: 11,
                  color: "var(--text-mid)",
                  marginTop: 2,
                  fontFamily: "var(--font-mono)",
                }}
              >
                {conv.time}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Footer ─────────────────────────────────────────── */}
      <div
        style={{
          padding: "14px 16px",
          borderTop: "1px solid var(--glass-edge)",
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 32, height: 32,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #2a1a3a, #1a1a2e)",
            border: "1.5px solid var(--pink-glow)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 13,
            flexShrink: 0,
            boxShadow: "0 0 8px var(--pink-dim)",
          }}
        >
          👤
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-hi)" }}>
            User
          </div>
          <div
            style={{
              fontSize: 10,
              color: "var(--pink-soft)",
              letterSpacing: "0.08em",
            }}
          >
            AGENT MODE
          </div>
        </div>
      </div>
    </aside>
  );
}