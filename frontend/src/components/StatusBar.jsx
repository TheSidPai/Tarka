export default function StatusBar({ messages }) {
  if (!messages || messages.length === 0) return null

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "flex-start",
      padding: "20px 0",
      gap: 9
    }}>
      {messages.map((msg, i) => {
        const isLatest = i === messages.length - 1
        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              opacity: isLatest ? 1 : 0.4,
              transition: "opacity 0.3s ease",
              fontSize: 13,
              color: "var(--text-secondary)"
            }}
          >
            {/* Dot — green for latest, muted for past */}
            <div style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: isLatest
                ? "var(--consensus-border)"
                : "var(--border)",
              transition: "background 0.3s ease"
            }}/>
            {msg}
          </div>
        )
      })}
    </div>
  )
}
