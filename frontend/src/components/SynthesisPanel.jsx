import { useState } from "react";

const LABEL = {
  fontSize: 11,
  fontWeight: 500,
  color: "var(--text-secondary)",
  textTransform: "uppercase",
  letterSpacing: "0.1em",
};

function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url?.replace(/^https?:\/\//, "").split("/")[0] ?? "";
  }
}

function Favicon({ url, size = 14 }) {
  const [failed, setFailed] = useState(false);
  const domain = domainOf(url);
  if (!domain || failed) return null;
  return (
    <img
      src={`https://www.google.com/s2/favicons?domain=${domain}&sz=32`}
      alt=""
      width={size}
      height={size}
      onError={() => setFailed(true)}
      style={{ borderRadius: 3, flexShrink: 0, opacity: 0.85 }}
    />
  );
}

function SourceLink({ url }) {
  if (!url || url === "N/A") return null;
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: 11,
        color: "var(--text-secondary)",
        textDecoration: "none",
        marginTop: 10,
        maxWidth: "100%",
        overflow: "hidden",
      }}
    >
      <Favicon url={url} />
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {domainOf(url)}
      </span>
    </a>
  );
}

/* The corpus was already fetched and sent to the client — 30 sources that
   the UI previously never showed. Collapsed behind the source count. */
function SourceList({ web, papers }) {
  return (
    <div
      style={{
        marginTop: 14,
        paddingTop: 14,
        borderTop: "1px solid var(--border)",
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 24,
      }}
    >
      <div>
        <p style={{ ...LABEL, marginBottom: 10 }}>
          Web · <span className="tnum">{web.length}</span>
        </p>
        <ol style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 9 }}>
          {web.map((w, i) => (
            <li key={i} style={{ fontSize: 12, lineHeight: 1.45 }}>
              <a
                href={w.url}
                target="_blank"
                rel="noreferrer"
                style={{ color: "var(--text-primary)", textDecoration: "none" }}
              >
                {w.title || domainOf(w.url)}
              </a>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  marginLeft: 6,
                  color: "var(--text-secondary)",
                  fontSize: 11,
                }}
              >
                <Favicon url={w.url} size={12} />
                {domainOf(w.url)}
              </span>
            </li>
          ))}
        </ol>
      </div>

      <div>
        <p style={{ ...LABEL, marginBottom: 10 }}>
          Papers · <span className="tnum">{papers.length}</span>
        </p>
        <ol style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 9 }}>
          {papers.map((p, i) => (
            <li key={i} style={{ fontSize: 12, lineHeight: 1.45, color: "var(--text-primary)" }}>
              {p.doi ? (
                <a
                  href={`https://doi.org/${p.doi}`}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: "var(--text-primary)", textDecoration: "none" }}
                >
                  {p.title}
                </a>
              ) : (
                p.title
              )}
              <span style={{ color: "var(--text-secondary)", fontSize: 11 }}>
                {p.year ? ` · ${p.year}` : ""}
                {p.venue ? ` · ${p.venue}` : ""}
                {p.cited_by_count ? (
                  <>
                    {" · "}
                    <span className="tnum">{p.cited_by_count.toLocaleString()}</span> cites
                  </>
                ) : null}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export default function SynthesisPanel({ synthesis, sources }) {
  const [showSources, setShowSources] = useState(false);
  if (!synthesis) return null;

  const { summary, consensus, contradictions, source_count } = synthesis;
  const web = sources?.web ?? [];
  const papers = sources?.papers ?? [];
  const canExpand = web.length > 0 || papers.length > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28, marginTop: 20 }}>
      {/* Overview — the most-read text on the page, so it leads in serif */}
      <div
        style={{
          padding: "22px 26px",
          borderRadius: 12,
          border: "1px solid var(--border)",
          background: "var(--card-bg)",
        }}
      >
        <button
          onClick={() => canExpand && setShowSources((s) => !s)}
          disabled={!canExpand}
          style={{
            ...LABEL,
            background: "none",
            border: "none",
            padding: 0,
            marginBottom: 12,
            cursor: canExpand ? "pointer" : "default",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontFamily: "var(--font-sans)",
          }}
        >
          <span>
            Overview · <span className="tnum">{source_count?.web ?? 0}</span> web ·{" "}
            <span className="tnum">{source_count?.papers ?? 0}</span> papers
          </span>
          {canExpand && (
            <span
              style={{
                transform: showSources ? "rotate(180deg)" : "none",
                transition: "transform 0.2s ease",
                fontSize: 9,
              }}
            >
              ▼
            </span>
          )}
        </button>

        <p
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 17,
            color: "var(--text-primary)",
            lineHeight: 1.65,
            // The card is wide now; prose still wants a readable measure.
            maxWidth: "74ch",
          }}
        >
          {summary}
        </p>

        {/* Always mounted so the print stylesheet can reveal it — a
            conditionally rendered node can't be un-hidden by CSS. */}
        {canExpand && (
          <div className="sources" data-open={showSources ? "true" : "false"}>
            <SourceList web={web} papers={papers} />
          </div>
        )}
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

      {/* Contradictions lead — they're the point of the product */}
      {contradictions?.length > 0 && (
        <div>
          <h2 style={{ ...LABEL, marginBottom: 12 }}>
            Contradictions · <span className="tnum">{contradictions.length}</span>
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {contradictions.map((item, i) => (
              <div
                key={i}
                style={{
                  borderRadius: 12,
                  border: "1px solid var(--contradiction-border)",
                  borderLeft: "3px solid var(--contradiction-border)",
                  background: "var(--contradiction-bg)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "14px 22px",
                    borderBottom: "1px solid var(--contradiction-border)",
                  }}
                >
                  <p
                    style={{
                      fontFamily: "var(--font-serif)",
                      fontSize: 15,
                      fontWeight: 600,
                      color: "var(--text-primary)",
                      lineHeight: 1.45,
                    }}
                  >
                    {item.conflict_topic}
                  </p>
                </div>

                {/* Two opposed claims, with the divider made explicit */}
                <div style={{ position: "relative", display: "grid", gridTemplateColumns: "1fr 1fr" }}>
                  <ClaimSide
                    label="Web"
                    claim={item.web_claim}
                    quote={item.web_quote}
                    url={item.source_url}
                    borderRight
                  />
                  <ClaimSide label="Paper" claim={item.paper_claim} quote={item.paper_quote} />
                  <span
                    style={{
                      position: "absolute",
                      left: "50%",
                      top: "50%",
                      transform: "translate(-50%, -50%)",
                      background: "var(--bg-primary)",
                      border: "1px solid var(--contradiction-border)",
                      color: "var(--text-secondary)",
                      borderRadius: 999,
                      padding: "2px 9px",
                      fontSize: 10,
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                      pointerEvents: "none",
                    }}
                  >
                    vs
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Consensus */}
      {consensus?.length > 0 && (
        <div>
          <h2 style={{ ...LABEL, marginBottom: 12 }}>
            Consensus · <span className="tnum">{consensus.length}</span>
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
                    fontFamily: "var(--font-serif)",
                    fontSize: 15,
                    color: "var(--text-primary)",
                    marginBottom: 12,
                    lineHeight: 1.5,
                  }}
                >
                  {item.point}
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <Quote label="Web" text={item.web_quote} url={item.source_url} />
                  <Quote label="Paper" text={item.paper_quote} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ClaimSide({ label, claim, quote, url, borderRight }) {
  return (
    <div
      style={{
        padding: "18px 22px",
        borderRight: borderRight ? "1px solid var(--contradiction-border)" : "none",
      }}
    >
      <p style={{ ...LABEL, marginBottom: 9 }}>{label}</p>
      <p
        style={{
          fontSize: 13.5,
          color: "var(--text-primary)",
          lineHeight: 1.6,
          marginBottom: 10,
        }}
      >
        {claim}
      </p>
      <p
        style={{
          fontFamily: "var(--font-serif)",
          fontSize: 13,
          color: "var(--text-secondary)",
          fontStyle: "italic",
          lineHeight: 1.6,
          borderLeft: "2px solid var(--border)",
          paddingLeft: 12,
        }}
      >
        {quote}
      </p>
      <SourceLink url={url} />
    </div>
  );
}

function Quote({ label, text, url }) {
  if (!text || text === "N/A") return null;
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
      <span style={{ ...LABEL, paddingTop: 3, minWidth: 40, flexShrink: 0 }}>{label}</span>
      <div style={{ minWidth: 0 }}>
        <span
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 13,
            color: "var(--text-secondary)",
            fontStyle: "italic",
            lineHeight: 1.6,
          }}
        >
          {text}
        </span>
        {url && url !== "N/A" && (
          <span style={{ display: "block" }}>
            <SourceLink url={url} />
          </span>
        )}
      </div>
    </div>
  );
}
