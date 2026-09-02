import { useState } from "react"

export default function SearchBar({ onSearch, hasResults, disabled }) {
  const [input, setInput] = useState("")

  // The question is rendered in the thread now, so the box clears on submit
  // instead of mirroring the active query back from the parent.
  function handleSubmit() {
    if (disabled || !input.trim()) return
    onSearch(input.trim())
    setInput("")
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") handleSubmit()
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: hasResults ? "flex-start" : "center",
        minHeight: hasResults ? "auto" : "65vh",
        padding: hasResults ? "24px 24px 0" : "0 24px",
        transition: "all 0.4s ease",
      }}
    >
      {/* Logo + tagline — hide once results appear */}
      {!hasResults && (
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <h1 style={{
            fontSize: 48,
            fontWeight: 600,
            color: "var(--text-primary)",
            letterSpacing: "-1px",
            marginBottom: 12
          }}>
            Tarka
          </h1>
          <p style={{
            fontSize: 16,
            color: "var(--text-secondary)",
            letterSpacing: "0.02em"
          }}>
            Research that argues with itself.
          </p>
        </div>
      )}

      {/* Logo inline when results showing */}
      {hasResults && (
        <div style={{ marginBottom: 16 }}>
          <span style={{
            fontSize: 22,
            fontWeight: 600,
            color: "var(--text-primary)",
            letterSpacing: "-0.5px"
          }}>
            Tarka
          </span>
        </div>
      )}

      {/* Search row */}
      <div style={{
        display: "flex",
        gap: 10,
        width: "100%",
        maxWidth: hasResults ? 720 : 600,
        transition: "max-width 0.4s ease"
      }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={disabled ? "Researching..." : "Ask a research question..."}
          style={{
            flex: 1,
            padding: "14px 18px",
            borderRadius: 12,
            border: "1px solid var(--border)",
            background: "var(--card-bg)",
            color: "var(--text-primary)",
            fontSize: 15,
            outline: "none",
            opacity: disabled ? 0.6 : 1,
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={disabled}
          style={{
            padding: "14px 24px",
            borderRadius: 12,
            border: "none",
            background: "var(--accent)",
            color: "var(--bg-primary)",
            fontSize: 15,
            fontWeight: 500,
            cursor: disabled ? "not-allowed" : "pointer",
            whiteSpace: "nowrap",
            opacity: disabled ? 0.6 : 1,
          }}
        >
          Search
        </button>
      </div>
    </div>
  )
}