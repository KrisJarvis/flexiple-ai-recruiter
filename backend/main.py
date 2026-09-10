"""
AI Recruiter — FastAPI Backend

Serves the sourcing refinement loop:
  POST /api/search  — Free-text → filters + rubric + scored candidates
  POST /api/refine  — Feedback → adjusted filters + rubric + re-scored candidates  
  POST /api/freeze  — Lock final state
  GET  /api/health   — Health check + API key status
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from models import (
    SearchRequest, SearchResponse,
    RefineRequest, RefineResponse,
    FreezeRequest, FreezeResponse,
    ObjectiveFilters, FitRubric, CandidateProfile,
    SearchParseResponse
)
from llm_service import (
    call_llm_structured,
    LLMError, LLMRateLimitError, LLMValidationError, ScoringError
)
from filter_engine import load_profiles, filter_candidates
from scoring_engine import score_and_rank
from refine_engine import refine_search
from prompts import parse_query_prompt

from pathlib import Path
# ─── Load env vars ──────────────────────────────────────────────────────────
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Load profiles on startup ──────────────────────────────────────────────

ALL_PROFILES: list[CandidateProfile] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ALL_PROFILES
    ALL_PROFILES = load_profiles()
    logger.info(f"Loaded {len(ALL_PROFILES)} candidate profiles")
    yield


app = FastAPI(
    title="AI Recruiter API",
    description="Sourcing refinement loop for Flexiple",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Exception Handlers: Never let malformed LLM output crash the backend ──

@app.exception_handler(ScoringError)
async def scoring_error_handler(request: Request, exc: ScoringError):
    logger.error(f"Candidate scoring error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": f"Candidate scoring failed: {exc}",
            "error_type": "scoring_error",
            "recoverable": exc.recoverable
        }
    )


@app.exception_handler(LLMValidationError)
async def llm_validation_error_handler(request: Request, exc: LLMValidationError):
    logger.error(f"LLM validation error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error_type": "llm_validation_error", "recoverable": True}
    )


@app.exception_handler(LLMRateLimitError)
async def llm_rate_limit_error_handler(request: Request, exc: LLMRateLimitError):
    logger.error(f"LLM rate limit error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc), "error_type": "rate_limit_error", "recoverable": True}
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    logger.error(f"LLM error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc), "error_type": "llm_service_error", "recoverable": True}
    )


# ─── Health Check ───────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    has_key = bool(os.environ.get("GEMINI_API_KEY"))
    return {
        "status": "ok",
        "profiles_loaded": len(ALL_PROFILES),
        "api_key_configured": has_key,
    }


# ─── Search: Free-text → Filters + Rubric + Scored Candidates ──────────────

@app.post("/api/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    try:
        # Step 1: LLM parses free-text into filters + rubric with validation and 1-time retry
        prompt = parse_query_prompt(req.query)
        parsed = call_llm_structured(
            prompt=prompt,
            validator_fn=lambda raw: SearchParseResponse.model_validate(raw),
            temperature=0.3,
            context_desc="search query parsing",
        )
        filters = parsed.filters
        rubric = parsed.rubric
        
    except LLMRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except LLMValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in query parsing: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while parsing your search query.")
    
    try:
        # Step 2: Apply objective filters deterministically in Python
        matched, _ = filter_candidates(ALL_PROFILES, filters)
        filtered_candidates = matched
        
        valid_profile_ids = {p.id for p in ALL_PROFILES}
        filtered_candidate_ids = {c.id for c in filtered_candidates}
        
        if not filtered_candidates:
            validated_scored = []
            scored_profiles = []
        else:
            # Step 3: Score and rank strictly filtered candidates using Gemini
            scored = score_and_rank(filtered_candidates, rubric, top_n=5)
            
            # Strict guarantee: Gemini can NEVER invent a candidate or bypass an objective filter
            validated_scored = [
                s for s in scored 
                if s.candidate_id in filtered_candidate_ids and s.candidate_id in valid_profile_ids
            ]
            
            profile_map = {p.id: p for p in ALL_PROFILES}
            scored_profiles = [
                profile_map[s.candidate_id] 
                for s in validated_scored 
                if s.candidate_id in profile_map
            ]
        
        return SearchResponse(
            filters=filters,
            rubric=rubric,
            candidates=validated_scored,
            candidate_profiles=scored_profiles,
            total_filtered=len(filtered_candidates),
            total_pool=len(ALL_PROFILES),
            is_near_miss=False,
        )
        
    except (ScoringError, LLMValidationError) as e:
        logger.warning(f"Candidate scoring error in search: {e}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": f"Candidate scoring failed: {e}",
                "error_type": "scoring_error",
                "recoverable": getattr(e, "recoverable", True),
            }
        )
    except LLMRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in candidate ranking: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while scoring and ranking candidates.")


# ─── Refine: Feedback → Adjusted Filters + Rubric + Re-scored ──────────────

@app.post("/api/refine", response_model=RefineResponse)
async def refine(req: RefineRequest):
    try:
        # Step 1: LLM adjusts filters and rubric based on feedback
        refinement = refine_search(
            current_filters=req.current_filters,
            current_rubric=req.current_rubric,
            shown_candidates=req.shown_candidates,
            shown_profiles=req.shown_profiles,
            feedback=req.feedback,
            thumbs=req.thumbs,
        )
        
        updated_filters = refinement.updated_filters
        updated_rubric = refinement.updated_rubric
        
    except LLMRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except LLMValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    
    try:
        # Step 2: Re-filter with updated filters deterministically in Python
        matched, _ = filter_candidates(ALL_PROFILES, updated_filters)
        filtered_candidates = matched
        
        valid_profile_ids = {p.id for p in ALL_PROFILES}
        filtered_candidate_ids = {c.id for c in filtered_candidates}
        
        if not filtered_candidates:
            validated_scored = []
            scored_profiles = []
        else:
            # Step 3: Re-score strictly filtered candidates using Gemini
            scored = score_and_rank(filtered_candidates, updated_rubric, top_n=5)
            
            # Strict guarantee: Gemini can NEVER invent a candidate or bypass an objective filter
            validated_scored = [
                s for s in scored 
                if s.candidate_id in filtered_candidate_ids and s.candidate_id in valid_profile_ids
            ]
            
            profile_map = {p.id: p for p in ALL_PROFILES}
            scored_profiles = [
                profile_map[s.candidate_id] 
                for s in validated_scored 
                if s.candidate_id in profile_map
            ]
        
        return RefineResponse(
            filters=updated_filters,
            rubric=updated_rubric,
            candidates=validated_scored,
            candidate_profiles=scored_profiles,
            changes_made=refinement.changes_made,
            reasoning=refinement.reasoning,
            total_filtered=len(filtered_candidates),
            total_pool=len(ALL_PROFILES),
            is_near_miss=False,
        )
        
    except (ScoringError, LLMValidationError) as e:
        logger.warning(f"Candidate scoring error in refine: {e}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": f"Candidate scoring failed: {e}. Previously valid candidate shortlist has been preserved.",
                "error_type": "scoring_error",
                "recoverable": True,
                "preserved_filters": req.current_filters.model_dump(),
                "preserved_rubric": req.current_rubric.model_dump(),
                "preserved_candidates": [s.model_dump() for s in req.shown_candidates],
                "preserved_profiles": [p.model_dump() for p in req.shown_profiles],
            }
        )
    except LLMRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in candidate re-ranking: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while re-ranking candidates.")


# ─── Freeze: Lock the final state ──────────────────────────────────────────

@app.post("/api/freeze", response_model=FreezeResponse)
async def freeze(req: FreezeRequest):
    return FreezeResponse(
        filters=req.filters,
        rubric=req.rubric,
        candidates=req.candidates,
        candidate_profiles=req.candidate_profiles,
        frozen=True,
    )
