import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, MessageSquare, Terminal, User, AlertCircle, ArrowDown } from 'lucide-react';

export default function ChatBar({ chatHistory, isRefining, onRefine, thumbs }) {
  const [message, setMessage] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const historyRef = useRef(null);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const thumbUpCount = Object.values(thumbs).filter(v => v === true).length;
  const thumbDownCount = Object.values(thumbs).filter(v => v === false).length;
  const hasThumbs = thumbUpCount > 0 || thumbDownCount > 0;

  const handleSubmit = (e) => {
    e.preventDefault();
    if ((message.trim() || hasThumbs) && !isRefining) {
      onRefine(message.trim());
      setMessage('');
    }
  };

  return (
    <div className="border-t border-[#1E4E5A] bg-[#0E313A] shadow-lg">
      {/* Refinement History Drawer Toggle */}
      {chatHistory.length > 0 && (
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="w-full flex items-center justify-center gap-2 py-1.5 text-[11px] font-mono text-[#94A3B8] hover:text-cyan-accent bg-[#0C2B33] border-b border-[#1E4E5A] transition-colors cursor-pointer"
        >
          <MessageSquare className="w-3 h-3 text-cyan-accent" />
          <span>REFINEMENT LOG: {chatHistory.length} ENTRIES</span>
          <ArrowDown className={`w-3 h-3 transition-transform duration-200 ${showHistory ? 'rotate-180 text-[#A3E635]' : ''}`} />
        </button>
      )}

      {/* History Messages Drawer */}
      {showHistory && chatHistory.length > 0 && (
        <div ref={historyRef} className="max-h-64 overflow-y-auto px-5 py-3 space-y-3 bg-petrol-dark border-b border-[#1E4E5A]">
          {chatHistory.map((msg, i) => (
            <div key={i} className="flex gap-2.5 animate-fade-in text-xs">
              <div className={`w-6 h-6 rounded flex items-center justify-center shrink-0 ${
                msg.role === 'user'
                  ? 'bg-[#143D47] text-cyan-accent border border-cyan-accent/30'
                  : msg.role === 'error'
                  ? 'bg-[#FB7185]/20 text-[#FB7185] border border-[#FB7185]/40'
                  : 'bg-[#0C2B33] text-[#A3E635] border border-[#A3E635]/30'
              }`}>
                {msg.role === 'user' ? <User className="w-3.5 h-3.5" /> :
                 msg.role === 'error' ? <AlertCircle className="w-3.5 h-3.5" /> :
                 <Terminal className="w-3.5 h-3.5" />}
              </div>
              <div className="flex-1 min-w-0 bg-[#0E313A] border border-[#1E4E5A] p-2.5 rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider font-bold text-[#94A3B8]">
                    {msg.role === 'user' ? 'Recruiter Directive' : msg.role === 'error' ? 'Execution Fault' : 'Pipeline Calibration'}
                  </span>
                </div>
                <p className={`leading-relaxed ${msg.role === 'error' ? 'text-[#FB7185]' : 'text-[#F0FDFA]'}`}>
                  {msg.content}
                </p>
                {msg.changes && (
                  <div className="mt-2 pt-2 border-t border-[#1E4E5A]">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-[#A3E635] block mb-1">
                      Parameters Adjusted:
                    </span>
                    <ul className="space-y-1">
                      {msg.changes.map((change, j) => (
                        <li key={j} className="text-[11px] text-[#A3E635]/90 flex items-start gap-1.5 font-mono">
                          <span className="mt-1 w-1 h-1 rounded-full bg-[#A3E635] shrink-0" />
                          <span>{change}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Main Refinement Input Bar */}
      <form onSubmit={handleSubmit} className="px-5 py-3 flex items-center gap-3">
        {/* Real-time Thumb Telemetry Chip */}
        {hasThumbs && (
          <div className="flex items-center gap-1.5 bg-[#0C2B33] border border-[#1E4E5A] px-2.5 py-1.5 rounded-lg shrink-0 text-xs font-mono tabular-nums">
            {thumbUpCount > 0 && (
              <span className="text-[#4ADE80] font-semibold flex items-center gap-1">
                {thumbUpCount} 👍
              </span>
            )}
            {thumbUpCount > 0 && thumbDownCount > 0 && <span className="text-[#1E4E5A]">·</span>}
            {thumbDownCount > 0 && (
              <span className="text-[#FB7185] font-semibold flex items-center gap-1">
                {thumbDownCount} 👎
              </span>
            )}
            <span className="text-[10px] text-cyan-accent ml-1 uppercase">SIGNAL</span>
          </div>
        )}

        {/* Text Directive Input */}
        <div className="flex-1 relative">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={isRefining}
            placeholder={
              isRefining
                ? 'Calibrating loop and re-evaluating fit rubric...'
                : hasThumbs
                ? 'Optional feedback or click CALIBRATE to refine using thumb reactions...'
                : 'Enter directive: "1 is too junior, 2 and 4 are right" or "focus on startup experience"...'
            }
            className="w-full bg-[#0C2B33] border border-[#1E4E5A] text-[#F0FDFA] placeholder-[#5E7A8A] px-4 py-2.5 rounded-lg text-xs md:text-sm font-sans focus:outline-none focus:border-cyan-accent focus:ring-1 focus:ring-cyan-accent/40 disabled:opacity-50 transition-all"
          />
        </div>

        {/* Primary Action Button: Electric Lime */}
        <button
          type="submit"
          disabled={(!message.trim() && !hasThumbs) || isRefining}
          className="h-10 px-4 rounded-lg bg-[#A3E635] hover:bg-[#BEF264] active:bg-[#84CC16] disabled:opacity-30 disabled:cursor-not-allowed text-petrol-base text-xs font-bold font-mono tracking-wider uppercase flex items-center justify-center gap-1.5 transition-all shadow-[0_0_12px_rgba(163,230,53,0.3)] hover:shadow-[0_0_18px_rgba(163,230,53,0.45)] shrink-0 cursor-pointer"
        >
          {isRefining ? (
            <Loader2 className="w-4 h-4 text-petrol-base animate-spin" />
          ) : (
            <>
              <span>CALIBRATE</span>
              <Send className="w-3.5 h-3.5 stroke-[2.5]" />
            </>
          )}
        </button>
      </form>
    </div>
  );
}
