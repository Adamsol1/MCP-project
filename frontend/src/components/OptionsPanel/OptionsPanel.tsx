import { useState } from "react";
import PerspectiveSelector from "../PerspectiveSelector/PerspectiveSelector";

interface OptionsPanelProps {
  selectedPerspectives: string[];
  onPerspectiveChange: (perspectives: string[]) => void;
  onOpenFileUpload: () => void;
}

/**
 * OptionsPanel is the right-hand sidebar that exposes analysis configuration.
 *
 * It is collapsible: clicking the toggle button shrinks it to a narrow rail
 * (w-14) so the user can reclaim horizontal space without losing access to
 * the toggle itself. Collapse state is managed internally with useState.
 *
 * Contents (visible when expanded):
 *   - PerspectiveSelector  — choose which geopolitical angles to apply
 *   - Upload Files button  — opens the file-upload modal
 */
export function OptionsPanel({
  selectedPerspectives,
  onPerspectiveChange,
  onOpenFileUpload,
}: OptionsPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    // Width snaps instantly (no transition) to avoid content squishing,
    // matching the same decision made for the left Sidebar.
    <aside
      className={`${
        isCollapsed ? "w-14" : "w-64"
      } bg-gray-50 border-l border-gray-200 flex flex-col overflow-hidden`}
    >
      {/* Toggle button — chevron points left (collapse) when expanded,
          right (expand) when collapsed. Mirrors the left sidebar pattern. */}
      <button
        aria-label="Toggle options"
        onClick={() => setIsCollapsed((prev) => !prev)}
        className="p-2 flex items-center justify-center shrink-0 hover:bg-gray-200 rounded"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          {isCollapsed
            ? <path d="M15 18l-6-6 6-6" />  /* ‹ chevron-left  = expand  */
            : <path d="M9 18l6-6-6-6" />    /* › chevron-right = collapse */
          }
        </svg>
      </button>

      {/* Panel content — hidden when collapsed */}
      {!isCollapsed && (
        <div className="flex flex-col gap-4 p-4">
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
        </div>
      )}
    </aside>
  );
}