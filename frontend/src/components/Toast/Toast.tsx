import { useEffect } from "react";
import type { ToastType } from "../../contexts/Toast/ToastContext";

interface ToastProps {
  /** UUID of this toast — passed back to onClose so the correct toast is removed. */
  id: string;
  /** Severity level — controls colour scheme and icon. */
  type: ToastType;
  /** Human-readable text displayed inside the bubble. */
  message: string;
  /** Milliseconds before the toast auto-dismisses. */
  duration: number;
  /** Called with this toast's id when the timer expires or the user clicks ×. */
  onClose: (id: string) => void;
  /**
   * When true, the toast stretches to fill its container's full width instead of
   * using the default min/max-w constraints. Used by ToastContainer in above-input
   * mode so the toast dynamically matches the chatbox width.
   */
  fullWidth?: boolean;
}

/**
 * Tailwind class strings for each severity level.
 * Applied to the outermost div to colour the background, border, and text together.
 */
const typeStyles: Record<ToastType, string> = {
  success: "bg-success-subtle border-success text-success-text",
  error: "bg-error-subtle border-error text-error-text",
  warning: "bg-warning-subtle border-warning text-warning-text",
  info: "bg-info-subtle border-info text-info-text",
};

/**
 * Unicode icon characters displayed on the left of each toast.
 * ✓ success  ✕ error  ⚠ warning  ℹ info
 */
const icons: Record<ToastType, string> = {
  success: "\u2713",
  error: "\u2715",
  warning: "\u26A0",
  info: "\u2139",
};

/**
 * A single toast notification bubble.
 *
 * Auto-dismisses after `duration` milliseconds via a useEffect timer.
 * The cleanup function cancels the timer if the component unmounts before it
 * fires (e.g. the user closed the toast manually), preventing a stale call
 * to onClose on an already-removed toast.
 *
 * Accessibility:
 *   - role="alert" causes screen readers to announce the notification immediately.
 *   - aria-live="assertive" is used for errors so they interrupt the user;
 *     "polite" is used for all other types, waiting for a pause in activity.
 *
 * @param id       - UUID used to identify this toast when calling onClose.
 * @param type     - Severity level — controls colour scheme and icon.
 * @param message  - Text displayed inside the bubble.
 * @param duration - Milliseconds before auto-dismiss.
 * @param onClose  - Called with the toast id when the timer fires or × is clicked.
 */
export default function Toast({
  id,
  type,
  message,
  duration,
  onClose,
  fullWidth = false,
}: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose(id);
    }, duration);

    // Cleanup: cancel the timer if the toast is removed before it fires.
    return () => clearTimeout(timer);
  }, [id, duration, onClose]);

  return (
    <div
      role="alert"
      aria-live={type === "error" ? "assertive" : "polite"}
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border-2 shadow-lg animate-[slideIn_0.3s_ease-out] ${fullWidth ? "w-full" : "min-w-80 max-w-md"} ${typeStyles[type]}`}
    >
      <span className="text-lg">{icons[type]}</span>
      <p className="flex-1 text-sm font-medium">{message}</p>
      <button
        type="button"
        onClick={() => onClose(id)}
        className="text-text-muted hover:text-text-secondary font-bold text-xl leading-none"
        aria-label="Close notification"
      >
        &times;
      </button>
    </div>
  );
}
