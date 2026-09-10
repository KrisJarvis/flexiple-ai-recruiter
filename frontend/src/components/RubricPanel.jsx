import { Target, AlertTriangle, Star, Sliders } from 'lucide-react';

export default function RubricPanel({ rubric }) {
  if (!rubric) return null;

  return (
    <div className="bg-[#143D47] border border-[#1E4E5A] rounded-xl p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 mb-3.5 border-b border-[#1E4E5A]">
        <div className="flex items-center gap-2">
          <Target className="w-3.5 h-3.5 text-cyan-accent" />
          <h3 className="text-xs font-bold text-[#F0FDFA] uppercase tracking-wider">
            Fit Rubric
          </h3>
        </div>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#0C2B33] text-[#A3E635] border border-[#A3E635]/30">
          WEIGHTED
        </span>
      </div>

      {/* Role Summary */}
      <div className="bg-[#0C2B33] border-l-2 border-cyan-accent rounded-r-lg p-2.5 mb-3.5">
        <p className="text-[#F0FDFA] text-xs leading-relaxed font-medium">
          {rubric.role_summary}
        </p>
      </div>

      {/* Criteria */}
      <div className="space-y-2 mb-3.5">
        <label className="text-[#94A3B8] text-[11px] font-medium flex items-center gap-1.5 mb-1">
          <Sliders className="w-3 h-3 text-cyan-accent" /> Evaluation Dimensions
        </label>
        {rubric.criteria?.map((criterion, i) => (
          <div key={i} className="bg-[#0C2B33] border border-[#1E4E5A] rounded-lg p-2.5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[#F0FDFA] text-xs font-medium">{criterion.name}</span>
              <div className="flex items-center gap-1">
                <span className="text-[10px] font-mono tabular-nums text-[#94A3B8] mr-1">
                  W{criterion.weight}
                </span>
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map(w => (
                    <div
                      key={w}
                      className={`w-1.5 h-2 rounded-xs transition-colors ${
                        w <= criterion.weight
                          ? 'bg-[#A3E635] shadow-[0_0_6px_rgba(163,230,53,0.4)]'
                          : 'bg-[#143D47] border border-[#1E4E5A]'
                      }`}
                    />
                  ))}
                </div>
              </div>
            </div>
            <p className="text-[#94A3B8] text-[11px] leading-relaxed">{criterion.description}</p>
          </div>
        ))}
      </div>

      {/* Dealbreakers */}
      {rubric.dealbreakers?.length > 0 && (
        <div className="mb-3">
          <label className="text-[#FB7185] text-[11px] font-semibold flex items-center gap-1.5 mb-1.5 uppercase tracking-wider">
            <AlertTriangle className="w-3 h-3 text-[#FB7185]" /> Dealbreakers
          </label>
          <ul className="space-y-1">
            {rubric.dealbreakers.map((db, i) => (
              <li key={i} className="text-xs text-[#FB7185]/90 bg-[#0C2B33] border border-[#FB7185]/20 rounded-md px-2.5 py-1.5 flex items-start gap-2">
                <span className="mt-1 w-1.5 h-1.5 rounded-full bg-[#FB7185] shrink-0" />
                <span>{db}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Positive Signals */}
      {rubric.positive_signals?.length > 0 && (
        <div>
          <label className="text-[#4ADE80] text-[11px] font-semibold flex items-center gap-1.5 mb-1.5 uppercase tracking-wider">
            <Star className="w-3 h-3 text-[#4ADE80]" /> High-Fit Signals
          </label>
          <ul className="space-y-1">
            {rubric.positive_signals.map((ps, i) => (
              <li key={i} className="text-xs text-[#4ADE80]/90 bg-[#0C2B33] border border-[#4ADE80]/20 rounded-md px-2.5 py-1.5 flex items-start gap-2">
                <span className="mt-1 w-1.5 h-1.5 rounded-full bg-[#4ADE80] shrink-0" />
                <span>{ps}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
