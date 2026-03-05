import type { Source } from "../../types/conversation";

interface SourceListProps {
  sources: Source[];
  highlightedRef: string | null;
  onSourceHover: (ref: string | null) => void;
}

export default function SourceList({ sources, highlightedRef, onSourceHover }: SourceListProps) {
  if (sources.length === 0) return <ul></ul>;   // empty but still a DOM node

  return (
    <ul>
      {sources.map((source) => {
        const isHighlighted = highlightedRef === source.ref;
        const citation = source.citation;

        return (
          <li
            key={source.id}
            className={isHighlighted ? "bg-primary-subtle" : ""}
            onMouseEnter={() => onSourceHover(source.ref)}
            onMouseLeave={() => onSourceHover(null)}
          >
            <span>{source.ref}</span>
            {citation ? (
              <span>
                {citation.author}. ({citation.year}). <em>{citation.title}</em>. {citation.publisher}.
              </span>
            ) : (
              <span>{source.id}</span>
            )}
             <span> [{source.source_type}]</span>
          </li>
        );
      })}
    </ul>
  );
}
