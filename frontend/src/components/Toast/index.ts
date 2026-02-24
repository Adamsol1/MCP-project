/**
 * Public barrel exports for the Toast component system.
 *
 * Toast          — renders a single notification bubble with auto-dismiss.
 * ToastContainer — renders all active toasts in a fixed overlay at a chosen position.
 *
 * Most consumers only need ToastContainer (placed once in the layout) and
 * the useToast() hook (to trigger notifications from anywhere in the tree).
 */
export { default as Toast } from './Toast';
export { default as ToastContainer } from './ToastContainer';
