import { Loader2, Activity, Check } from 'lucide-react';
import PipelineLoop from './PipelineLoop';

export default function ThinkingScreen({ query, step }) {
  // Determine pipeline stage based on thinking step
  let currentStage = 'criteria';
  if (step?.toLowerCase().includes('filter') || step?.toLowerCase().includes('rubric')) {
    currentStage = 'filtering';
  } else if (step?.toLowerCase().includes('scor') || step?.toLowerCase().includes('rank')) {
    currentStage = 'scoring';
  }

  const STEPS = [
    { index: '01', label: 'Extracting hard criteria & objective filters', active: currentStage === 'criteria' || currentStage === 'filtering' || currentStage === 'scoring' },
    { index: '02', label: 'Synthesizing multi-dimensional fit rubric', active: currentStage === 'filtering' || currentStage === 'scoring' },
    { index: '03', label: 'Scoring candidate pool & extracting profile citations', active: currentStage === 'scoring' },
  ];

  return (
    <div className="min-h-screen bg-[#0C2B33] text-[#F0FDFA] flex flex-col items-center justify-center px-4 relative">
      {/* Background Precision Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(#1E4E5A_1px,transparent_1px)] bg-size-[24px_24px] opacity-25 pointer-events-none" />

      {/* Header Pipeline Container */}
      <div className="w-full max-w-2xl mb-8">
        <PipelineLoop
          currentStage={currentStage}
          totalFiltered={0}
          totalPool={48}
          isRefining={true}
          compact={true}
        />
      </div>

      {/* Main Status Container */}
      <div className="w-full max-w-md bg-[#143D47] border border-[#1E4E5A] rounded-2xl p-6 shadow-xl z-10 animate-fade-in">
        {/* Radar Icon with Electric Lime Beacon */}
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-[#1E4E5A]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#0C2B33] border border-[#A3E635] flex items-center justify-center text-[#A3E635] shadow-[0_0_15px_rgba(163,230,53,0.3)]">
              <Activity className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h2 className="text-xs font-mono font-bold text-[#A3E635] uppercase tracking-wider">
                PIPELINE EXECUTING
              </h2>
              <p className="text-[11px] font-mono text-[#94A3B8]">
                Stage {currentStage === 'criteria' ? '01' : currentStage === 'filtering' ? '02' : '03'} of 05 Active
              </p>
            </div>
          </div>
          <Loader2 className="w-5 h-5 text-[#A3E635] animate-spin" />
        </div>

        {/* Target Query */}
        <div className="bg-[#0C2B33] border border-[#1E4E5A] rounded-lg p-3 mb-5">
          <div className="text-[10px] font-mono text-[#5E7A8A] uppercase tracking-wider mb-1">
            TARGET CRITERIA:
          </div>
          <p className="text-xs text-[#F0FDFA] font-sans italic leading-relaxed">
            "{query}"
          </p>
        </div>

        {/* Execution Steps */}
        <div className="space-y-2.5">
          {STEPS.map((s, idx) => (
            <div
              key={idx}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-all ${
                s.active
                  ? 'bg-[#0E313A] border-[#A3E635]/50 text-[#F0FDFA]'
                  : 'bg-[#0C2B33]/40 border-[#1E4E5A] text-[#5E7A8A]'
              }`}
            >
              <div
                className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-mono font-bold tabular-nums ${
                  s.active
                    ? 'bg-[#A3E635] text-petrol-base'
                    : 'bg-[#143D47] text-[#94A3B8]'
                }`}
              >
                {s.active ? <Check className="w-3 h-3 stroke-3" /> : s.index}
              </div>
              <span className="text-xs font-sans font-medium flex-1">{s.label}</span>
              {s.active && (
                <div className="w-1.5 h-1.5 rounded-full bg-[#A3E635] animate-ping" />
              )}
            </div>
          ))}
        </div>

        <div className="mt-5 text-center text-[11px] font-mono text-[#5E7A8A]">
          Telemetry active · Gemini 2.0 Flash calibration
        </div>
      </div>
    </div>
  );
}
