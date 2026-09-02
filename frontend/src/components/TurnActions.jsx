import { useState } from "react";
import {
  copyText,
  downloadText,
  papersToBibTeX,
  papersToRIS,
  slugify,
  turnToMarkdown,
} from "../lib/export";

const BTN = {
  background: "none",
  border: "1px solid var(--border)",
  borderRadius: 7,
  padding: "6px 11px",
  color: "var(--text-secondary)",
  fontFamily: "var(--font-sans)",
  fontSize: 11.5,
  letterSpacing: "0.02em",
  cursor: "pointer",
  transition: "color 0.15s, border-color 0.15s",
};

function Action({ label, done, onClick, title }) {
  return (
    <button
      title={title}
      onClick={onClick}
      style={BTN}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = "var(--text-primary)";
        e.currentTarget.style.borderColor = "var(--text-secondary)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = "var(--text-secondary)";
        e.currentTarget.style.borderColor = "var(--border)";
      }}
    >
      {done ? "Copied" : label}
    </button>
  );
}

export default function TurnActions({ turn, sources }) {
  const [copied, setCopied] = useState(null);

  if (!turn.synthesis) return null;
  const papers = sources?.papers ?? [];
  const stem = slugify(turn.query);

  async function copy(kind, text) {
    if (await copyText(text)) {
      setCopied(kind);
      setTimeout(() => setCopied(null), 1600);
    }
  }

  return (
    // Excluded from print — see the @media print block in index.css
    <div className="no-print" style={{ display: "flex", gap: 8, marginTop: 18, flexWrap: "wrap" }}>
      <Action
        label="Copy Markdown"
        done={copied === "md"}
        title="Copy this answer with quotes and links, ready to paste into a doc"
        onClick={() => copy("md", turnToMarkdown(turn, sources))}
      />
      {papers.length > 0 && (
        <>
          <Action
            label={`Copy BibTeX (${papers.length})`}
            done={copied === "bib"}
            title="Copy the academic sources as BibTeX entries"
            onClick={() => copy("bib", papersToBibTeX(papers))}
          />
          <Action
            label=".ris"
            title="Download RIS for Zotero, Mendeley or EndNote"
            onClick={() => downloadText(`${stem}.ris`, papersToRIS(papers), "application/x-research-info-systems")}
          />
          <Action
            label=".bib"
            title="Download a BibTeX file"
            onClick={() => downloadText(`${stem}.bib`, papersToBibTeX(papers), "application/x-bibtex")}
          />
        </>
      )}
      <Action
        label="Print / PDF"
        title="Opens the print dialogue — choose 'Save as PDF' to export"
        onClick={() => window.print()}
      />
    </div>
  );
}
