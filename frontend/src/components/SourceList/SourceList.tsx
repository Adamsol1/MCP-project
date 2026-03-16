import type { Source } from "../../types/conversation";

interface SourceListProps {
  sources: Source[];
  highlightedRefs: string[];
  onSourceHover: (refs: string[]) => void;
}

export default function SourceList({ sources, highlightedRefs, onSourceHover }: SourceListProps) {
  if (sources.length === 0) return <ul></ul>;   // empty but still a DOM node

  return (
    <ul className="space-y-0 divide-y divide-border-muted">
      {sources.map((source) => {
        const isHighlighted = highlightedRefs.includes(source.ref);
        const citation = source.citation;

        return (
          <li
            key={source.id}
            className={[
              "flex items-baseline gap-2 py-1.5 text-xs transition-colors cursor-default",
              isHighlighted
                ? "text-primary"
                : "text-text-secondary hover:text-text-primary",
            ].join(" ")}
            onMouseEnter={() => onSourceHover([source.ref])}
            onMouseLeave={() => onSourceHover([])}
          >
            <span
              className={[
                "shrink-0 font-semibold tabular-nums",
                isHighlighted ? "text-primary" : "text-text-muted",
              ].join(" ")}
            >
              {source.ref}
            </span>
            <span className="min-w-0">
              {citation ? (
                <>
                  {citation.author}. ({citation.year}). <em>{citation.title}</em>.{" "}
                  {citation.publisher}.
                </>
              ) : (
                source.id
              )}
              <span className="ml-1.5 text-[10px] font-medium uppercase tracking-wider text-text-muted">
                [{source.source_type}]
              </span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
