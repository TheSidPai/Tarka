/* Tarka's mark: one disc, cut once, the halves slid out of true — a single
   subject described two ways that no longer reconcile.

   Drawn in currentColor so a single definition serves both themes; the
   standalone copy lives in public/favicon.svg, which needs literal colours
   because a favicon has no page to inherit from. Geometry is shared between
   the two, so any change here belongs there as well. */
export default function Mark({ size = 28, style }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="currentColor"
      role="img"
      aria-label="Tarka"
      style={style}
    >
      {/* Offset is 12 horizontally against an 8 vertical gap. The specimen
          sheet used 8/8, which reads at 104px but collapses into a plain
          bisected disc — or a "no entry" sign — at UI sizes. The slip has to
          out-read the cut. */}
      {/* upper half, centred (44,46) */}
      <path d="M14 46 A30 30 0 0 1 74 46 Z" />
      {/* lower half, centred (56,54) */}
      <path d="M26 54 A30 30 0 0 0 86 54 Z" />
    </svg>
  );
}
