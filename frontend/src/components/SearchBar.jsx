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
            fontFamily: "var(--font-display)",
            fontSize: 76,
            fontWeight: 400,
            color: "var(--text-primary)",
            letterSpacing: "-0.03em",
            lineHeight: 1,
            marginBottom: 18
          }}>
            tarka
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
        <div style={{ marginBottom: 18 }}>
          <span style={{
            fontFamily: "var(--font-display)",
            fontSize: 30,
            fontWeight: 400,
            color: "var(--text-primary)",
            letterSpacing: "-0.025em",
            lineHeight: 1
          }}>
            tarka
          </span>
        </div>
      )}

      {/* Search row */}
      <div style={{
        display: "flex",
        gap: 10,
        width: "100%",
        maxWidth: hasResults ? 976 : 680,
        transition: "max-width 0.4s ease"
      }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={disabled ? "Researching..." : "Ask a research question..."}
          onFocus={e => {
            e.currentTarget.style.borderColor = "var(--text-secondary)"
            e.currentTarget.style.boxShadow = "0 0 0 3px var(--dot)"
          }}
          onBlur={e => {
            e.currentTarget.style.borderColor = "var(--border)"
            e.currentTarget.style.boxShadow = "none"
          }}
          style={{
            flex: 1,
            padding: "14px 18px",
            borderRadius: 12,
            border: "1px solid var(--border)",
            background: "var(--card-bg)",
            color: "var(--text-primary)",
            fontFamily: "var(--font-serif)",
            fontSize: 15,
            outline: "none",
            opacity: disabled ? 0.6 : 1,
            transition: "border-color 0.15s ease, box-shadow 0.15s ease",
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={disabled}
          onMouseEnter={e => {
            if (disabled) return
            e.currentTarget.style.transform = "translateY(-1px)"
            e.currentTarget.style.boxShadow = `0 6px 18px -4px var(--btn-shadow)`
            e.currentTarget.querySelector("[data-arrow]").style.transform = "translateX(2px)"
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = "none"
            e.currentTarget.style.boxShadow = `0 2px 8px -2px var(--btn-shadow)`
            e.currentTarget.querySelector("[data-arrow]").style.transform = "none"
          }}
          onMouseDown={e => { if (!disabled) e.currentTarget.style.transform = "translateY(0)" }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 9,
            padding: "14px 22px",
            borderRadius: 12,
            border: "none",
            // Slight vertical gradient + shadow reads as a raised surface
            // rather than a flat colour block.
            background: "linear-gradient(180deg, var(--btn-from), var(--btn-to))",
            boxShadow: `0 2px 8px -2px var(--btn-shadow)`,
            color: "var(--bg-primary)",
            fontFamily: "var(--font-sans)",
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: "0.02em",
            cursor: disabled ? "not-allowed" : "pointer",
            whiteSpace: "nowrap",
            opacity: disabled ? 0.5 : 1,
            transition: "transform 0.15s ease, box-shadow 0.15s ease, opacity 0.2s",
          }}
        >
          {disabled ? "Working" : "Search"}
          <span
            data-arrow
            style={{
              display: "inline-block",
              transition: "transform 0.15s ease",
              fontSize: 13,
            }}
          >
            →
          </span>
        </button>
      </div>
    </div>
  )
}