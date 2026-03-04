/**
 * Props for PerspectiveSelector.
 *
 * This is a controlled component — the parent owns the selected array and
 * passes updates back through onChange. The component never mutates the
 * selected array directly.
 */
interface PerspectiveSelectorProps {
  /** Array of perspective IDs currently active (e.g. ["NEUTRAL", "US"]). */
  selected: string[];
  /** Called with the updated array every time the user toggles a perspective. */
  onChange: (perspectives: string[]) => void;
}

/**
 * A list of toggle buttons for choosing geopolitical analysis perspectives.
 *
 * Each button represents one perspective (e.g. United States, EU, Russia).
 * Clicking a button toggles that perspective on or off and calls onChange
 * with the new selection — multiple perspectives can be active at once.
 *
 * Accessibility:
 *   - aria-pressed reflects the toggle state for screen readers
 *     (React serialises the boolean to "true" / "false" automatically).
 *   - data-selected mirrors the state as a string attribute for CSS/test hooks.
 */
export default function PerspectiveSelector({
  selected,
  onChange,
}: PerspectiveSelectorProps) {
  /**
   * Each perspective has a human-readable label shown in the button and a
   * value string used in the selected array and sent to the backend.
   */
  const perspectives = [
    { label: "United States", value: "US" },
    { label: "European Union", value: "EU" },
    { label: "Norway", value: "NORWAY" },
    { label: "China", value: "CHINA" },
    { label: "Russia", value: "RUSSIA" },
    { label: "Neutral", value: "NEUTRAL" },
  ];

  /**
   * Toggles a single perspective on or off.
   * Safety net: if the resulting selection is empty, restore NEUTRAL.
   *
   * @param value - The perspective ID to toggle (e.g. "US").
   */
  const togglePerspective = (value: string) => {
    let updated = selected.includes(value)
      ? selected.filter((p) => p !== value)
      : [...selected, value];

    // Safety net: if all perspectives were deselected, restore NEUTRAL as default.
    if (updated.length === 0) updated = ["NEUTRAL"];

    onChange(updated);
  };

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
        Perspectives
      </p>

      {/*
        .map() transforms the perspectives array into an array of button elements.
        React renders the returned array as a sequence of sibling nodes.
        key={perspective.value} lets React identify each button across re-renders.
      */}
      {perspectives.map((perspective) => (
        <button
          key={perspective.value}
          onClick={() => togglePerspective(perspective.value)}
          aria-pressed={selected.includes(perspective.value)}
          data-selected={selected.includes(perspective.value).toString()}
          className={`px-4 py-2 rounded border font-medium transition-colors ${
            selected.includes(perspective.value)
              ? "bg-primary text-text-inverse border-primary-dark"
              : "bg-surface text-text-primary border-border hover:bg-surface-muted"
          }`}
        >
          {perspective.label}
        </button>
      ))}
    </div>
  );
}
