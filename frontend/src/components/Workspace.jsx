import { Snowflake, RotateCcw, Users, Filter as FilterIcon, Activity } from 'lucide-react';
import FilterPanel from './FilterPanel';
import RubricPanel from './RubricPanel';
import CandidateCard from './CandidateCard';
import ChatBar from './ChatBar';
import PipelineLoop from './PipelineLoop';

export default function Workspace({
  query,
  filters,
  rubric,
  candidates,
  candidateProfiles,
  totalFiltered,
  totalPool,
  isNearMiss,
  thumbs,
  chatHistory,
  refinementCount,
  isRefining,
  onThumb,
  onRefine,
  onFreeze,
  onNewSearch,
}) {
  const profileMap = {};
  candidateProfiles.forEach(p => { profileMap[p.id] = p; });

  return (
    <div className="min-h-screen flex flex-col bg-[#0C2B33] text-[#F0FDFA]">
      {/* Top Instrument Header */}
      <header className="bg-[#143D47] border-b border-[#1E4E5A] px-6 py-3 flex items-center justify-between sticky top-0 z-40 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#0C2B33] border border-[#1E4E5A] flex items-center justify-center text-[#A3E635]">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wider text-[#F0FDFA] flex items-center gap-2">
                AI RECRUITER
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#0C2B33] text-cyan-accent font-mono tracking-normal border border-[#1E4E5A]">
                  PRECISION INSTRUMENT
                </span>
              </h1>
            </div>
          </div>
          <div className="h-4 w-px bg-[#1E4E5A]" />
          <p className="text-[#94A3B8] text-xs font-mono truncate max-w-md" title={query}>
            TARGET: <span className="text-[#F0FDFA] font-sans">"{query}"</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Telemetry Metrics */}
          <div className="flex items-center gap-2 text-xs font-mono bg-[#0C2B33] px-3 py-1.5 rounded-lg border border-[#1E4E5A]">
            <Users className="w-3.5 h-3.5 text-cyan-accent" />
            <span className="text-[#F0FDFA] tabular-nums font-semibold">{totalFiltered}</span>
            <span className="text-[#5E7A8A]">/</span>
            <span className="text-[#94A3B8] tabular-nums">{totalPool} POOL</span>
            {refinementCount > 0 && (
              <>
                <span className="text-[#1E4E5A]">|</span>
                <span className="text-[#A3E635] tabular-nums font-semibold">
                  LOOP #{refinementCount}
                </span>
              </>
            )}
          </div>

          <div className="h-4 w-px bg-[#1E4E5A]" />

          {/* Reset / New Search */}
          <button
            onClick={onNewSearch}
            className="flex items-center gap-1.5 text-xs text-[#94A3B8] hover:text-[#F0FDFA] bg-[#0E313A] hover:bg-[#184551] border border-[#1E4E5A] px-3 py-2 rounded-lg transition-all cursor-pointer font-medium"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New Search
          </button>

          {/* Primary Action: Freeze Shortlist in Electric Lime */}
          <button
            onClick={onFreeze}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#A3E635] text-petrol-base text-xs font-bold tracking-wide uppercase hover:bg-[#BEF264] active:bg-[#84CC16] transition-all duration-150 shadow-[0_0_14px_rgba(163,230,53,0.3)] hover:shadow-[0_0_20px_rgba(163,230,53,0.5)] cursor-pointer"
          >
            <Snowflake className="w-4 h-4 stroke-[2.5]" />
            Freeze Search
          </button>
        </div>
      </header>

      {/* Horizontal Pipeline Loop Visualization */}
      <PipelineLoop
        currentStage="refining"
        totalFiltered={totalFiltered}
        totalPool={totalPool}
        refinementCount={refinementCount}
        thumbs={thumbs}
        isRefining={isRefining}
      />

      {/* Main Content Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar — Filters & Rubric */}
        <aside className="w-80 md:w-88 border-r border-[#1E4E5A] bg-[#0C2B33] overflow-y-auto h-[calc(100vh-109px)] sticky top-27.25 shrink-0">
          <div className="p-4 space-y-4">
            <FilterPanel filters={filters} />
            <RubricPanel rubric={rubric} />
          </div>
        </aside>

        {/* Center — Candidates + Refinement Command Console */}
        <main className="flex-1 flex flex-col h-[calc(100vh-109px)] bg-[#0C2B33]">
          {/* Candidate Stream */}
          <div className="flex-1 overflow-y-auto p-5 md:p-6 space-y-4">
            {/* Real-time calibration status indicator */}
            {isRefining && (
              <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-[#143D47] border border-[#A3E635] shadow-[0_0_15px_rgba(163,230,53,0.18)] animate-fade-in">
                <div className="flex items-center gap-3">
                  <div className="relative flex items-center justify-center">
                    <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-[#A3E635] opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[#A3E635]" />
                  </div>
                  <span className="text-xs font-mono font-semibold text-[#A3E635] uppercase tracking-wider">
                    CALIBRATING PIPELINE LOOP · RE-EVALUATING FIT RUBRIC...
                  </span>
                </div>
                <span className="text-[11px] font-mono text-[#94A3B8]">
                  Processing feedback parameters
                </span>
              </div>
            )}

            {candidates.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-96 text-center border border-dashed border-[#1E4E5A] rounded-2xl p-8 bg-[#143D47]/30">
                <FilterIcon className="w-12 h-12 text-[#5E7A8A] mb-4 stroke-1" />
                <h3 className="text-base font-semibold text-[#F0FDFA] mb-1">Zero Candidates Match Current Parameters</h3>
                <p className="text-[#94A3B8] text-xs max-w-sm mb-4 leading-relaxed">
                  Relax hard constraints in the left panel or calibrate with conversational feedback below.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between px-1">
                  <div className="flex items-center gap-2">
                    <h2 className="text-xs font-bold text-[#94A3B8] tracking-widest uppercase">
                      Ranked Shortlist
                    </h2>
                    <span className="text-xs font-mono tabular-nums px-2 py-0.5 rounded bg-[#143D47] border border-[#1E4E5A] text-cyan-accent">
                      {candidates.length} CANDIDATES
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-[#5E7A8A]">
                    SORTED BY FIT COEFFICIENT
                  </div>
                </div>

                {(isNearMiss || (totalFiltered === 0 && candidates.length > 0)) && (
                  <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-[#FACC15]/10 border border-[#FACC15]/30 text-[#FACC15] text-xs font-mono">
                    <span className="w-2 h-2 rounded-full bg-[#FACC15] shrink-0 animate-pulse" />
                    <span>STRICT FILTER MATCHES: 0. Displaying top near-miss profiles (1 relaxed parameter).</span>
                  </div>
                )}

                <div className="space-y-3 stagger-children">
                  {candidates.map((score, i) => (
                    <CandidateCard
                      key={score.candidate_id}
                      score={score}
                      profile={profileMap[score.candidate_id]}
                      rank={i + 1}
                      thumb={thumbs[score.candidate_id]}
                      onThumb={onThumb}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Refinement Chat & Command Console */}
          <ChatBar
            chatHistory={chatHistory}
            isRefining={isRefining}
            onRefine={onRefine}
            thumbs={thumbs}
          />
        </main>
      </div>
    </div>
  );
}
