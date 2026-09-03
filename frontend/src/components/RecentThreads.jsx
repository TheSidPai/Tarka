import { relativeTime } from "../lib/threads";

/* Shown on the empty state only — once a thread is open the page belongs to
   it, and a list of other threads would compete with the reading column. */
export default function RecentThreads({ threads, currentId, onOpen, onDelete }) {
  const others = threads.filter((t) => t.id !== currentId && t.turns?.length);
  if (others.length === 0) return null;

  return (
    <div
      className="no-print"
      style={{ maxWidth: 680, margin: "44px auto 0", padding: "0 24px" }}
    >
      <p
        style={{
          fontSize: 11,
          fontWeight: 500,
          color: "var(--text-secondary)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginBottom: 10,
        }}
      >
        Recent
      </p>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {others.map((t, i) => (
          <div
            key={t.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              borderTop: i === 0 ? "1px solid var(--border)" : "none",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <button
              onClick={() => onOpen(t)}
              style={{
                flex: 1,
                minWidth: 0,
                display: "flex",
                alignItems: "baseline",
                gap: 12,
                padding: "12px 4px",
                background: "none",
                border: "none",
                color: "var(--text-secondary)",
                fontFamily: "var(--font-serif)",
                fontSize: 14,
                textAlign: "left",
                cursor: "pointer",
                transition: "color 0.15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
            >
              <span
                style={{
                  flex: 1,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {t.title}
              </span>
              <span
                className="tnum"
                style={{ fontFamily: "var(--font-sans)", fontSize: 11, flexShrink: 0 }}
              >
                {t.turns.length} turn{t.turns.length === 1 ? "" : "s"} · {relativeTime(t.updatedAt)}
              </span>
            </button>
            <button
              onClick={() => onDelete(t.id)}
              title="Delete this thread"
              style={{
                background: "none",
                border: "none",
                color: "var(--text-secondary)",
                fontSize: 15,
                lineHeight: 1,
                padding: "6px 4px",
                cursor: "pointer",
                opacity: 0.5,
                flexShrink: 0,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.5")}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
