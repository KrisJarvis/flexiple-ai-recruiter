"""
Refine Engine — Translates recruiter feedback into filter/rubric adjustments.

Takes the current state (filters, rubric, shown candidates) plus the
recruiter's feedback (chat message + per-profile thumbs up/down), calls the
LLM to produce updated filters and rubric with explanations of what changed.
Strictly validates all updated filters, rubric, changes made, and reasoning.
"""

import json
import logging
from models import (
    ObjectiveFilters, FitRubric, CandidateScore, CandidateProfile,
    RefinementResponse
)
from prompts import refine_search_prompt
from llm_service import call_llm_structured

logger = logging.getLogger(__name__)


def refine_search(
    current_filters: ObjectiveFilters,
    current_rubric: FitRubric,
    shown_candidates: list[CandidateScore],
    shown_profiles: list[CandidateProfile],
    feedback: str,
    thumbs: dict[str, bool]
) -> RefinementResponse:
    """
    Use the LLM to adjust filters and rubric based on recruiter feedback.
    Strictly validates the refinement result via Pydantic model with 1-time retry on malformed output.
    """
    # Build context for the LLM
    current_filters_json = current_filters.model_dump_json(indent=2)
    current_rubric_json = current_rubric.model_dump_json(indent=2)
    
    # Combine candidate scores with their profiles for context
    candidates_context = []
    profile_map = {p.id: p for p in shown_profiles}
    for idx, score in enumerate(shown_candidates):
        profile = profile_map.get(score.candidate_id)
        if profile:
            candidates_context.append({
                "candidate_number": idx + 1,
                "display_rank": f"#{idx + 1:02d}",
                "candidate_name": profile.name,
                "candidate_id": score.candidate_id,
                "score": score.model_dump(),
                "profile": profile.model_dump(),
                "recruiter_reaction": "thumbs_up" if thumbs.get(score.candidate_id, None) is True 
                    else ("thumbs_down" if thumbs.get(score.candidate_id, None) is False else "no_reaction")
            })
    
    shown_candidates_json = json.dumps(candidates_context, indent=2)
    thumbs_json = json.dumps(thumbs, indent=2)
    
    prompt = refine_search_prompt(
        current_filters_json,
        current_rubric_json,
        shown_candidates_json,
        feedback,
        thumbs_json
    )
    
    return call_llm_structured(
        prompt=prompt,
        validator_fn=lambda raw: RefinementResponse.model_validate(raw),
        temperature=0.3,
        context_desc="refinement response",
        response_schema=RefinementResponse,
    )
