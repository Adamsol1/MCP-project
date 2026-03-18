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
    { label: "Neutral", value: "NEUTRAL" },
    { label: "China", value: "CHINA" },
    { label: "European Union", value: "EU" },
    { label: "Norway", value: "NORWAY" },
    { label: "Russia", value: "RUSSIA" },
    { label: "United States", value: "US" },
  ];

  /**
   * Toggles a single perspective on or off.
   * Safety net: if the resulting selection is empty, restore NEUTRAL.
   *
   * @param value - The perspective ID to toggle (e.g. "US").
   */
  const togglePerspective = (value: string) => {
    const isSelected = selected.includes(value);
    const isNeutralOnly =
      selected.length === 1 && selected[0] === "NEUTRAL";

    let updated: string[];
    if (isSelected) {
      updated = selected.filter((p) => p !== value);
    } else if (value !== "NEUTRAL" && isNeutralOnly) {
      // First non-neutral pick replaces default NEUTRAL.
      updated = [value];
    } else {
      updated = [...selected, value];
    }

    // Safety net: if all perspectives were deselected, restore NEUTRAL as default.
    if (updated.length === 0) updated = ["NEUTRAL"];

    onChange(updated);
  };

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
        Perspectives
      </p>

      <div className="flex flex-wrap gap-1.5">
        {perspectives.map((perspective) => {
          const isActive = selected.includes(perspective.value);
          return (
            <button
              key={perspective.value}
              onClick={() => togglePerspective(perspective.value)}
              aria-pressed={isActive}
              data-selected={isActive.toString()}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors cursor-pointer ${
                isActive
                  ? "bg-primary border-primary-dark text-text-inverse"
                  : "bg-surface border-border text-text-secondary hover:bg-primary-subtle hover:border-primary hover:text-primary"
              }`}
            >
              {perspective.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
