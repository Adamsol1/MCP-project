import type { Claim } from "../../types/conversation";

interface CitationTextProps {
  text: string;
  claims: Claim[];
  highlightedRef: string | null;
  onRefHover: (ref: string | null) => void;
}

export default function CitationText({
  text,
  claims,
  highlightedRef,
  onRefHover,
}: CitationTextProps) {
  const parts = text.split(/(\[\d+\])/g);

  return (
    <span>
      {parts.map((part, i) => {
        if (part === "") return null; // Skip empty segments

        // find markers [1], [2], etc. using regex, and make them hoverable
        if (/^\[\d+\]$/.test(part)) {
          return (
            <sup
              key={i}
              onMouseEnter={() => onRefHover(part)}
              onMouseLeave={() => onRefHover(null)}
            >
              {part}
            </sup>
          );
        }


        // Look for a claim whose .text matches this segment (trim spaces before comparing)
        const claim = claims.find((c) => c.text === part.trim());

        if (claim) {
          const isHighlighted = highlightedRef === claim.source_ref;
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
        // "claim[1][2]" splits as ["claim", "[1]", "", "[2]", ...] — we skip empty
        // segments and gather every marker before the next real text.
        // This means hovering source [1] OR source [2] both highlight "claim".
        const followingRefs: string[] = [];
        let j = i + 1;
        while (j < parts.length) {
          if (parts[j] === "") { j++; continue; }
          if (/^\[\d+\]$/.test(parts[j])) { followingRefs.push(parts[j]); j++; }
          else break;
        }
        if (followingRefs.length > 0) {
          const isHighlighted =
            highlightedRef !== null && followingRefs.includes(highlightedRef);
          return (
            <span
              key={i}
              className={isHighlighted ? "bg-primary-subtle" : ""}
              onMouseEnter={() => onRefHover(followingRefs[0])}
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
