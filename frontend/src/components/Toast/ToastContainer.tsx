import { useToast } from '../../hooks/useToast';
import Toast from './Toast';

/** All supported anchor positions for the toast stack. */
type Position = 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center' | 'above-input';

interface ToastContainerProps {
  /**
   * Where on the screen to anchor the toast stack.
   * Defaults to 'top-right'.
   * Use 'above-input' to float the stack just above the chat input form.
   */
  position?: Position;
}

/**
 * Maps each position key to Tailwind utility classes for that screen location.
 * All positions use fixed layout so the stack floats on top of page content
 * regardless of scroll position.
 *
 * 'above-input' sits ~128px from the viewport bottom — just above the chat
 * input form (pb-6 outer gap ≈ 24px + ~96px form height = ~120px total).
 */
const positionClasses: Record<Position, string> = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-center': 'top-4 left-1/2 -translate-x-1/2',
  'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
  // Sits just above the chat input form (pb-6 outer gap + ~96px form height = ~120px from bottom).
  'above-input': 'bottom-32 left-1/2 -translate-x-1/2',
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
export default function ToastContainer({ position = 'top-right' }: ToastContainerProps) {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className={`fixed z-50 flex flex-col gap-2 ${positionClasses[position]}`}>
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          id={toast.id}
          type={toast.type}
          message={toast.message}
          duration={toast.duration}
          onClose={removeToast}
        />
      ))}
    </div>
  );
}
