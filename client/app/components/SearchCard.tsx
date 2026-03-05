interface SearchCardProps {
  query: string;
  urls?: string[];
}

function getHostname(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch (_e) {
    return url;
  }
}

function UrlRow({ url }: { url: string }) {
  const hostname = getHostname(url);

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        textDecoration: "none",
        color: "var(--cyan)",
        opacity: 0.8,
        transition: "opacity 0.15s ease",
        fontSize: 11,
        overflow: "hidden",
      }}
      onMouseEnter={(e: React.MouseEvent<HTMLAnchorElement>) => {
        e.currentTarget.style.opacity = "1";
      }}
      onMouseLeave={(e: React.MouseEvent<HTMLAnchorElement>) => {
        e.currentTarget.style.opacity = "0.8";
      }}
    >
      {/* Colored dot instead of favicon */}
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: "var(--cyan)",
          flexShrink: 0,
          boxShadow: "0 0 4px var(--cyan)",
        }}
      />
      <span
        style={{
          flexShrink: 0,
          fontWeight: 700,
          fontSize: 10,
          minWidth: 90,
        }}
      >
        {hostname}
      </span>
      <span
        style={{
          opacity: 0.5,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          fontSize: 10,
        }}
      >
        {url}
      </span>
    </a>
  );
}

export default function SearchCard({ query, urls = [] }: SearchCardProps) {
  const done = urls.length > 0;

  return (
    <div
      style={{
        marginTop: 10,
        marginBottom: 10,
        borderRadius: "var(--radius-md)",
        background: "rgba(0,240,255,0.04)",
        border: "1px solid rgba(0,240,255,0.15)",
        fontSize: 12,
        color: "var(--cyan)",
        fontFamily: "var(--font-mono)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Left cyan bar */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: 2,
          background: "var(--cyan)",
          boxShadow: "0 0 8px var(--cyan)",
        }}
      />

      {/* Scanning sweep */}
      {!done && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "linear-gradient(90deg, transparent 0%, rgba(0,240,255,0.06) 50%, transparent 100%)",
            animation: "scan 1.8s linear infinite",
          }}
        />
      )}

      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span style={{ flexShrink: 0, fontSize: 14, zIndex: 1 }}>🔍</span>

        <div style={{ flex: 1, zIndex: 1 }}>
          <span
            style={{
              fontSize: 9,
              letterSpacing: "0.15em",
              opacity: 0.6,
              display: "block",
              marginBottom: 2,
              textTransform: "uppercase",
            }}
          >
            {done ? "Search results" : "Searching the web"}
          </span>
          <strong style={{ fontSize: 12 }}>{query}</strong>
        </div>

        {!done ? (
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: "50%",
              border: "2px solid rgba(0,240,255,0.2)",
              borderTopColor: "var(--cyan)",
              animation: "spin 0.7s linear infinite",
              flexShrink: 0,
              zIndex: 1,
            }}
          />
        ) : (
          <span
            style={{
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: "0.1em",
              opacity: 0.7,
              flexShrink: 0,
            }}
          >
            {urls.length} SOURCE{urls.length !== 1 ? "S" : ""}
          </span>
        )}
      </div>

      {/* URL rows */}
      {done && (
        <div
          style={{
            borderTop: "1px solid rgba(0,240,255,0.1)",
            padding: "8px 16px 10px",
            display: "flex",
            flexDirection: "column",
            gap: 5,
          }}
        >
          {urls.map((url: string) => (
            <UrlRow key={url} url={url} />
          ))}
        </div>
      )}
    </div>
  );
}