import { useState } from 'react';
import { Search, ArrowRight, Activity } from 'lucide-react';

const EXAMPLE_QUERIES = [
  'RDS developers with 4-7 years of experience who have worked at startups, for a role based in Bangalore',
  'Senior frontend engineers skilled in React and TypeScript, preferably from scaleups',
  'Full-stack engineers with Python and AWS experience, 5+ years, open to remote',
  'DevOps engineers with Kubernetes and Docker experience in Hyderabad',
];

export default function SearchScreen({ onSearch }) {
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  const handleExampleClick = (example) => {
    setQuery(example);
    onSearch(example);
  };

  return (
    <div className="min-h-screen bg-[#0C2B33] text-[#F0FDFA] flex flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Subtle Precision Instrument Ambient Backing */}
      <div className="absolute inset-0 bg-[radial-gradient(#1E4E5A_1px,transparent_1px)] bg-size-[24px_24px] opacity-25 pointer-events-none" />
      <div className="absolute top-1/3 -left-32 w-96 h-96 bg-[#143D47]/40 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/3 -right-32 w-96 h-96 bg-[#0E313A]/60 rounded-full blur-3xl pointer-events-none" />

      {/* Main Container */}
      <div className="w-full max-w-3xl flex flex-col items-center z-10">
        {/* System Status Readout */}
        <div className="mb-6 flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#143D47] border border-[#1E4E5A] text-[11px] font-mono tracking-wider animate-fade-in">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#A3E635] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#A3E635]" />
          </span>
          <span className="text-[#A3E635] font-semibold uppercase">INSTRUMENT ONLINE</span>
          <span className="text-[#5E7A8A]">·</span>
          <span className="text-[#94A3B8] tabular-nums">48 CANDIDATE PROFILES INDEXED</span>
        </div>

        {/* Title & Subtitle */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-[#143D47] border border-[#1E4E5A] flex items-center justify-center text-[#A3E635] shadow-[0_0_15px_rgba(163,230,53,0.2)]">
              <Activity className="w-5 h-5 stroke-[2.2]" />
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-[#F0FDFA]">
              AI RECRUITER
            </h1>
          </div>
          <p className="text-[#94A3B8] text-sm md:text-base max-w-lg mx-auto leading-relaxed">
            Precision sourcing refinement loop. Specify role requirements in natural language to engage the calibration pipeline.
          </p>
        </div>

        {/* Mini Horizontal Pipeline Preview — Stage 01 Active in Electric Lime */}
        <div className="w-full mb-8 bg-[#143D47]/80 border border-[#1E4E5A] rounded-xl p-3 shadow-sm animate-fade-in">
          <div className="text-[10px] font-mono text-[#5E7A8A] uppercase tracking-wider mb-2 text-center">
            RECRUITMENT REFINEMENT PIPELINE
          </div>
          <div className="flex items-center justify-between gap-1 text-[11px] font-mono">
            {/* Stage 1: Active */}
            <div className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg bg-[#0C2B33] border border-[#A3E635] text-[#A3E635] shadow-[0_0_10px_rgba(163,230,53,0.2)] font-semibold">
              <span className="w-4 h-4 rounded bg-[#A3E635] text-petrol-base flex items-center justify-center text-[10px] font-bold">01</span>
              <span>CRITERIA</span>
            </div>
            <div className="w-3 h-px bg-[#1E4E5A]" />

            {/* Stage 2 */}
            <div className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg bg-[#0C2B33]/50 border border-[#1E4E5A] text-[#94A3B8]">
              <span className="text-[10px] opacity-60">02</span>
              <span>FILTER POOL</span>
            </div>
            <div className="w-3 h-px bg-[#1E4E5A]" />

            {/* Stage 3 */}
            <div className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg bg-[#0C2B33]/50 border border-[#1E4E5A] text-[#94A3B8]">
              <span className="text-[10px] opacity-60">03</span>
              <span>FIT SCORING</span>
            </div>
            <div className="w-3 h-px bg-[#1E4E5A]" />

            {/* Stage 4: Loop */}
            <div className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg bg-[#0C2B33]/50 border border-[#1E4E5A] text-[#94A3B8]">
              <span className="text-[10px] opacity-60">04</span>
              <span>CALIBRATE ↺</span>
            </div>
            <div className="w-3 h-px bg-[#1E4E5A]" />

            {/* Stage 5: Lock */}
            <div className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg bg-[#0C2B33]/50 border border-[#1E4E5A] text-[#94A3B8]">
              <span className="text-[10px] opacity-60">05</span>
              <span>LOCK 🔒</span>
            </div>
          </div>
        </div>

        {/* Search Command Input */}
        <form onSubmit={handleSubmit} className="w-full animate-slide-up">
          <div
            className={`
              relative bg-[#143D47] rounded-xl border transition-all duration-200
              ${isFocused
                ? 'border-cyan-accent shadow-[0_0_18px_rgba(103,232,249,0.22)]'
                : 'border-[#1E4E5A] hover:border-[#235B69]'
              }
            `}
          >
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-cyan-accent" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="e.g., RDS developers with 4-7 years experience at startups in Bangalore..."
              className="w-full bg-transparent text-[#F0FDFA] placeholder-[#5E7A8A] pl-12 pr-14 py-4 text-sm md:text-base rounded-xl focus:outline-none font-sans"
              autoFocus
            />
            {/* Primary Action Button: Electric Lime */}
            <button
              type="submit"
              disabled={!query.trim()}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 w-10 h-10 rounded-lg bg-[#A3E635] hover:bg-[#BEF264] active:bg-[#84CC16] disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center transition-all shadow-[0_0_10px_rgba(163,230,53,0.3)] cursor-pointer"
              title="Initialize recruitment loop"
            >
              <ArrowRight className="w-5 h-5 text-petrol-base stroke-[2.5]" />
            </button>
          </div>
        </form>

        {/* Preset Queries */}
        <div className="mt-8 w-full animate-slide-up" style={{ animationDelay: '0.1s' }}>
          <div className="flex items-center justify-between mb-2.5 px-1">
            <span className="text-[#5E7A8A] text-[11px] font-mono uppercase tracking-wider">
              Sample Calibration Presets:
            </span>
            <span className="text-[#5E7A8A] text-[11px] font-mono">CLICK TO LOAD</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {EXAMPLE_QUERIES.map((example, i) => (
              <button
                key={i}
                onClick={() => handleExampleClick(example)}
                className="text-xs px-3 py-2.5 rounded-lg bg-[#143D47] border border-[#1E4E5A] hover:border-cyan-accent/50 hover:bg-[#184551] text-[#94A3B8] hover:text-[#F0FDFA] transition-all cursor-pointer text-left leading-relaxed truncate"
              >
                <span className="text-cyan-accent font-mono mr-1.5">›</span>
                {example}
              </button>
            ))}
          </div>
        </div>

        {/* Footer Telemetry */}
        <div className="mt-12 text-[11px] font-mono text-[#5E7A8A] flex items-center gap-2">
          <span>POWERED BY GOOGLE GEMINI</span>
          <span>·</span>
          <span>FLEXIBLE REFINEMENT PIPELINE</span>
        </div>
      </div>
    </div>
  );
}
