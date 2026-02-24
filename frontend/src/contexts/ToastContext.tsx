import { createContext, useReducer, useCallback, type ReactNode } from 'react';

/**
 * Visual severity of a toast notification.
 * Determines the colour scheme and icon rendered by the Toast component.
 */
export type ToastType = 'success' | 'error' | 'warning' | 'info';

/** Data for a single in-flight toast notification. */
export interface Toast {
  /** Unique identifier (UUID) used as the React key and for targeted removal. */
  id: string;
  /** Visual severity — controls colour and icon. */
  type: ToastType;
  /** Human-readable notification text displayed inside the toast. */
  message: string;
  /** How long the toast stays visible before auto-dismissing, in milliseconds. */
  duration: number;
}

/**
 * The value exposed by ToastContext to any consuming component.
 *
 * Consumers can read the active toast list and trigger or dismiss notifications
 * via the typed convenience methods (success, error, warning, info) or the
 * lower-level addToast / removeToast pair for full control.
 */
export interface ToastContextValue {
  /** All currently visible toasts, in the order they were added. */
  toasts: Toast[];
  /**
   * Low-level method to add a toast with explicit control over type and duration.
   * @returns The UUID of the newly created toast.
   */
  addToast: (message: string, options?: { type?: ToastType; duration?: number }) => string;
  /**
   * Remove a specific toast by its id.
   * Called automatically when a toast's timer expires or the user clicks ×.
   */
  removeToast: (id: string) => void;
  /** Show a green success toast. @returns The new toast's id. */
  success: (message: string, duration?: number) => string;
  /** Show a red error toast. @returns The new toast's id. */
  error: (message: string, duration?: number) => string;
  /** Show a yellow warning toast. @returns The new toast's id. */
  warning: (message: string, duration?: number) => string;
  /** Show a blue informational toast. @returns The new toast's id. */
  info: (message: string, duration?: number) => string;
}

/** Auto-dismiss duration used when the caller does not specify one (5 seconds). */
const DEFAULT_DURATION = 5000;

/**
 * The React context object for the toast system.
 * Initialised with null — a null value at runtime means the consuming component
 * is not wrapped in a ToastProvider (caught by the useToast guard).
 */
export const ToastContext = createContext<ToastContextValue | null>(null);

/** Union of all actions that can be dispatched to toastReducer. */
type Action =
  | { type: 'ADD'; payload: Toast }
  | { type: 'REMOVE'; payload: string };

/**
 * Pure reducer for the toast list.
 * ADD appends the new toast; REMOVE filters out the toast matching the given id.
 * Always returns a new array — the original is never mutated.
 */
function toastReducer(state: Toast[], action: Action): Toast[] {
  switch (action.type) {
    case 'ADD':
      return [...state, action.payload];
    case 'REMOVE':
      return state.filter((t) => t.id !== action.payload);
    default:
      return state;
  }
}

/**
 * Provides toast notification state and helpers to the component tree.
 *
 * Wrap your application (or the relevant subtree) with this provider so that
 * any component can call useToast() to trigger and dismiss notifications.
 *
 * All callback functions are wrapped in useCallback so their references stay
 * stable across re-renders — safe to pass as props without causing unnecessary
 * child re-renders.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, dispatch] = useReducer(toastReducer, []);

  /** Creates a toast with a generated UUID and dispatches ADD. */
  const addToast = useCallback((message: string, options?: { type?: ToastType; duration?: number }) => {
    const id = crypto.randomUUID();
    const toast: Toast = {
      id,
      message,
      type: options?.type || 'info',
      duration: options?.duration ?? DEFAULT_DURATION,
    };
    dispatch({ type: 'ADD', payload: toast });
    return id;
  }, []);

  /** Dispatches REMOVE for the toast with the given id. */
  const removeToast = useCallback((id: string) => {
    dispatch({ type: 'REMOVE', payload: id });
  }, []);

  const success = useCallback((message: string, duration?: number) =>
    addToast(message, { type: 'success', duration }), [addToast]);

  const error = useCallback((message: string, duration?: number) =>
    addToast(message, { type: 'error', duration }), [addToast]);

  const warning = useCallback((message: string, duration?: number) =>
    addToast(message, { type: 'warning', duration }), [addToast]);

  const info = useCallback((message: string, duration?: number) =>
    addToast(message, { type: 'info', duration }), [addToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, success, error, warning, info }}>
      {children}
    </ToastContext.Provider>
  );
}
