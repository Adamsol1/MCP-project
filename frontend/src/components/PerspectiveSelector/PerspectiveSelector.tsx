// Props interface for PerspectiveSelector
// selected: array of perspective IDs currently chosen (e.g. ["NEUTRAL", "US"])
// onChange: callback that receives the updated array when user toggles a perspective
interface PerspectiveSelectorProps {
  selected: string[];
  onChange: (perspectives: string[]) => void;
}

// PerspectiveSelector is a controlled component — the parent owns the state.
// This component renders toggle buttons and reports changes via onChange.
export default function PerspectiveSelector({
  selected,
  onChange,
}: PerspectiveSelectorProps) {
  // Each perspective has a human-readable label (shown in the button)
  // and a value (the ID used in the selected array and sent to the backend)
  const perspectives = [
    { label: "United States", value: "US" },
    { label: "European Union", value: "EU" },
    { label: "Norway", value: "NORWAY" },
    { label: "China", value: "CHINA" },
    { label: "Russia", value: "RUSSIA" },
    { label: "Neutral", value: "NEUTRAL" },
  ];

  // Toggle a perspective on or off.
  // If already selected → remove it (filter it out).
  // If not selected → add it (spread existing + append new).
  // Then notify the parent via onChange with the new array.
  const togglePerspective = (value: string) => {
    let updatedPerspectives: string[];
    if (selected.includes(value)) {
      // filter keeps every item where the callback returns true,
      // so we keep everything that is NOT the clicked value
      updatedPerspectives = selected.filter((p) => p !== value);
    } else {
      updatedPerspectives = [...selected, value];
    }
    onChange(updatedPerspectives);
  };

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-lg font-bold text-gray-900">Perspectives</h2>
      {/* .map() transforms the perspectives array into button elements.
          React renders the returned array of JSX elements. */}
      {perspectives.map((perspective) => (
        <button
          key={perspective.value}
          onClick={() => togglePerspective(perspective.value)}
          // aria-pressed: accessibility attribute for screen readers
          // React auto-converts the boolean to "true"/"false" for aria-* attrs
          aria-pressed={selected.includes(perspective.value)}
          // data-selected: custom attribute for CSS styling hooks
          // HTML data attributes are always strings, so we need .toString()
          data-selected={selected.includes(perspective.value).toString()}
          className={`px-4 py-2 rounded border font-medium transition-colors ${
            selected.includes(perspective.value)
              ? "bg-blue-500 text-white border-blue-600"
              : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
          }`}
        >
          {perspective.label}
        </button>
      ))}
    </div>
  );
}
