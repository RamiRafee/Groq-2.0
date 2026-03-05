"use client";

interface TopBarProps {
  title: string;
}

const PILLS = ["LLaMA 3.3", "Web Search", "Memory"];

export default function TopBar({ title }: TopBarProps) {
  return (
    <div
      style={{
        height: 56,
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
        borderBottom: "1px solid var(--glass-edge)",
        background: "rgba(13,13,18,0.5)",
        backdropFilter: "blur(12px)",
        zIndex: 10,
      }}
    >
      {/* Conversation title */}
      <span
        style={{
          fontSize: 14,
          fontWeight: 700,
          color: "var(--text-hi)",
          letterSpacing: "0.04em",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          maxWidth: "50%",
        }}
      >
        {title}
      </span>

      {/* Capability pills */}
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {PILLS.map((label, i) => (
          <div
            key={label}
            style={{
              padding: "4px 12px",
              borderRadius: 99,
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              border: i === 0
                ? "1px solid var(--pink-glow)"
                : "1px solid var(--glass-edge)",
              color: i === 0 ? "var(--pink-soft)" : "var(--text-mid)",
              background: i === 0 ? "var(--pink-dim)" : "var(--glass)",
              boxShadow: i === 0 ? "0 0 12px var(--pink-dim)" : "none",
            }}
          >
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}