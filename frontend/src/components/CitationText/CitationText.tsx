import type { Claim } from "../../types/conversation";

interface CitationTextProps {
  text: string;
  claims: Claim[];
  highlightedRef?: string | null;
  highlightedRefs?: string[];
  onRefHover: (refs: string[] | string | null) => void;
}

/**
 * Build a map from part-index → the full group of consecutive [N] markers that
 * part belongs to (or is adjacent to). This lets hovering any marker in [1][2]
 * emit both refs, highlighting both sources.
 */
function buildMarkerGroups(parts: string[]): Map<number, string[]> {
  const groups = new Map<number, string[]>();
  let i = 0;
  while (i < parts.length) {
    if (parts[i] === "") { i++; continue; }
    if (/^\[\d+\]$/.test(parts[i])) {
      // Collect the full run of consecutive markers (skipping empty strings)
      const group: number[] = [i];
      let j = i + 1;
      while (j < parts.length) {
        if (parts[j] === "") { j++; continue; }
        if (/^\[\d+\]$/.test(parts[j])) { group.push(j); j++; }
        else break;
      }
      const refs = group.map((idx) => parts[idx]);
      for (const idx of group) groups.set(idx, refs);
      i = j;
    } else {
      i++;
    }
  }
  return groups;
}

export default function CitationText({
  text,
  claims,
  highlightedRef = null,
  highlightedRefs,
  onRefHover,
}: CitationTextProps) {
  const activeHighlightedRefs = highlightedRefs ?? (highlightedRef ? [highlightedRef] : []);
  const parts = text.split(/(\[\d+\])/g);
  const markerGroups = buildMarkerGroups(parts);

  return (
    <span>
      {parts.map((part, i) => {
        if (part === "") return null; // Skip empty segments

        // [N] marker — emit its full group on hover
        if (/^\[\d+\]$/.test(part)) {
          const group = markerGroups.get(i) ?? [part];
          const isHighlighted = group.some((r) => activeHighlightedRefs.includes(r));
          return (
            <sup
              key={i}
              className={isHighlighted ? "text-primary" : undefined}
              onMouseEnter={() => onRefHover(group.length === 1 ? group[0] : group)}
              onMouseLeave={() => onRefHover(null)}
            >
              {part}
            </sup>
          );
        }

        // Look for a claim whose .text matches this segment (trim spaces before comparing)
        const claim = claims.find((c) => c.text === part.trim());

        if (claim) {
          const isHighlighted = activeHighlightedRefs.includes(claim.source_ref);
          return (
            <span
              key={i}
              className={isHighlighted ? "bg-primary-subtle" : ""}
              onMouseEnter={() => onRefHover(claim.source_ref)}
              onMouseLeave={() => onRefHover(null)}
            >
              {part}
            </span>
          );
        }

        // Fallback: collect ALL consecutive [N] markers immediately after this segment.
        const followingRefs: string[] = [];
        let j = i + 1;
        while (j < parts.length) {
          if (parts[j] === "") { j++; continue; }
          if (/^\[\d+\]$/.test(parts[j])) { followingRefs.push(parts[j]); j++; }
          else break;
        }
        if (followingRefs.length > 0) {
          const isHighlighted = followingRefs.some((r) => activeHighlightedRefs.includes(r));
          return (
            <span
              key={i}
              className={isHighlighted ? "bg-primary-subtle" : ""}
              onMouseEnter={() =>
                onRefHover(followingRefs.length === 1 ? followingRefs[0] : followingRefs)
              }
              onMouseLeave={() => onRefHover(null)}
            >
              {part}
            </span>
          );
        }

        // plain prose, no claim, no hover
        return <span key={i}>{part}</span>;
      })}
    </span>
  );
}
