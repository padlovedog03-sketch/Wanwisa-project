import React from 'react';

interface ToastProps {
  message: string;
  type: 'success' | 'error';
  visible: boolean;
}

export const Toast: React.FC<ToastProps> = ({ message, type, visible }) => {
  if (!visible) return null;

  return (
    <div
      className={`fixed right-4 bottom-4 z-50 max-w-sm rounded-xl px-4 py-3 text-sm font-bold shadow-xl transition-all duration-300 ${
        type === 'error' ? 'bg-red-700 text-white' : 'bg-emerald-600 text-white'
      }`}
      role="alert"
    >
      {message}
    </div>
  );
};
