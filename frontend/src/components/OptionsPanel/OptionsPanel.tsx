import PerspectiveSelector from "../PerspectiveSelector/PerspectiveSelector";

interface OptionsPanelProps {
  selectedPerspectives: string[];
  onPerspectiveChange: (perspectives: string[]) => void;
  onOpenFileUpload: () => void;
}

export function OptionsPanel({
  selectedPerspectives,
  onPerspectiveChange,
  onOpenFileUpload,
}: OptionsPanelProps) {
  return (
    <aside className="w-64 bg-gray-50 border-l border-gray-200 p-4 flex flex-col gap-4">
      <PerspectiveSelector
        selected={selectedPerspectives}
        onChange={onPerspectiveChange}
      />

      <button
        onClick={onOpenFileUpload}
        className="p-2 bg-blue-600 text-white rounded"
      >
        Upload Files
      </button>
    </aside>
  );
}
