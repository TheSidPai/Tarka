export default function SynthesisPanel({ synthesis }) {
  if (!synthesis) return null;

  const { summary, consensus, contradictions, source_count } = synthesis;

  return (
    <div
      style={{
        maxWidth: 720,
        margin: "32px auto 0",
        padding: "0 24px",
        display: "flex",
        flexDirection: "column",
        gap: 24,
      }}
    >
      {/* Summary */}
      <div
        style={{
          padding: "20px 24px",
          borderRadius: 12,
          border: "1px solid var(--border)",
          background: "var(--card-bg)",
        }}
      >
        <p
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            marginBottom: 8,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          Overview · {source_count?.web ?? 0} web · {source_count?.papers ?? 0}{" "}
          papers
        </p>
        <p
          style={{
            fontSize: 15,
            color: "var(--text-primary)",
            lineHeight: 1.7,
          }}
        >
          {summary}
        </p>
      </div>
      {(!consensus || consensus.length === 0) &&
        (!contradictions || contradictions.length === 0) && (
          <div
            style={{
              padding: "16px 20px",
              borderRadius: 10,
              border: "1px solid var(--border)",
              background: "var(--card-bg)",
              fontSize: 14,
              color: "var(--text-secondary)",
              textAlign: "center",
            }}
          >
            No consensus or contradictions found for this query. Try a more
            contested topic.
          </div>
        )}
      {/* Consensus */}
      {consensus?.length > 0 && (
        <div>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: 12,
            }}
          >
            Consensus · {consensus.length}
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {consensus.map((item, i) => (
              <div
                key={i}
                style={{
                  padding: "16px 20px",
                  borderRadius: 10,
                  border: "1px solid var(--consensus-border)",
                  background: "var(--consensus-bg)",
                  borderLeft: "3px solid var(--consensus-border)",
                }}
              >
                <p
                  style={{
                    fontSize: 14,
                    fontWeight: 500,
                    color: "var(--text-primary)",
                    marginBottom: 10,
                  }}
                >
                  {item.point}
                </p>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                  }}
                >
                  <Quote
                    label="Web"
                    text={item.web_quote}
                    url={item.source_url}
                  />
                  <Quote label="Paper" text={item.paper_quote} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contradictions */}
      {contradictions?.length > 0 && (
        <div>
          <h2
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: 12,
            }}
          >
            Contradictions · {contradictions.length}
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {contradictions.map((item, i) => (
              <div
                key={i}
                style={{
                  borderRadius: 10,
                  border: "1px solid var(--contradiction-border)",
                  background: "var(--contradiction-bg)",
                  overflow: "hidden",
                }}
              >
                {/* Topic header */}
                <div
                  style={{
                    padding: "12px 20px",
                    borderBottom: "1px solid var(--contradiction-border)",
                    borderLeft: "3px solid var(--contradiction-border)",
                  }}
                >
                  <p
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: "var(--text-primary)",
                    }}
                  >
                    {item.conflict_topic}
                  </p>
                </div>

                {/* Two column claims */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                  }}
                >
                  {/* Web side */}
                  <div
                    style={{
                      padding: "16px 20px",
                      borderRight: "1px solid var(--contradiction-border)",
                    }}
                  >
                    <p
                      style={{
                        fontSize: 11,
                        color: "var(--text-secondary)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 8,
                      }}
                    >
                      Web
                    </p>
                    <p
                      style={{
                        fontSize: 13,
                        color: "var(--text-primary)",
                        lineHeight: 1.6,
                        marginBottom: 8,
                      }}
                    >
                      {item.web_claim}
                    </p>
                    <p
                      style={{
                        fontSize: 12,
                        color: "var(--text-secondary)",
                        fontStyle: "italic",
                        lineHeight: 1.5,
                      }}
                    >
                      "{item.web_quote}"
                    </p>
                    {item.source_url && item.source_url !== "N/A" && (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          fontSize: 11,
                          color: "var(--text-secondary)",
                          marginTop: 8,
                          display: "block",
                          textDecoration: "none",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        ↗{" "}
                        {item.source_url.replace("https://", "").split("/")[0]}
                      </a>
                    )}
                  </div>

                  {/* Paper side */}
                  <div style={{ padding: "16px 20px" }}>
                    <p
                      style={{
                        fontSize: 11,
                        color: "var(--text-secondary)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 8,
                      }}
                    >
                      Paper
                    </p>
                    <p
                      style={{
                        fontSize: 13,
                        color: "var(--text-primary)",
                        lineHeight: 1.6,
                        marginBottom: 8,
                      }}
                    >
                      {item.paper_claim}
                    </p>
                    <p
                      style={{
                        fontSize: 12,
                        color: "var(--text-secondary)",
                        fontStyle: "italic",
                        lineHeight: 1.5,
                      }}
                    >
                      "{item.paper_quote}"
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ height: 48 }} />
    </div>
  );
}

function Quote({ label, text, url }) {
  if (!text || text === "N/A") return null;
  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        alignItems: "flex-start",
      }}
    >
      <span
        style={{
          fontSize: 11,
          color: "var(--text-secondary)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          paddingTop: 2,
          minWidth: 36,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: 13,
          color: "var(--text-secondary)",
          fontStyle: "italic",
          lineHeight: 1.5,
        }}
      >
        "{text}"
        {url && url !== "N/A" && (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            style={{
              marginLeft: 6,
              color: "var(--text-secondary)",
              textDecoration: "none",
              fontSize: 11,
            }}
          >
            ↗
          </a>
        )}
      </span>
    </div>
  );
}
