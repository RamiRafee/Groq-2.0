export default function ThinkingIndicator() {
  return (
    <div className="thinking-row">
      {/* Agent avatar */}
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          background: "linear-gradient(135deg, var(--pink) 0%, #7b1fdf 100%)",
          boxShadow: "0 0 12px var(--pink-glow)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 13,
          flexShrink: 0,
          marginTop: 2,
        }}
      >
        ✦
      </div>

      {/* Bubble */}
      <div
        style={{
          padding: "12px 18px",
          borderRadius: "4px var(--radius-lg) var(--radius-lg) var(--radius-lg)",
          background: "rgba(26,26,38,0.7)",
          backdropFilter: "blur(16px)",
          border: "1px solid var(--glass-edge)",
          display: "flex",
          alignItems: "center",
          gap: 10,
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase" as const,
          color: "var(--text-mid)",
        }}
      >
        {/* Dot pulse */}
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          {[0, 0.2, 0.4].map((delay, i) => (
            <span
              key={i}
              style={{
                width: 5,
                height: 5,
                borderRadius: "50%",
                background: "var(--pink)",
                boxShadow: "0 0 6px var(--pink)",
                display: "inline-block",
                animation: `dot-bounce 1.2s ease-in-out ${delay}s infinite`,
              }}
            />
          ))}
        </div>
        Reasoning…
      </div>
    </div>
  );
}