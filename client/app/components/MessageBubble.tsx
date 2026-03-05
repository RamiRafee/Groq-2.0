import SearchCard from "./SearchCard";
import { Message } from "./types";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser  = message.role === "user";
  const isAgent = message.role === "agent";

  return (
    <div
      style={{
        display: "flex",
        gap: 14,
        maxWidth: 760,
        width: "100%",
        flexDirection: isUser ? "row-reverse" : "row",
        marginLeft: isUser ? "auto" : undefined,
        animation: "msg-in 0.35s cubic-bezier(0.22, 1, 0.36, 1) both",
      }}
    >
      {/* Avatar */}
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 13,
          marginTop: 2,
          background: isAgent
            ? "linear-gradient(135deg, var(--pink) 0%, #7b1fdf 100%)"
            : "var(--bg-3)",
          boxShadow: isAgent ? "0 0 12px var(--pink-glow)" : undefined,
          border: isUser ? "1px solid var(--glass-edge)" : undefined,
        }}
      >
        {isAgent ? "✦" : "👤"}
      </div>

      {/* Body */}
      <div style={{ flex: 1, minWidth: 0 }}>

        {/* Name */}
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: 6,
            color: isUser ? "var(--pink-soft)" : "var(--text-mid)",
            textAlign: isUser ? "right" : "left",
          }}
        >
          {isUser ? "You" : "Agent"}
        </div>

        {/* Bubble */}
        <div
          style={{
            padding: "14px 18px",
            borderRadius: isUser
              ? "var(--radius-lg) 4px var(--radius-lg) var(--radius-lg)"
              : "4px var(--radius-lg) var(--radius-lg) var(--radius-lg)",
            fontSize: 14,
            lineHeight: 1.65,
            color: "var(--text-hi)",
            position: "relative",
            background: isUser
              ? "linear-gradient(135deg, rgba(255,45,120,0.18), rgba(155,31,239,0.12))"
              : "rgba(26,26,38,0.7)",
            backdropFilter: "blur(16px)",
            border: isUser
              ? "1px solid rgba(255,45,120,0.3)"
              : "1px solid var(--glass-edge)",
            boxShadow: isUser
              ? "0 0 24px rgba(255,45,120,0.08)"
              : undefined,
          }}
        >
          {/* Search card — agent only, when a search query exists */}
          {isAgent && message.searchQuery && (
            <SearchCard
              query={message.searchQuery}
              urls={message.searchUrls ?? []}
            />
          )}

          {/* Message text */}
          <span style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {message.content}
          </span>

          {/* Streaming cursor */}
          {message.isStreaming && (
            <span
              style={{
                display: "inline-block",
                width: 2,
                height: 14,
                background: "var(--pink)",
                marginLeft: 2,
                verticalAlign: "middle",
                borderRadius: 1,
                boxShadow: "0 0 6px var(--pink)",
                animation: "blink 0.8s step-end infinite",
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}