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
import { useT } from "../../i18n/useT";

export default function PerspectiveSelector({
  selected,
  onChange,
}: PerspectiveSelectorProps) {
  const t = useT();

  const perspectives = [
    { label: t.perspectiveLabels["NEUTRAL"], value: "NEUTRAL" },
    { label: t.perspectiveLabels["CHINA"], value: "CHINA" },
    { label: t.perspectiveLabels["EU"], value: "EU" },
    { label: t.perspectiveLabels["NORWAY"], value: "NORWAY" },
    { label: t.perspectiveLabels["RUSSIA"], value: "RUSSIA" },
    { label: t.perspectiveLabels["US"], value: "US" },
  ];

  /**
   * Toggles a single perspective on or off.
   * Safety net: if the resulting selection is empty, restore NEUTRAL.
   *
   * @param value - The perspective ID to toggle (e.g. "US").
   */
  const togglePerspective = (value: string) => {
    const isSelected = selected.includes(value);
    const isNeutralOnly = selected.length === 1 && selected[0] === "NEUTRAL";

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
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">
        {t.perspective}
      </p>

      <div className="grid grid-cols-2 gap-1">
        {perspectives.map((perspective) => {
          const isActive = selected.includes(perspective.value);
          return (
            <button
              key={perspective.value}
              onClick={() => togglePerspective(perspective.value)}
              aria-pressed={isActive}
              data-selected={isActive.toString()}
              className={`py-1.5 rounded text-[11px] font-semibold uppercase tracking-[0.08em] border transition-colors cursor-pointer ${
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
