"""
Scoring Engine — LLM-powered rubric scoring with evidence citations.

Flow:
profiles.json
→ deterministic filters
→ filtered candidates
→ Gemini scoring against fit rubric
→ validated scores
→ Python ranking

Rules enforced:
- Gemini must score only candidates actually passed to it.
- Gemini must not create candidates.
- Candidate IDs must be validated (no unknown, duplicate, or missing).
- Scores must be within defined range (0-100 overall, 0-10 criterion).
- Every candidate must have evidence explaining the score.
- Python performs final sorting/ranking without trusting Gemini's returned order.
- Returns a structured recoverable error on scoring failure.
"""

import json
import logging
from models import CandidateProfile, FitRubric, CandidateScore, validate_candidate_scores_batch
from prompts import score_candidates_prompt
from llm_service import call_llm_structured, ScoringError

logger = logging.getLogger(__name__)

TIER_WEIGHTS = {
    "strong_match": 3,
    "moderate_match": 2,
    "weak_match": 1,
}


def _rank_candidates(scores: list[CandidateScore]) -> list[CandidateScore]:
    """
    Python-authoritative deterministic ranking.
    Do not trust Gemini's return order blindly.

    Tie-breaking hierarchy:
    1. overall_score (descending)
    2. Sum of criterion scores (descending)
    3. Match tier weight (strong > moderate > weak)
    4. Stable tie-breaker: candidate_id (ascending)
    """
    return sorted(
        scores,
        key=lambda s: (
            -s.overall_score,
            -sum(c.score for c in (s.criterion_scores or [])),
            -TIER_WEIGHTS.get(s.match_tier, 0),
            s.candidate_id
        )
    )


def score_and_rank(
    candidates: list[CandidateProfile],
    rubric: FitRubric,
    top_n: int = 5
) -> list[CandidateScore]:
    """
    Score filtered candidates against the rubric using Gemini, validate strictly,
    and rank authoritatively in Python.
    
    Returns the top N candidates sorted by score descending.
    If Gemini returns malformed or invalid output after retry, raises ScoringError
    which is returned as a structured recoverable error.
    """
    if not candidates:
        return []

    rubric_json = rubric.model_dump_json(indent=2)
    all_scores: list[CandidateScore] = []
    batch_size = 6

    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        expected_ids = {c.id for c in batch}
        candidates_json = json.dumps(
            [c.model_dump() for c in batch],
            indent=2
        )

        prompt = score_candidates_prompt(rubric_json, candidates_json)

        batch_scores = call_llm_structured(
            prompt=prompt,
            validator_fn=lambda raw, eids=expected_ids: validate_candidate_scores_batch(raw, eids),
            temperature=0.3,
            context_desc=f"candidate scores batch ({len(batch)} candidates: {sorted(list(expected_ids))})",
        )
        all_scores.extend(batch_scores)

    # Authoritative Python ranking (never trust Gemini's order blindly)
    ranked_scores = _rank_candidates(all_scores)
    return ranked_scores[:top_n]
