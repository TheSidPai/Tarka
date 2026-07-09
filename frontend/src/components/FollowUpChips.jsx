export default function FollowUpChips({ followups, onSelect }) {
  console.log("FollowUpChips followups:", followups)
  if (!followups || followups.length === 0) return null

  return (
    <div style={{
      maxWidth: 720,
      margin: "24px auto 48px",
      padding: "0 24px",
    }}>
      <p style={{
        fontSize: 13,
        color: "var(--text-secondary)",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        marginBottom: 12
      }}>
        Follow up
      </p>
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 8
      }}>
        {followups.map((f, i) => (
          <button
            key={i}
            onClick={() => onSelect(f)}
            style={{
              padding: "10px 16px",
              borderRadius: 20,
              border: "1px solid var(--border)",
              background: "var(--card-bg)",
              color: "var(--text-secondary)",
              fontSize: 13,
              cursor: "pointer",
              textAlign: "left",
              lineHeight: 1.4,
              transition: "border-color 0.2s, color 0.2s"
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = "var(--accent)"
              e.currentTarget.style.color = "var(--text-primary)"
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = "var(--border)"
              e.currentTarget.style.color = "var(--text-secondary)"
            }}
          >
            {f}
          </button>
        ))}
      </div>
    </div>
  )
}