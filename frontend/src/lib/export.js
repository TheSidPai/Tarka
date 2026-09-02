// Turning a completed turn into something usable elsewhere: Markdown for
// writing, BibTeX/RIS for reference managers.

export function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return (url || "").replace(/^https?:\/\//, "").split("/")[0];
  }
}

/* ---------------------------------------------------------------- Markdown */

function quoteBlock(text, attribution) {
  if (!text || text === "N/A") return [];
  const lines = [`> ${text.replace(/\n+/g, " ")}`];
  if (attribution) lines.push(`> — ${attribution}`);
  return [...lines, ""];
}

export function turnToMarkdown(turn, sources = { web: [], papers: [] }) {
  const s = turn.synthesis;
  if (!s) return "";
  const out = [`## ${turn.query}`, "", s.summary, ""];

  out.push(
    `*${s.source_count?.web ?? 0} web sources · ${s.source_count?.papers ?? 0} academic papers*`,
    ""
  );

  if (s.contradictions?.length) {
    out.push("### Contradictions", "");
    for (const c of s.contradictions) {
      out.push(`**${c.conflict_topic}**`, "");
      out.push(`*Web:* ${c.web_claim}`, "");
      out.push(...quoteBlock(c.web_quote, c.source_url && c.source_url !== "N/A"
        ? `[${domainOf(c.source_url)}](${c.source_url})` : null));
      out.push(`*Paper:* ${c.paper_claim}`, "");
      out.push(...quoteBlock(c.paper_quote, null));
    }
  }

  if (s.consensus?.length) {
    out.push("### Consensus", "");
    for (const c of s.consensus) {
      out.push(`**${c.point}**`, "");
      out.push(...quoteBlock(c.web_quote, c.source_url && c.source_url !== "N/A"
        ? `[${domainOf(c.source_url)}](${c.source_url})` : "web"));
      out.push(...quoteBlock(c.paper_quote, "paper"));
    }
  }

  if (sources.web?.length || sources.papers?.length) {
    out.push("### Sources", "");
    if (sources.web?.length) {
      out.push("**Web**", "");
      sources.web.forEach((w, i) =>
        out.push(`${i + 1}. [${w.title || domainOf(w.url)}](${w.url})`)
      );
      out.push("");
    }
    if (sources.papers?.length) {
      out.push("**Academic**", "");
      sources.papers.forEach((p, i) => {
        const bits = [p.title];
        if (p.year) bits.push(`(${p.year})`);
        if (p.venue) bits.push(`*${p.venue}*`);
        if (p.doi) bits.push(`doi:${p.doi}`);
        if (p.cited_by_count) bits.push(`— cited ${p.cited_by_count} times`);
        out.push(`${i + 1}. ${bits.join(" ")}`);
      });
      out.push("");
    }
  }

  return out.join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
}

export function threadToMarkdown(turns, sources) {
  const body = turns
    .filter((t) => t.synthesis)
    .map((t) => turnToMarkdown(t, sources))
    .join("\n---\n\n");
  return `# Tarka — ${turns[0]?.query ?? "Research"}\n\n${body}`;
}

/* ------------------------------------------------------------- Citations */

// Best effort: our author strings are "First Last, First Last" full names, so
// the surname is taken as the final token of each name.
function surname(fullName) {
  const parts = (fullName || "").trim().split(/\s+/);
  return parts.length ? parts[parts.length - 1] : "";
}

function authorList(authors) {
  return (authors || "")
    .split(",")
    .map((a) => a.trim())
    .filter(Boolean);
}

function bibEscape(s) {
  return (s || "").replace(/[{}]/g, "").replace(/[&%$#_]/g, (m) => `\\${m}`);
}

function citeKey(paper, taken) {
  const first = authorList(paper.authors)[0];
  const name = (surname(first) || "anon").toLowerCase().replace(/[^a-z]/g, "");
  const word = (paper.title || "ref")
    .toLowerCase()
    .split(/\s+/)
    .find((w) => w.length > 3) || "ref";
  let key = `${name}${paper.year || "n.d."}${word.replace(/[^a-z]/g, "")}`;
  let n = 1;
  while (taken.has(key)) key = `${key}${String.fromCharCode(96 + ++n)}`;
  taken.add(key);
  return key;
}

export function papersToBibTeX(papers) {
  const taken = new Set();
  return (papers || [])
    .filter((p) => p.title)
    .map((p) => {
      const fields = [
        ["title", `{${bibEscape(p.title)}}`],
        ["author", `{${authorList(p.authors).map(bibEscape).join(" and ")}}`],
        p.year ? ["year", `{${p.year}}`] : null,
        p.venue ? ["journal", `{${bibEscape(p.venue)}}`] : null,
        p.doi ? ["doi", `{${p.doi}}`] : null,
        p.paper_id ? ["url", `{${p.paper_id}}`] : null,
      ].filter(Boolean);
      const body = fields.map(([k, v]) => `  ${k} = ${v}`).join(",\n");
      return `@article{${citeKey(p, taken)},\n${body}\n}`;
    })
    .join("\n\n") + "\n";
}

export function papersToRIS(papers) {
  return (papers || [])
    .filter((p) => p.title)
    .map((p) => {
      const lines = ["TY  - JOUR", `TI  - ${p.title}`];
      for (const a of authorList(p.authors)) {
        const last = surname(a);
        const rest = a.replace(new RegExp(`\\s*${last}$`), "").trim();
        lines.push(`AU  - ${rest ? `${last}, ${rest}` : last}`);
      }
      if (p.year) lines.push(`PY  - ${p.year}`);
      if (p.venue) lines.push(`JO  - ${p.venue}`);
      if (p.doi) lines.push(`DO  - ${p.doi}`);
      if (p.paper_id) lines.push(`UR  - ${p.paper_id}`);
      lines.push("ER  - ");
      return lines.join("\n");
    })
    .join("\n\n") + "\n";
}

/* ----------------------------------------------------------------- Output */

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Clipboard API needs a secure context; fall back to a temp selection.
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
}

export function downloadText(filename, text, mime = "text/plain") {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function slugify(text, max = 40) {
  return (text || "tarka")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, max) || "tarka";
}
