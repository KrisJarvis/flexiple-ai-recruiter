import { Filter, MapPin, Briefcase, Code, Clock, X, CheckSquare } from 'lucide-react';

export default function FilterPanel({ filters }) {
  if (!filters) return null;

  return (
    <div className="bg-[#143D47] border border-[#1E4E5A] rounded-xl p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 mb-3.5 border-b border-[#1E4E5A]">
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-cyan-accent" />
          <h3 className="text-xs font-bold text-[#F0FDFA] uppercase tracking-wider">
            Objective Filters
          </h3>
        </div>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#0C2B33] text-cyan-accent border border-[#1E4E5A]">
          HARD GATES
        </span>
      </div>

      <div className="space-y-3.5 text-xs">
        {/* Required Skills */}
        {filters.required_skills?.length > 0 && (
          <div>
            <label className="text-[#94A3B8] text-[11px] font-medium flex items-center gap-1.5 mb-1.5">
              <Code className="w-3 h-3 text-[#A3E635]" /> Required Skills
            </label>
            <div className="flex flex-wrap gap-1.5">
              {filters.required_skills.map((skill, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded bg-[#0C2B33] text-[#A3E635] border border-[#A3E635]/40 text-xs font-mono font-medium"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Preferred Skills */}
        {filters.preferred_skills?.length > 0 && (
          <div>
            <label className="text-[#94A3B8] text-[11px] font-medium flex items-center gap-1.5 mb-1.5">
              <CheckSquare className="w-3 h-3 text-cyan-accent" /> Preferred Skills
            </label>
            <div className="flex flex-wrap gap-1.5">
              {filters.preferred_skills.map((skill, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded bg-[#0C2B33] text-[#F0FDFA] border border-[#1E4E5A] text-xs font-mono"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Experience Range */}
        {(filters.min_years_experience != null || filters.max_years_experience != null) && (
          <div className="bg-[#0C2B33] border border-[#1E4E5A] rounded-lg p-2.5 flex items-center justify-between">
            <span className="text-[#94A3B8] text-[11px] flex items-center gap-1.5">
              <Clock className="w-3 h-3 text-cyan-accent" /> Experience
            </span>
            <span className="text-[#F0FDFA] font-mono tabular-nums font-semibold text-xs">
              {filters.min_years_experience ?? 0} – {filters.max_years_experience ?? '∞'} YEARS
            </span>
          </div>
        )}

        {/* Location */}
        {filters.locations?.length > 0 && (
          <div>
            <label className="text-[#94A3B8] text-[11px] font-medium flex items-center gap-1.5 mb-1.5">
              <MapPin className="w-3 h-3 text-cyan-accent" /> Locations
            </label>
            <div className="flex flex-wrap gap-1.5">
              {filters.locations.map((loc, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded bg-[#0C2B33] text-cyan-accent border border-cyan-accent/30 text-xs font-mono"
                >
                  {loc}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Company Types */}
        {filters.company_types?.length > 0 && (
          <div>
            <label className="text-[#94A3B8] text-[11px] font-medium flex items-center gap-1.5 mb-1.5">
              <Briefcase className="w-3 h-3 text-[#FACC15]" /> Company Archetypes
            </label>
            <div className="flex flex-wrap gap-1.5">
              {filters.company_types.map((type, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded bg-[#0C2B33] text-[#FACC15] border border-[#FACC15]/30 text-xs font-mono capitalize"
                >
                  {type}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Title Keywords */}
        {filters.title_keywords?.length > 0 && (
          <div>
            <label className="text-[#94A3B8] text-[11px] font-medium mb-1.5 block">Title Keywords</label>
            <div className="flex flex-wrap gap-1.5">
              {filters.title_keywords.map((kw, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded bg-[#0C2B33] text-[#94A3B8] border border-[#1E4E5A] text-xs font-mono"
                >
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Exclude Skills */}
        {filters.exclude_skills?.length > 0 && (
          <div>
            <label className="text-[#94A3B8] text-[11px] font-medium flex items-center gap-1.5 mb-1.5">
              <X className="w-3 h-3 text-[#FB7185]" /> Excluded
            </label>
            <div className="flex flex-wrap gap-1.5">
              {filters.exclude_skills.map((skill, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded bg-[#0C2B33] text-[#FB7185] border border-[#FB7185]/30 text-xs font-mono line-through"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
