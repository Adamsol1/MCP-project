import { useContext } from "react";
import { ToastContext } from "../../contexts/Toast/ToastContext";

/**
 * Convenience hook for accessing the toast notification system.
 *
 * Reads from ToastContext, which is populated by ToastProvider in main.tsx.
 * Throws a descriptive error if called outside of a ToastProvider, preventing
 * silent failures caused by a missing provider higher up in the component tree.
 *
 * @returns The full ToastContextValue — the active toast list plus convenience
 *          methods: success(), error(), warning(), info(), addToast(), removeToast().
 */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
