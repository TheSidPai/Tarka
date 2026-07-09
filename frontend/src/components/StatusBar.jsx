export default function StatusBar({ messages }) {
  console.log("StatusBar messages:", messages)
  if (!messages || messages.length === 0) return null

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "32px 24px",
      gap: 10
    //   background: "red"
    }}>
      {messages.map((msg, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            opacity: i === messages.length - 1 ? 1 : 0.4,
            transition: "opacity 0.3s ease",
            fontSize: 14,
            color: "var(--text-secondary)"
          }}
        >
          {/* Dot — green for latest, muted for past */}
          <div style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: i === messages.length - 1
              ? "var(--consensus-border)"
              : "var(--border)",
            transition: "background 0.3s ease"
          }}/>
          {msg}
        </div>
      ))}
    </div>
  )
}