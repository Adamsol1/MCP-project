import { useState } from "react";
import PerspectiveSelector from "../PerspectiveSelector/PerspectiveSelector";

/** Props for the OptionsPanel component. */
interface OptionsPanelProps {
  /** The currently active geopolitical perspectives for the active conversation. */
  selectedPerspectives: string[];
  /** Called with the updated perspectives array when the user toggles one. */
  onPerspectiveChange: (perspectives: string[]) => void;
  /** Called when the user clicks the Upload Files button. */
  onOpenFileUpload: () => void;
}

/**
 * Right-hand sidebar that exposes analysis configuration for the active conversation.
 *
 * Collapsible: clicking the toggle button shrinks the panel to a slim w-14 icon
 * rail so the user can reclaim horizontal space without losing the toggle itself.
 * Width snaps instantly (no CSS transition) to avoid content squishing — matching
 * the same decision made for the left Sidebar.
 *
 * Contents (visible when expanded):
 *   - PerspectiveSelector — toggles for geopolitical analysis angles.
 *   - Upload Files button — opens the FileUploadModal overlay.
 *
 * Local state:
 *   isCollapsed — whether the panel is in its narrow rail mode.
 */
export function OptionsPanel({
  selectedPerspectives,
  onPerspectiveChange,
  onOpenFileUpload,
}: OptionsPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside
      className={`${
        isCollapsed ? "w-14" : "w-64"
      } bg-gray-50 border-l border-gray-200 flex flex-col overflow-hidden`}
    >
      {/* Toggle button — chevron points left (‹) when expanded to signal "collapse",
          right (›) when collapsed to signal "expand".
          Mirrors the chevron logic used in the left Sidebar. */}
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

      {/* Panel content — hidden entirely when collapsed. */}
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
