import { AlertCircle, X } from 'lucide-react';

export default function ErrorBanner({ message, onDismiss }) {
  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 animate-slide-up max-w-lg w-full px-4">
      <div className="flex items-center gap-3 bg-[#0C2B33] border border-[#FB7185] text-[#FB7185] px-4 py-3 rounded-xl shadow-[0_0_20px_rgba(251,113,133,0.25)] backdrop-blur-md">
        <AlertCircle className="w-4 h-4 shrink-0 text-[#FB7185]" />
        <span className="text-xs font-mono font-medium flex-1 text-[#F0FDFA] leading-relaxed">
          {message}
        </span>
        <button
          onClick={onDismiss}
          className="hover:bg-[#FB7185]/20 text-[#FB7185] rounded-lg p-1 transition-colors shrink-0 cursor-pointer"
          title="Dismiss notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
