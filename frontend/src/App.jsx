import { useState, useCallback } from 'react';
import { search, refine, freeze } from './api/client';
import SearchScreen from './components/SearchScreen';
import ThinkingScreen from './components/ThinkingScreen';
import Workspace from './components/Workspace';
import FrozenView from './components/FrozenView';
import ErrorBanner from './components/ErrorBanner';

/**
 * App State Machine:
 *   idle → searching → active ⇄ refining → frozen
 *                                ↑              ↓
 *                                └── unfreezing ─┘
 */

export default function App() {
  // Core state
  const [phase, setPhase] = useState('idle'); // idle | searching | active | refining | frozen
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState(null);
  const [rubric, setRubric] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [candidateProfiles, setCandidateProfiles] = useState([]);
  const [totalFiltered, setTotalFiltered] = useState(0);
  const [totalPool, setTotalPool] = useState(0);
  const [isNearMiss, setIsNearMiss] = useState(false);

  // Refinement state
  const [thumbs, setThumbs] = useState({}); // { candidateId: true/false }
  const [rejectedCandidateIds, setRejectedCandidateIds] = useState([]);
  const [chatHistory, setChatHistory] = useState([]); // [{role, content, changes}]
  const [refinementCount, setRefinementCount] = useState(0);

  // Error state
  const [error, setError] = useState(null);

  // Thinking step tracking
  const [thinkingStep, setThinkingStep] = useState('');

  // ─── Search ────────────────────────────────────────────────────────────
  const handleSearch = useCallback(async (searchQuery) => {
    setQuery(searchQuery);
    setPhase('searching');
    setError(null);
    setThinkingStep('Analyzing your requirements...');

    try {
      setThinkingStep('Extracting filters & building rubric...');
      const result = await search(searchQuery);

      setFilters(result.filters);
      setRubric(result.rubric);
      setCandidates(result.candidates);
      setCandidateProfiles(result.candidate_profiles);
      setTotalFiltered(result.total_filtered);
      setTotalPool(result.total_pool);
      setIsNearMiss(Boolean(result.is_near_miss));
      setThumbs({});
      setRejectedCandidateIds([]);
      setChatHistory([]);
      setRefinementCount(0);
      setPhase('active');
    } catch (err) {
      setError(err.message || 'Search failed. Please try again.');
      setPhase('idle');
    }
  }, []);

  // ─── Refine ────────────────────────────────────────────────────────────
  const handleRefine = useCallback(async (feedback) => {
    setPhase('refining');
    setError(null);

    const upCount = Object.values(thumbs).filter(v => v === true).length;
    const downCount = Object.values(thumbs).filter(v => v === false).length;
    const userDisplay = feedback?.trim() || `Calibrated with ${upCount} 👍 and ${downCount} 👎 candidate reactions`;

    // Add user message to chat
    setChatHistory(prev => [...prev, { role: 'user', content: userDisplay }]);

    try {
      // Re-send every explicit rejection in this search session. The current
      // thumbs are only the latest feedback, but a rejected candidate must not
      // quietly return during a later calibration.
      const allReactions = Object.fromEntries(
        rejectedCandidateIds.map(candidateId => [candidateId, false])
      );
      Object.assign(allReactions, thumbs);

      const result = await refine({
        feedback: feedback?.trim() || '',
        currentFilters: filters,
        currentRubric: rubric,
        shownCandidates: candidates,
        shownProfiles: candidateProfiles,
        thumbs: allReactions,
      });

      setFilters(result.filters);
      setRubric(result.rubric);
      setCandidates(result.candidates);
      setCandidateProfiles(result.candidate_profiles);
      setTotalFiltered(result.total_filtered);
      setTotalPool(result.total_pool);
      setIsNearMiss(Boolean(result.is_near_miss));
      setThumbs({});
      setRefinementCount(prev => prev + 1);

      // Add AI response to chat
      setChatHistory(prev => [
        ...prev,
        {
          role: 'assistant',
          content: result.reasoning,
          changes: result.changes_made,
        },
      ]);

      setPhase('active');
    } catch (err) {
      setError(err.message || 'Refinement failed. Please try again.');
      setChatHistory(prev => [
        ...prev,
        { role: 'error', content: err.message || 'Refinement failed.' },
      ]);
      setPhase('active');
    }
  }, [filters, rubric, candidates, candidateProfiles, thumbs, rejectedCandidateIds]);

  // ─── Thumbs ────────────────────────────────────────────────────────────
  const handleThumb = useCallback((candidateId, isUp) => {
    setThumbs(prev => {
      const next = { ...prev };
      if (next[candidateId] === isUp) {
        delete next[candidateId]; // Toggle off
      } else {
        next[candidateId] = isUp;
      }

      setRejectedCandidateIds(previousRejected => {
        if (next[candidateId] === false) {
          return previousRejected.includes(candidateId)
            ? previousRejected
            : [...previousRejected, candidateId];
        }
        return previousRejected.filter(id => id !== candidateId);
      });

      return next;
    });
  }, []);

  // ─── Freeze ────────────────────────────────────────────────────────────
  const handleFreeze = useCallback(async () => {
    try {
      await freeze({
        filters,
        rubric,
        candidates,
        candidateProfiles,
      });
      setPhase('frozen');
    } catch (err) {
      setError(err.message || 'Freeze failed.');
    }
  }, [filters, rubric, candidates, candidateProfiles]);

  // ─── Unfreeze ──────────────────────────────────────────────────────────
  const handleUnfreeze = useCallback(() => {
    setPhase('active');
  }, []);

  // ─── New Search ────────────────────────────────────────────────────────
  const handleNewSearch = useCallback(() => {
    setPhase('idle');
    setQuery('');
    setFilters(null);
    setRubric(null);
    setCandidates([]);
    setCandidateProfiles([]);
    setThumbs({});
    setRejectedCandidateIds([]);
    setChatHistory([]);
    setError(null);
    setRefinementCount(0);
  }, []);

  return (
    <div className="min-h-screen bg-surface-950">
      {/* Error Banner */}
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* Phase: Idle — Search Screen */}
      {phase === 'idle' && (
        <SearchScreen onSearch={handleSearch} />
      )}

      {/* Phase: Searching — Thinking Screen */}
      {phase === 'searching' && (
        <ThinkingScreen query={query} step={thinkingStep} />
      )}

      {/* Phase: Active / Refining — Main Workspace */}
      {(phase === 'active' || phase === 'refining') && (
        <Workspace
          query={query}
          filters={filters}
          rubric={rubric}
          candidates={candidates}
          candidateProfiles={candidateProfiles}
          totalFiltered={totalFiltered}
          totalPool={totalPool}
          isNearMiss={isNearMiss}
          thumbs={thumbs}
          chatHistory={chatHistory}
          refinementCount={refinementCount}
          isRefining={phase === 'refining'}
          onThumb={handleThumb}
          onRefine={handleRefine}
          onFreeze={handleFreeze}
          onNewSearch={handleNewSearch}
        />
      )}

      {/* Phase: Frozen — Final Summary */}
      {phase === 'frozen' && (
        <FrozenView
          query={query}
          filters={filters}
          rubric={rubric}
          candidates={candidates}
          candidateProfiles={candidateProfiles}
          totalFiltered={totalFiltered}
          totalPool={totalPool}
          refinementCount={refinementCount}
          onUnfreeze={handleUnfreeze}
          onNewSearch={handleNewSearch}
        />
      )}
    </div>
  );
}
