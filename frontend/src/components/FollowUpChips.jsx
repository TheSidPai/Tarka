export default function FollowUpChips({ followups, onSelect }) {
  if (!followups || followups.length === 0) return null

  return (
    <div style={{ marginTop: 28 }}>
      <p style={{
        fontSize: 11,
        fontWeight: 500,
        color: "var(--text-secondary)",
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        marginBottom: 10
      }}>
        Follow up
      </p>
      {/* A list, not pills — these are questions, not tags */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {followups.map((f, i) => (
          <button
            key={i}
            onClick={() => onSelect(f)}
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 12,
              width: "100%",
              padding: "13px 4px",
              border: "none",
              borderTop: i === 0 ? "1px solid var(--border)" : "none",
              borderBottom: "1px solid var(--border)",
              background: "none",
              color: "var(--text-secondary)",
              fontFamily: "var(--font-serif)",
              fontSize: 14.5,
              lineHeight: 1.5,
              cursor: "pointer",
              textAlign: "left",
              transition: "color 0.15s, padding-left 0.15s"
            }}
            onMouseEnter={e => {
              e.currentTarget.style.color = "var(--text-primary)"
              e.currentTarget.style.paddingLeft = "10px"
              e.currentTarget.querySelector("[data-arrow]").style.opacity = "1"
            }}
            onMouseLeave={e => {
              e.currentTarget.style.color = "var(--text-secondary)"
              e.currentTarget.style.paddingLeft = "4px"
              e.currentTarget.querySelector("[data-arrow]").style.opacity = "0.3"
            }}
          >
            <span style={{ flex: 1, maxWidth: "80ch" }}>{f}</span>
            <span
              data-arrow
              style={{
                opacity: 0.3,
                transition: "opacity 0.15s",
                fontSize: 13,
                flexShrink: 0
              }}
            >
              →
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
