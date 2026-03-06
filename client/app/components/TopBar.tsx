"use client";

import { Menu } from "lucide-react";

interface TopBarProps {
  title: string;
  onMenuClick: () => void;
}

const PILLS = ["LLaMA 3.3", "Web Search", "Memory"];

export default function TopBar({ title, onMenuClick }: TopBarProps) {
  return (
    <div
      style={{
        height: 56,
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        borderBottom: "1px solid var(--glass-edge)",
        background: "rgba(13,13,18,0.5)",
        backdropFilter: "blur(12px)",
        zIndex: 10,
        gap: 12,
      }}
    >
      {/* Left — hamburger + title */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
        {/* Hamburger — always visible, opens sidebar drawer */}
        <button
          onClick={onMenuClick}
          style={{
            width: 36,
            height: 36,
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--glass-edge)",
            background: "var(--glass)",
            color: "var(--text-mid)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            flexShrink: 0,
            transition: "all 0.2s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--pink-dim)";
            e.currentTarget.style.color = "var(--pink-soft)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--glass-edge)";
            e.currentTarget.style.color = "var(--text-mid)";
          }}
        >
          <Menu size={16} />
        </button>

        {/* Title */}
        <span
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: "var(--text-hi)",
            letterSpacing: "0.04em",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {title}
        </span>
      </div>

      {/* Right — pills (hidden on very small screens) */}
      <div
        style={{
          display: "flex",
          gap: 6,
          alignItems: "center",
          flexShrink: 0,
        }}
      >
        {PILLS.map((label, i) => (
          <div
            key={label}
            style={{
              padding: "4px 10px",
              borderRadius: 99,
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              border: i === 0
                ? "1px solid var(--pink-glow)"
                : "1px solid var(--glass-edge)",
              color: i === 0 ? "var(--pink-soft)" : "var(--text-mid)",
              background: i === 0 ? "var(--pink-dim)" : "var(--glass)",
              boxShadow: i === 0 ? "0 0 12px var(--pink-dim)" : "none",
              // Hide secondary pills on small screens
              display: i > 0 ? "var(--pill-display, flex)" : "flex",
            }}
          >
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}