import { Check, RotateCw, Lock, Sparkles, Filter, Target, ArrowRight } from 'lucide-react';

/**
 * PipelineLoop — Precision Instrument Horizontal Pipeline
 * 
 * Visualizes the sourcing refinement loop as an instrument pipeline:
 * [ 01 CRITERIA ] → [ 02 FILTER POOL ] → [ 03 FIT SCORING ] → ↺ [ 04 CALIBRATE & REFINE ] → 🔒 [ 05 SHORTLIST LOCK ]
 * 
 * Active stages are highlighted in Electric Lime (#A3E635).
 */
export default function PipelineLoop({
  currentStage = 'refining', // 'criteria' | 'filtering' | 'scoring' | 'refining' | 'frozen'
  totalFiltered = 0,
  totalPool = 0,
  refinementCount = 0,
  thumbs = {},
  isRefining = false,
  compact = false,
}) {
  const thumbUpCount = Object.values(thumbs).filter(v => v === true).length;
  const thumbDownCount = Object.values(thumbs).filter(v => v === false).length;

  const stageOrder = ['criteria', 'filtering', 'scoring', 'refining', 'frozen'];
  const currentIndex = stageOrder.indexOf(currentStage);

  const STAGES = [
    {
      id: 'criteria',
      index: '01',
      title: 'CRITERIA',
      subtext: 'Role Intent',
      icon: Sparkles,
      metric: null,
    },
    {
      id: 'filtering',
      index: '02',
      title: 'FILTER POOL',
      subtext: 'Hard Criteria',
      icon: Filter,
      metric: totalPool > 0 ? `${totalFiltered}/${totalPool}` : null,
    },
    {
      id: 'scoring',
      index: '03',
      title: 'FIT SCORING',
      subtext: 'Rubric Evaluator',
      icon: Target,
      metric: totalFiltered > 0 ? `${totalFiltered} Ranked` : null,
    },
    {
      id: 'refining',
      index: '04',
      title: 'CALIBRATE & REFINE',
      subtext: isRefining ? 'Calibrating loop...' : `Iteration #${refinementCount}`,
      icon: RotateCw,
      metric: refinementCount > 0 ? `Loop #${refinementCount}` : (thumbUpCount + thumbDownCount > 0 ? `${thumbUpCount}👍 ${thumbDownCount}👎` : 'Live Loop'),
      isLoop: true,
    },
    {
      id: 'frozen',
      index: '05',
      title: 'SHORTLIST LOCK',
      subtext: currentStage === 'frozen' ? 'Calibrated State' : 'Pending Lock',
      icon: Lock,
      metric: currentStage === 'frozen' ? 'Locked' : null,
    },
  ];

  return (
    <div className={`w-full bg-[#0E313A]/90 border-b border-[#1E4E5A] px-4 md:px-6 py-2.5 transition-all ${compact ? 'py-1.5' : ''}`}>
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-2 overflow-x-auto no-scrollbar">
        {STAGES.map((stage, idx) => {
          const isCurrent = stage.id === currentStage;
          const isPassed = idx < currentIndex;

          return (
            <div key={stage.id} className="flex items-center flex-1 min-w-fit first:pl-0 last:pr-0">
              {/* Stage Node */}
              <div
                className={`
                  flex items-center gap-2.5 px-3 py-1.5 rounded-lg transition-all duration-200
                  ${isCurrent
                    ? 'bg-[#143D47] border border-[#A3E635] shadow-[0_0_12px_rgba(163,230,53,0.22)]'
                    : isPassed
                    ? 'bg-surface-850/80 border border-[#1E4E5A] hover:border-cyan-accent/40'
                    : 'bg-transparent border border-transparent opacity-45'
                  }
                `}
              >
                {/* Index / Status Indicator */}
                <div
                  className={`
                    w-6 h-6 rounded flex items-center justify-center text-xs font-bold shrink-0 tabular-nums transition-colors
                    ${isCurrent
                      ? 'bg-[#A3E635] text-petrol-base shadow-sm'
                      : isPassed
                      ? 'bg-cyan-accent/15 text-cyan-accent border border-cyan-accent/30'
                      : 'bg-[#143D47] text-[#94A3B8]'
                    }
                  `}
                >
                  {isPassed ? (
                    <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                  ) : stage.isLoop && isCurrent ? (
                    <RotateCw className={`w-3.5 h-3.5 ${isRefining ? 'animate-spin' : ''}`} />
                  ) : (
                    <span>{stage.index}</span>
                  )}
                </div>

                {/* Stage Title & Telemetry */}
                <div className="flex flex-col text-left">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`text-xs font-semibold tracking-wider uppercase ${
                        isCurrent
                          ? 'text-[#A3E635]'
                          : isPassed
                          ? 'text-[#F0FDFA]'
                          : 'text-[#94A3B8]'
                      }`}
                    >
                      {stage.title}
                    </span>

                    {/* Stage Metric Badge */}
                    {stage.metric && (
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-mono tabular-nums ${
                          isCurrent
                            ? 'bg-[#A3E635]/20 text-[#A3E635] font-semibold border border-[#A3E635]/40'
                            : 'bg-[#143D47] text-cyan-accent border border-[#1E4E5A]'
                        }`}
                      >
                        {stage.metric}
                      </span>
                    )}
                  </div>

                  {/* Secondary Telemetry Text */}
                  {!compact && (
                    <span
                      className={`text-[11px] truncate max-w-32.5 ${
                        isCurrent
                          ? 'text-[#F0FDFA] font-medium'
                          : 'text-[#5E7A8A]'
                      }`}
                    >
                      {stage.subtext}
                    </span>
                  )}
                </div>

                {/* Active Stage Pulsing Beacon */}
                {isCurrent && (
                  <div className="relative flex items-center justify-center ml-1">
                    <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-[#A3E635] opacity-75" />
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#A3E635]" />
                  </div>
                )}
              </div>

              {/* Connector Rail Arrow */}
              {idx < STAGES.length - 1 && (
                <div className="flex items-center px-1.5 text-[#1E4E5A] shrink-0">
                  <div className={`h-px w-3 md:w-5 transition-colors ${idx < currentIndex ? 'bg-cyan-accent/40' : 'bg-[#1E4E5A]'}`} />
                  <ArrowRight className={`w-3 h-3 -ml-1 ${idx < currentIndex ? 'text-cyan-accent' : 'text-[#1E4E5A]'}`} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
