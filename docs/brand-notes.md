# Brand notes

Design decisions and parked options for Tarka's identity.

## In use

**Symbol — "Slipped"** — chosen 2026-09-04 from sheet 02.

One disc, cut once, the halves slid out of true: a single subject described two
ways that no longer reconcile. Chosen over ∴ and the opposed chevrons because it
has the most solid silhouette of the ten, which is what survives an app tile and
a 16px favicon — detail dies at that size, mass does not.

```
viewBox 0 0 100 100
upper half  M14 46 A30 30 0 0 1 74 46 Z   (centre 44,46 · r30)
lower half  M26 54 A30 30 0 0 0 86 54 Z   (centre 56,54 · r30)
```

Both are exact semicircles — endpoint distance equals 2r. The halves are offset
**12 units horizontally** against an **8 unit vertical gap**.

The specimen sheet drew this 8/8, which reads at 104px and fails at UI sizes:
at 44px an 8-unit offset is ~3.5px, and the mark collapses into a plain
bisected disc — or, worse, a "no entry" sign. The horizontal slip has to
out-read the horizontal cut, so it was widened to 12. Scale the pair; don't
narrow the offset back toward the gap.

Lives in two places that must change together:

- `frontend/src/components/Mark.jsx` — `currentColor`, so one definition serves
  both themes. Used at 46px above the wordmark on the empty state and at 23px
  beside it once results appear.
- `frontend/public/favicon.svg` — literal colours, because a favicon has no page
  to inherit from. Light ground (`#ECEDEF`) with an ink mark rather than the
  reverse: an ink tile disappears against dark browser chrome.

**Wordmark** — lowercase `tarka`, Playfair Display 400, tracking `-0.03em`.
Scoped to `--font-display` in `frontend/src/index.css` and used in
`SearchBar.jsx` at 76px (empty state) and 30px (inline, with results).

Playfair is the wordmark only. Its stroke contrast is right at display size and
tiring as body copy, so reading text stays on Source Serif 4 and UI chrome on
Inter.

## Parked

**Disagreement wordmark** — considered 2026-09-04, kept for later use.

```css
/* "tar" roman, "ka" bold italic — the word disagrees with itself mid-stride */
font-family: "Playfair Display", Georgia, serif;
letter-spacing: -0.03em;
/* span.a */ font-weight: 400; font-style: normal;
/* span.b */ font-weight: 700; font-style: italic;
```

```html
<span class="split"><span class="a">tar</span><span class="b">ka</span></span>
```

Two voices in one name — roman meets bold italic at the syllable break. Subtle
enough to survive in a header, and it needs no explanation to feel deliberately
off-balance. Requires Playfair Display 700 and its italic to be loaded; the
current font link only requests weights 400 and 500, so add `700` and `ital`
before using it.

## Specimen sheets

- Sheet 01 — wordmark directions: https://claude.ai/code/artifact/63c226dd-2593-437a-a6a0-7a176e0fb834
- Sheet 02 — icon marks: https://claude.ai/code/artifact/33ce38d3-08a4-4666-88e8-ccd97af6a2ea
