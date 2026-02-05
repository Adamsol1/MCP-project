import { useEffect } from 'react';
import type { ToastType } from '../../contexts/ToastContext';

interface ToastProps {
  id: string;
  type: ToastType;
  message: string;
  duration: number;
  onClose: (id: string) => void;
}

const typeStyles: Record<ToastType, string> = {
  success: 'bg-green-50 border-green-500 text-green-800',
  error: 'bg-red-50 border-red-500 text-red-800',
  warning: 'bg-yellow-50 border-yellow-500 text-yellow-800',
  info: 'bg-blue-50 border-blue-500 text-blue-800',
};

const icons: Record<ToastType, string> = {
  success: '\u2713',
  error: '\u2715',
  warning: '\u26A0',
  info: '\u2139',
};

export default function Toast({ id, type, message, duration, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose(id);
    }, duration);

    return () => clearTimeout(timer);
  }, [id, duration, onClose]);

  return (
    <div
      role="alert"
      aria-live={type === 'error' ? 'assertive' : 'polite'}
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border-2 shadow-lg min-w-80 max-w-md animate-[slideIn_0.3s_ease-out] ${typeStyles[type]}`}
    >
      <span className="text-lg">{icons[type]}</span>
      <p className="flex-1 text-sm font-medium">{message}</p>
      <button
        type="button"
        onClick={() => onClose(id)}
        className="text-gray-400 hover:text-gray-600 font-bold text-xl leading-none"
        aria-label="Close notification"
      >
        &times;
      </button>
    </div>
  );
}
