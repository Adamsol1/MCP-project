import { useToast } from "../../hooks/useToast/useToast";
import Toast from "./Toast";

/** All supported anchor positions for the toast stack. */
type Position =
  | "top-right"
  | "top-left"
  | "bottom-right"
  | "bottom-left"
  | "top-center"
  | "bottom-center"
  | "above-input";

interface ToastContainerProps {
  /**
   * Where on the screen to anchor the toast stack.
   * Defaults to 'top-right'.
   * Use 'above-input' to float the stack just above the chat input form,
   * dynamically matching the chatbox width.
   */
  position?: Position;
}

/**
 * Per-position layout config.
 *
 * positioning — 'fixed' floats over the viewport; 'absolute' anchors to the
 *               nearest positioned ancestor (used for above-input so the stack
 *               automatically matches the chatbox width).
 * classes     — Tailwind utilities that set the offset / size for that anchor.
 */
const positionConfig: Record<
  Position,
  { positioning: "fixed" | "absolute"; classes: string }
> = {
  "top-right": { positioning: "fixed", classes: "top-16 right-14" },
  "top-left": { positioning: "fixed", classes: "top-4 left-4" },
  "bottom-right": { positioning: "fixed", classes: "bottom-4 right-4" },
  "bottom-left": { positioning: "fixed", classes: "bottom-4 left-4" },
  "top-center": {
    positioning: "fixed",
    classes: "top-16 left-1/2 -translate-x-1/2",
  },
  "bottom-center": {
    positioning: "fixed",
    classes: "bottom-4 left-1/2 -translate-x-1/2",
  },
  // Anchors to the relative wrapper inside ChatWindow so the stack width
  // automatically tracks the chatbox. bottom-full places it just above the form.
  "above-input": {
    positioning: "absolute",
    classes: "bottom-full left-0 w-full pb-2",
  },
};

/**
 * Renders all active toasts stacked in a fixed overlay at the chosen position.
 *
 * Reads the toast list from ToastContext via useToast() so it can be placed
 * anywhere in the component tree without prop drilling.
 * Returns null (renders nothing at all) when there are no active toasts,
 * keeping the DOM clean when the notification system is idle.
 *
 * @param position - Where to anchor the stack. Defaults to 'top-right'.
 */
export default function ToastContainer({
  position = "top-right",
}: ToastContainerProps) {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) {
    return null;
  }

  const { positioning, classes } = positionConfig[position];
  const fullWidth = position === "above-input";

  return (
    <div className={`${positioning} z-50 flex flex-col gap-2 ${classes}`}>
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          id={toast.id}
          type={toast.type}
          message={toast.message}
          duration={toast.duration}
          onClose={removeToast}
          fullWidth={fullWidth}
        />
      ))}
    </div>
  );
}
