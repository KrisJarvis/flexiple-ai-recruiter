import { Lock, RotateCcw, Search, Copy, Download, Check, MapPin, Building2, Clock, GraduationCap } from 'lucide-react';
import { useState } from 'react';
import PipelineLoop from './PipelineLoop';

export default function FrozenView({
  query,
  filters,
  rubric,
  candidates,
  candidateProfiles,
  totalFiltered,
  totalPool,
  refinementCount,
  onUnfreeze,
  onNewSearch,
}) {
  const [copied, setCopied] = useState(false);
  const profileMap = {};
  candidateProfiles.forEach(p => { profileMap[p.id] = p; });

  const handleCopy = () => {
    const summary = candidates.map((s, i) => {
      const p = profileMap[s.candidate_id];
      return `${i + 1}. ${p?.name} — ${p?.current_title} at ${p?.current_company} (${s.overall_score}/100)\n   ${s.match_reason}`;
    }).join('\n\n');

    const text = `AI Recruiter Search: "${query}"\nRefinements: ${refinementCount}\nMatched: ${totalFiltered}/${totalPool}\n\nShortlist:\n${summary}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportJSON = () => {
    const data = {
      query,
      filters,
      rubric,
      shortlist: candidates.map(s => ({
        ...s,
        profile: profileMap[s.candidate_id],
      })),
      meta: { totalFiltered, totalPool, refinementCount, timestamp: new Date().toISOString() },
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'calibrated-shortlist.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-[#0C2B33] text-[#F0FDFA]">
      {/* Top Instrument Header */}
      <header className="bg-[#143D47] border-b border-[#1E4E5A] px-6 py-3.5 sticky top-0 z-40 shadow-sm">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#0C2B33] border border-[#A3E635] flex items-center justify-center text-[#A3E635] shadow-[0_0_12px_rgba(163,230,53,0.3)]">
              <Lock className="w-4 h-4 stroke-[2.5]" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-[#F0FDFA] flex items-center gap-2">
                SEARCH LOCKED & CALIBRATED
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#A3E635]/20 text-[#A3E635] border border-[#A3E635]/40 font-semibold">
                  STAGE 05 COMPLETE
                </span>
              </h1>
              <p className="text-[#94A3B8] text-xs font-mono truncate max-w-md">"{query}"</p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#0C2B33] border border-[#1E4E5A] hover:border-cyan-accent/40 text-xs font-mono text-[#F0FDFA] transition-all cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-[#4ADE80]" /> : <Copy className="w-3.5 h-3.5 text-cyan-accent" />}
              <span>{copied ? 'COPIED' : 'COPY SUMMARY'}</span>
            </button>

            <button
              onClick={handleExportJSON}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#0C2B33] border border-[#1E4E5A] hover:border-cyan-accent/40 text-xs font-mono text-[#F0FDFA] transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-cyan-accent" />
              <span>EXPORT JSON</span>
            </button>

            <div className="h-4 w-px bg-[#1E4E5A]" />

            <button
              onClick={onUnfreeze}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#143D47] border border-[#A3E635] text-xs font-mono font-bold text-[#A3E635] hover:bg-[#A3E635]/15 transition-all cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>RE-ENGAGE LOOP</span>
            </button>

            <button
              onClick={onNewSearch}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#0E313A] border border-[#1E4E5A] text-xs font-mono text-[#94A3B8] hover:text-[#F0FDFA] transition-all cursor-pointer"
            >
              <Search className="w-3.5 h-3.5" />
              <span>NEW SEARCH</span>
            </button>
          </div>
        </div>
      </header>

      {/* Horizontal Pipeline with Stage 05 (Shortlist Lock) Active */}
      <PipelineLoop
        currentStage="frozen"
        totalFiltered={totalFiltered}
        totalPool={totalPool}
        refinementCount={refinementCount}
      />

      {/* Body Content */}
      <div className="max-w-6xl mx-auto p-6 space-y-6 animate-fade-in">
        {/* Instrument Telemetry Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
          <div className="bg-[#143D47] border border-[#1E4E5A] rounded-xl p-4 text-center">
            <p className="text-3xl font-extrabold text-[#F0FDFA] tabular-nums">{candidates.length}</p>
            <p className="text-[11px] font-mono text-cyan-accent mt-0.5 uppercase tracking-wider">Shortlisted</p>
          </div>
          <div className="bg-[#143D47] border border-[#1E4E5A] rounded-xl p-4 text-center">
            <p className="text-3xl font-extrabold text-[#F0FDFA] tabular-nums">{totalFiltered}</p>
            <p className="text-[11px] font-mono text-[#94A3B8] mt-0.5 uppercase tracking-wider">Passed Filters</p>
          </div>
          <div className="bg-[#143D47] border border-[#1E4E5A] rounded-xl p-4 text-center">
            <p className="text-3xl font-extrabold text-[#A3E635] tabular-nums">{refinementCount}</p>
            <p className="text-[11px] font-mono text-[#A3E635] mt-0.5 uppercase tracking-wider">Loop Iterations</p>
          </div>
          <div className="bg-[#143D47] border border-[#1E4E5A] rounded-xl p-4 text-center">
            <p className="text-3xl font-extrabold text-[#94A3B8] tabular-nums">{totalPool}</p>
            <p className="text-[11px] font-mono text-[#5E7A8A] mt-0.5 uppercase tracking-wider">Total Pool</p>
          </div>
        </div>

        {/* 2-Column Layout */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Left Column: Final Filters + Final Rubric */}
          <div className="col-span-1 space-y-4">
            {/* Frozen Filters */}
            <div className="bg-[#143D47] border border-[#1E4E5A] rounded-xl p-4.5">
              <h3 className="text-xs font-bold text-[#F0FDFA] uppercase tracking-wider mb-3 flex items-center gap-2">
                <Lock className="w-3.5 h-3.5 text-cyan-accent" /> Locked Filters
              </h3>
              <div className="space-y-2.5 text-xs">
                {filters?.required_skills?.length > 0 && (
                  <div>
                    <span className="text-[#94A3B8] text-[11px] font-mono block mb-1">Required Skills:</span>
                    <div className="flex flex-wrap gap-1">
                      {filters.required_skills.map((s, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-[#0C2B33] text-[#A3E635] border border-[#A3E635]/30 text-xs font-mono">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
                {(filters?.min_years_experience != null || filters?.max_years_experience != null) && (
                  <div className="bg-[#0C2B33] border border-[#1E4E5A] p-2 rounded text-xs text-[#F0FDFA] font-mono tabular-nums">
                    Experience: {filters.min_years_experience ?? 0}–{filters.max_years_experience ?? '∞'} years
                  </div>
                )}
                {filters?.locations?.length > 0 && (
                  <div className="text-xs text-[#94A3B8]">
                    <span className="font-mono text-[#5E7A8A]">Locations:</span> <span className="text-[#F0FDFA]">{filters.locations.join(', ')}</span>
                  </div>
                )}
                {filters?.company_types?.length > 0 && (
                  <div className="text-xs text-[#94A3B8]">
                    <span className="font-mono text-[#5E7A8A]">Companies:</span> <span className="text-[#FACC15]">{filters.company_types.join(', ')}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Frozen Rubric */}
            <div className="bg-[#143D47] border border-[#1E4E5A] rounded-xl p-4.5">
              <h3 className="text-xs font-bold text-[#F0FDFA] uppercase tracking-wider mb-3 flex items-center gap-2">
                <Lock className="w-3.5 h-3.5 text-cyan-accent" /> Calibrated Rubric
              </h3>
              <p className="text-xs text-[#94A3B8] leading-relaxed italic mb-3 bg-[#0C2B33] p-2 rounded border border-[#1E4E5A]">
                {rubric?.role_summary}
              </p>
              <div className="space-y-2">
                {rubric?.criteria?.map((c, i) => (
                  <div key={i} className="text-xs bg-[#0C2B33] p-2 rounded border border-[#1E4E5A] flex items-center justify-between">
                    <span className="text-[#F0FDFA] font-medium">{c.name}</span>
                    <span className="text-[#A3E635] font-mono tabular-nums text-[11px]">WEIGHT {c.weight}/5</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Final Calibrated Shortlist */}
          <div className="col-span-2 space-y-3">
            <div className="flex items-center justify-between px-1 mb-2">
              <h3 className="text-xs font-bold text-[#94A3B8] uppercase tracking-widest">
                Final Calibrated Shortlist
              </h3>
              <span className="text-[11px] font-mono text-[#A3E635]">
                {candidates.length} CANDIDATES READY FOR OUTREACH
              </span>
            </div>

            <div className="space-y-3 stagger-children">
              {candidates.map((score, i) => {
                const p = profileMap[score.candidate_id];
                if (!p) return null;

                const scoreBg =
                  score.match_tier === 'strong_match' ? 'bg-[#4ADE80] text-[#082026]' :
                  score.match_tier === 'moderate_match' ? 'bg-[#FACC15] text-[#082026]' :
                  'bg-[#FB7185] text-[#082026]';

                return (
                  <div key={score.candidate_id} className="bg-[#143D47] border border-[#1E4E5A] rounded-xl p-4 flex gap-4">
                    {/* Rank & Score Gauge */}
                    <div className="flex flex-col items-center gap-1 shrink-0">
                      <span className="text-[10px] font-mono text-[#94A3B8] font-bold">#{i + 1}</span>
                      <div className={`w-11 h-11 rounded-lg ${scoreBg} flex flex-col items-center justify-center font-bold tabular-nums`}>
                        <span className="text-sm leading-none font-extrabold">{score.overall_score}</span>
                        <span className="text-[7px] font-mono mt-0.5">FIT</span>
                      </div>
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <h4 className="text-[#F0FDFA] font-bold text-sm">{p.name}</h4>
                      <p className="text-[#94A3B8] text-xs font-medium">{p.current_title}</p>
                      <div className="flex flex-wrap gap-3 mt-1.5 text-xs text-[#94A3B8]">
                        <span className="flex items-center gap-1"><Building2 className="w-3 h-3 text-cyan-accent" />{p.current_company}</span>
                        <span className="flex items-center gap-1"><MapPin className="w-3 h-3 text-cyan-accent" />{p.location}</span>
                        <span className="flex items-center gap-1 tabular-nums"><Clock className="w-3 h-3 text-cyan-accent" />{p.years_experience}yrs</span>
                        <span className="flex items-center gap-1"><GraduationCap className="w-3 h-3 text-cyan-accent" />{p.education}</span>
                      </div>
                      <p className="text-xs text-[#F0FDFA] mt-2 bg-[#0C2B33] p-2 rounded border border-[#1E4E5A] leading-relaxed">
                        {score.match_reason}
                      </p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {p.skills.map((s, j) => (
                          <span key={j} className="px-1.5 py-0.5 rounded bg-[#0C2B33] border border-[#1E4E5A] text-[#94A3B8] text-[11px] font-mono">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
