import { createContext, useReducer, useCallback, type ReactNode } from 'react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration: number;
}

export interface ToastContextValue {
  toasts: Toast[];
  addToast: (message: string, options?: { type?: ToastType; duration?: number }) => string;
  removeToast: (id: string) => void;
  success: (message: string, duration?: number) => string;
  error: (message: string, duration?: number) => string;
  warning: (message: string, duration?: number) => string;
  info: (message: string, duration?: number) => string;
}

const DEFAULT_DURATION = 5000;

export const ToastContext = createContext<ToastContextValue | null>(null);

type Action =
  | { type: 'ADD'; payload: Toast }
  | { type: 'REMOVE'; payload: string };

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

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, dispatch] = useReducer(toastReducer, []);

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
