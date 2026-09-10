import { ThumbsUp, ThumbsDown, MapPin, Building2, GraduationCap, Briefcase, Clock, ChevronRight } from 'lucide-react';

function ScoreBadge({ score, tier }) {
  // Precision instrument gauge color coding
  const tierStyles = {
    strong_match: 'bg-[#4ADE80] text-[#082026] shadow-[0_0_12px_rgba(74,222,128,0.25)] border-[#4ADE80]',
    moderate_match: 'bg-[#FACC15] text-[#082026] shadow-[0_0_12px_rgba(250,204,21,0.2)] border-[#FACC15]',
    weak_match: 'bg-[#FB7185] text-[#082026] shadow-[0_0_12px_rgba(251,113,133,0.2)] border-[#FB7185]',
  };

  const currentStyle = tierStyles[tier] || tierStyles.weak_match;

  return (
    <div className={`w-12 h-12 rounded-xl flex flex-col items-center justify-center border font-bold tabular-nums transition-transform ${currentStyle}`}>
      <span className="text-base leading-none font-extrabold">{score}</span>
      <span className="text-[8px] tracking-wider uppercase font-mono mt-0.5 opacity-80">FIT</span>
    </div>
  );
}

export default function CandidateCard({ score, profile, rank, thumb, onThumb }) {
  if (!profile) return null;

  return (
    <div className="bg-[#143D47] border border-[#1E4E5A] hover:border-cyan-accent/40 hover:bg-[#16434E] rounded-xl p-5 transition-all duration-200 shadow-sm group">
      <div className="flex gap-4.5">
        {/* Score Gauge & Rank */}
        <div className="flex flex-col items-center gap-1.5 shrink-0">
          <span className="text-[11px] font-mono tabular-nums text-[#94A3B8] font-bold">
            #{String(rank).padStart(2, '0')}
          </span>
          <ScoreBadge score={score.overall_score} tier={score.match_tier} />
        </div>

        {/* Main Details */}
        <div className="flex-1 min-w-0">
          {/* Header Bar */}
          <div className="flex items-start justify-between gap-3 mb-2.5">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-[#F0FDFA] font-bold text-base tracking-tight">
                  {profile.name}
                </h3>
                {score.overall_score >= 85 && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#A3E635]/15 text-[#A3E635] border border-[#A3E635]/30">
                    TOP MATCH
                  </span>
                )}
              </div>
              <p className="text-[#94A3B8] text-xs font-medium mt-0.5">
                {profile.current_title}
              </p>
            </div>

            {/* Thumbs Feedback Controls */}
            <div className="flex items-center gap-1.5 bg-[#0C2B33] p-1 rounded-lg border border-[#1E4E5A]">
              <button
                onClick={() => onThumb(score.candidate_id, true)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all duration-150 cursor-pointer ${
                  thumb === true
                    ? 'bg-[#4ADE80] text-petrol-base font-bold shadow-[0_0_8px_rgba(74,222,128,0.4)]'
                    : 'text-[#94A3B8] hover:text-[#4ADE80] hover:bg-[#143D47]'
                }`}
                title="Calibrate: Good candidate profile"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
                <span className="text-[10px] font-mono">ACCEPT</span>
              </button>
              <button
                onClick={() => onThumb(score.candidate_id, false)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all duration-150 cursor-pointer ${
                  thumb === false
                    ? 'bg-[#FB7185] text-petrol-base font-bold shadow-[0_0_8px_rgba(251,113,133,0.4)]'
                    : 'text-[#94A3B8] hover:text-[#FB7185] hover:bg-[#143D47]'
                }`}
                title="Calibrate: Reject candidate profile"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
                <span className="text-[10px] font-mono">REJECT</span>
              </button>
            </div>
          </div>

          {/* Quick Telemetry Facts */}
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 mb-3 text-xs text-[#94A3B8]">
            <span className="flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-cyan-accent" />
              <span className="text-[#F0FDFA] font-medium">{profile.current_company}</span>
              <span className="text-[#5E7A8A]">({profile.current_company_type})</span>
            </span>
            <span className="flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-cyan-accent" /> {profile.location}
            </span>
            <span className="flex items-center gap-1.5 tabular-nums">
              <Clock className="w-3.5 h-3.5 text-cyan-accent" /> {profile.years_experience} yrs
            </span>
            <span className="flex items-center gap-1.5">
              <GraduationCap className="w-3.5 h-3.5 text-cyan-accent" /> {profile.education}
            </span>
          </div>

          {/* Skills Chips */}
          <div className="flex flex-wrap gap-1.5 mb-3">
            {profile.skills.map((skill, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded bg-[#0C2B33] text-[#F0FDFA] border border-[#1E4E5A] text-xs font-mono"
              >
                {skill}
              </span>
            ))}
          </div>

          {/* Match Reason */}
          <p className="text-xs md:text-sm text-[#F0FDFA] mb-3 leading-relaxed bg-[#0C2B33]/50 border-l-2 border-[#A3E635] p-2.5 rounded-r-lg">
            {score.match_reason}
          </p>

          {/* Evidence Citations */}
          {score.evidence?.length > 0 && (
            <div className="border-t border-[#1E4E5A] pt-2.5 mt-2">
              <h4 className="text-[10px] font-mono font-bold text-cyan-accent mb-2 uppercase tracking-wider flex items-center gap-1.5">
                <ChevronRight className="w-3 h-3 text-[#A3E635]" /> Verified Profile Evidence
              </h4>
              <div className="space-y-1.5">
                {score.evidence.map((ev, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs bg-[#0C2B33] border border-[#1E4E5A] rounded-md px-2.5 py-1.5">
                    <span className="px-1.5 py-0.2 rounded bg-[#143D47] text-cyan-accent font-mono text-[11px] shrink-0 border border-[#1E4E5A]">
                      {ev.field}
                    </span>
                    <span className="text-[#94A3B8]">
                      <span className="text-[#F0FDFA] font-medium">{ev.value}</span>
                      {' — '}{ev.explanation}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Career History */}
          {profile.past_companies?.length > 0 && (
            <div className="border-t border-[#1E4E5A] pt-2.5 mt-2">
              <h4 className="text-[10px] font-mono font-bold text-[#94A3B8] mb-1.5 uppercase tracking-wider flex items-center gap-1.5">
                <Briefcase className="w-3 h-3 text-[#5E7A8A]" /> Career Trajectory
              </h4>
              <div className="flex flex-wrap gap-2">
                {profile.past_companies.map((pc, i) => (
                  <span key={i} className="text-xs text-[#94A3B8] bg-[#0C2B33] border border-[#1E4E5A] rounded px-2 py-1 tabular-nums">
                    {pc.title} at <span className="text-[#F0FDFA] font-medium">{pc.company}</span>
                    <span className="text-[#5E7A8A] ml-1">({pc.years}yr, {pc.company_type})</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
