"""
Pydantic models for the AI Recruiter sourcing refinement loop.
These define the structured schemas for:
- Objective Filters (deterministic filtering)
- Subjective Fit Rubric (LLM scoring criteria)
- Candidate Scores (LLM-generated match evaluations)
- Refinement responses (filter/rubric adjustments from feedback)
"""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Any
from enum import Enum
from llm_service import ScoringError


# ─── Company Types ───────────────────────────────────────────────────────────

class CompanyType(str, Enum):
    STARTUP = "startup"
    SCALEUP = "scaleup"
    ENTERPRISE = "enterprise"
    AGENCY = "agency"


# ─── Objective Filters ──────────────────────────────────────────────────────

class ObjectiveFilters(BaseModel):
    """Structured filters extracted from free-text recruiter query."""
    required_skills: list[str] = Field(default_factory=list, description="Skills that candidates MUST have")
    preferred_skills: list[str] = Field(default_factory=list, description="Skills that are nice-to-have")
    min_years_experience: Optional[int] = Field(default=None, description="Minimum years of experience")
    max_years_experience: Optional[int] = Field(default=None, description="Maximum years of experience")
    locations: list[str] = Field(default_factory=list, description="Preferred candidate locations")
    company_types: list[CompanyType] = Field(default_factory=list, description="Preferred company background types (current or past)")
    current_company: Optional[str] = Field(default=None, description="Target company for candidate's current role")
    companies: list[str] = Field(default_factory=list, description="Target companies (current or past)")
    past_companies: list[str] = Field(default_factory=list, description="Target past companies")
    current_company_types: list[CompanyType] = Field(default_factory=list, description="Target company types for current role")
    past_company_types: list[CompanyType] = Field(default_factory=list, description="Target company types for past roles")
    title_keywords: list[str] = Field(default_factory=list, description="Keywords to match against job titles")
    exclude_skills: list[str] = Field(default_factory=list, description="Skills to explicitly exclude")

    @field_validator('company_types', 'current_company_types', 'past_company_types', mode='before')
    @classmethod
    def normalize_company_types(cls, v: Any) -> list[CompanyType]:
        if not v:
            return []
        if isinstance(v, (str, CompanyType)):
            v = [v]
        if not isinstance(v, list):
            return []
        normalized = []
        mapping = {
            "startup": CompanyType.STARTUP,
            "startups": CompanyType.STARTUP,
            "scaleup": CompanyType.SCALEUP,
            "scaleups": CompanyType.SCALEUP,
            "enterprise": CompanyType.ENTERPRISE,
            "enterprises": CompanyType.ENTERPRISE,
            "agency": CompanyType.AGENCY,
            "agencies": CompanyType.AGENCY,
        }
        for item in v:
            if isinstance(item, CompanyType):
                normalized.append(item)
            elif isinstance(item, str):
                cleaned = item.lower().strip()
                if cleaned in mapping:
                    normalized.append(mapping[cleaned])
                elif cleaned.rstrip('s') in mapping:
                    normalized.append(mapping[cleaned.rstrip('s')])
                else:
                    raise ValueError(
                        f"Invalid company_type '{item}'. Valid values are: {[e.value for e in CompanyType]}"
                    )
            else:
                raise ValueError(
                    f"Invalid company_type value type '{type(item).__name__}'. Expected string or CompanyType."
                )
        return normalized

    @field_validator('required_skills', 'preferred_skills', 'locations', 'title_keywords', 'exclude_skills', 'companies', 'past_companies', mode='before')
    @classmethod
    def clean_str_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            cleaned = v.strip()
            return [cleaned] if cleaned else []
        if not isinstance(v, list):
            return []
        result = []
        for x in v:
            if x is not None and str(x).strip():
                result.append(str(x).strip())
        return result

    @field_validator('current_company', mode='before')
    @classmethod
    def clean_single_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, list):
            v = v[0] if v else None
        if v is None:
            return None
        cleaned = str(v).strip()
        return cleaned if cleaned else None

    @field_validator('min_years_experience', 'max_years_experience', mode='before')
    @classmethod
    def clean_experience_int(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return None
        try:
            return round(float(v))
        except (ValueError, TypeError, OverflowError):
            return None

    @model_validator(mode='after')
    def validate_experience_range(self) -> 'ObjectiveFilters':
        if self.min_years_experience is not None and self.min_years_experience < 0:
            raise ValueError(f"min_years_experience cannot be negative (got {self.min_years_experience})")
        if self.max_years_experience is not None and self.max_years_experience < 0:
            raise ValueError(f"max_years_experience cannot be negative (got {self.max_years_experience})")
        if (self.min_years_experience is not None and 
            self.max_years_experience is not None and 
            self.min_years_experience > self.max_years_experience):
            raise ValueError(
                f"min_years_experience ({self.min_years_experience}) cannot be greater than "
                f"max_years_experience ({self.max_years_experience})"
            )
        return self


# ─── Subjective Fit Rubric ──────────────────────────────────────────────────

class RubricCriterion(BaseModel):
    """A single scoring criterion in the fit rubric."""
    name: str = Field(min_length=1, description="Name of the criterion (e.g., 'Domain expertise')")
    weight: int = Field(default=3, ge=1, le=5, description="Importance weight 1-5")
    description: str = Field(min_length=1, description="What good looks like for this criterion")

    @field_validator('name', 'description')
    @classmethod
    def validate_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()

    @field_validator('weight', mode='before')
    @classmethod
    def validate_weight(cls, v: Any) -> int:
        try:
            val = round(float(v))
            if not (1 <= val <= 5):
                raise ValueError(f"Weight must be between 1 and 5, got {val}")
            return val
        except (ValueError, TypeError, OverflowError) as e:
            raise ValueError(f"Criterion weight must be an integer between 1 and 5: {e}")


class FitRubric(BaseModel):
    """Subjective fit rubric that defines what 'good' looks like for this role."""
    role_summary: str = Field(min_length=1, description="One-line summary of the ideal candidate")
    criteria: list[RubricCriterion] = Field(min_length=1, description="Scoring criteria with weights")
    dealbreakers: list[str] = Field(default_factory=list, description="Automatic disqualifiers")
    positive_signals: list[str] = Field(default_factory=list, description="Strong positive indicators")

    @field_validator('role_summary')
    @classmethod
    def validate_role_summary(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("role_summary cannot be empty")
        return v.strip()

    @field_validator('criteria')
    @classmethod
    def validate_criteria(cls, v: list[RubricCriterion]) -> list[RubricCriterion]:
        if not v or len(v) == 0:
            raise ValueError("criteria cannot be empty: must provide at least one RubricCriterion")
        return v


class SearchParseResponse(BaseModel):
    """Container for validated search query parsing."""
    filters: ObjectiveFilters
    rubric: FitRubric


# ─── Profile (from profiles.json) ───────────────────────────────────────────

class PastCompany(BaseModel):
    company: str = ""
    company_type: str = ""
    title: str = ""
    years: int = 0

    @field_validator('company', 'company_type', 'title', mode='before')
    @classmethod
    def clean_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator('years', mode='before')
    @classmethod
    def clean_years(cls, v: Any) -> int:
        if v is None or v == "":
            return 0
        try:
            return round(float(v))
        except (ValueError, TypeError, OverflowError):
            return 0


class CandidateProfile(BaseModel):
    id: str
    name: str = ""
    current_title: str = ""
    years_experience: int = 0
    location: str = ""
    current_company: str = ""
    current_company_type: str = ""
    skills: list[str] = Field(default_factory=list)
    past_companies: list[PastCompany] = Field(default_factory=list)
    education: Optional[str] = ""
    summary: Optional[str] = ""

    @field_validator('id', 'name', 'current_title', 'location', 'current_company', 'current_company_type', 'education', 'summary', mode='before')
    @classmethod
    def clean_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator('skills', mode='before')
    @classmethod
    def clean_skills(cls, v: Any) -> list[str]:
        if not v:
            return []
        if isinstance(v, str):
            cleaned = v.strip()
            return [cleaned] if cleaned else []
        if not isinstance(v, list):
            return []
        return [str(s).strip() for s in v if s is not None and str(s).strip()]

    @field_validator('past_companies', mode='before')
    @classmethod
    def clean_past_companies(cls, v: Any) -> list[Any]:
        if not v or not isinstance(v, list):
            return []
        return v

    @field_validator('years_experience', mode='before')
    @classmethod
    def clean_years_experience(cls, v: Any) -> int:
        if v is None or v == "":
            return 0
        try:
            return round(float(v))
        except (ValueError, TypeError, OverflowError):
            return 0


# ─── Candidate Scoring ──────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    """A single piece of evidence citing an actual field from the candidate's profile."""
    field: str = Field(min_length=1, description="The profile field being cited (e.g., 'skills', 'years_experience')")
    value: Any = Field(description="The actual value from the profile")
    explanation: str = Field(min_length=1, description="How this value relates to the rubric")

    @field_validator('field', 'explanation')
    @classmethod
    def validate_str_fields(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Evidence field and explanation must be non-empty strings")
        return v.strip()

    @field_validator('value', mode='before')
    @classmethod
    def stringify_and_validate_value(cls, v: Any) -> str:
        if v is None:
            raise ValueError("Evidence value cannot be None")
        if isinstance(v, list):
            val = ", ".join(str(item) if not isinstance(item, dict) else f"{item.get('title', '')} at {item.get('company', '')}" for item in v)
        elif isinstance(v, dict):
            val = ", ".join(f"{k}: {item}" for k, item in v.items())
        else:
            val = str(v).strip()
        if not val:
            raise ValueError("Evidence value cannot be empty")
        return val


class CriterionScore(BaseModel):
    """How a candidate scored against one rubric criterion."""
    criterion_name: str = Field(min_length=1, description="Rubric criterion name")
    score: int = Field(ge=0, le=10, description="Score 0-10 for this criterion")
    comment: str = Field(min_length=1, description="Brief explanation of the score")

    @field_validator('criterion_name', 'comment')
    @classmethod
    def validate_str_fields(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Criterion name and comment cannot be empty")
        return v.strip()

    @field_validator('score', mode='before')
    @classmethod
    def validate_score_range(cls, v: Any) -> int:
        try:
            val = round(float(v))
            if not (0 <= val <= 10):
                raise ValueError(f"Criterion score must be between 0 and 10, got {val}")
            return val
        except (ValueError, TypeError, OverflowError) as e:
            raise ValueError(f"Criterion score must be an integer between 0 and 10: {e}")


class CandidateScore(BaseModel):
    """Complete LLM-generated score for one candidate against the rubric."""
    candidate_id: str = Field(min_length=1, description="Candidate ID from the profile")
    overall_score: int = Field(ge=0, le=100, description="Weighted overall score 0-100")
    match_tier: str = Field(description="'strong_match', 'moderate_match', or 'weak_match'")
    match_reason: str = Field(min_length=1, description="One-sentence summary of why this candidate matched (citing real details)")
    evidence: list[EvidenceItem] = Field(min_length=1, description="Specific profile fields that support the match")
    criterion_scores: list[CriterionScore] = Field(default_factory=list, description="Per-criterion breakdown")

    @field_validator('candidate_id', 'match_reason')
    @classmethod
    def validate_non_empty_str(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Candidate ID and match_reason cannot be empty")
        return v.strip()

    @field_validator('overall_score', mode='before')
    @classmethod
    def validate_overall_score(cls, v: Any) -> int:
        try:
            val = round(float(v))
            if not (0 <= val <= 100):
                raise ValueError(f"overall_score must be between 0 and 100, got {val}")
            return val
        except (ValueError, TypeError, OverflowError) as e:
            raise ValueError(f"overall_score must be an integer between 0 and 100: {e}")

    @field_validator('match_tier')
    @classmethod
    def validate_match_tier(cls, v: str) -> str:
        valid_tiers = {"strong_match", "moderate_match", "weak_match"}
        cleaned = v.lower().strip()
        if cleaned not in valid_tiers:
            raise ValueError(f"match_tier must be one of {valid_tiers}, got '{v}'")
        return cleaned

    @field_validator('evidence')
    @classmethod
    def validate_evidence(cls, v: list[EvidenceItem]) -> list[EvidenceItem]:
        if not v or len(v) == 0:
            raise ValueError("Candidate evidence cannot be empty")
        return v


class CandidateScoreBatch(BaseModel):
    """Container for a batch of candidate scores from the LLM."""
    scores: list[CandidateScore] = Field(description="Scores for each candidate in the batch")


def validate_candidate_scores_batch(
    scores_data: Any,
    expected_ids: set[str]
) -> list[CandidateScore]:
    """
    Strictly validate candidate scores returned by LLM:
    - malformed response (must be a valid list or wrapped dict)
    - candidate IDs (must match expected profiles)
    - unknown candidate IDs (reject any not in expected_ids)
    - duplicate candidates (none allowed)
    - missing candidates (all expected candidates must be scored)
    - score range (0-100 overall, 0-10 criterion)
    - explanation and evidence (every candidate must have evidence and match_reason)
    """
    if scores_data is None:
        raise ScoringError("Malformed response: AI returned null/empty scoring data")

    if isinstance(scores_data, dict):
        for key in ("scores", "candidates", "candidate_scores", "results", "data"):
            if key in scores_data and isinstance(scores_data[key], list):
                scores_data = scores_data[key]
                break

    if not isinstance(scores_data, list):
        raise ScoringError(f"Malformed response: expected JSON array of candidate scores, got {type(scores_data).__name__}")
    
    validated_scores: list[CandidateScore] = []
    seen_ids: set[str] = set()

    for item in scores_data:
        if not isinstance(item, dict):
            raise ScoringError(f"Malformed response: candidate score item is not a JSON object: {item}")

        cid = item.get("candidate_id")
        if not cid or not str(cid).strip():
            raise ScoringError("Candidate score item is missing 'candidate_id'")
        cid = str(cid).strip()

        # Check unknown candidate ID
        if cid not in expected_ids:
            raise ScoringError(
                f"Unknown candidate ID '{cid}' returned by AI. Candidate was not in the expected candidate batch ({sorted(list(expected_ids))})"
            )

        # Check duplicate candidate ID
        if cid in seen_ids:
            raise ScoringError(f"Duplicate candidate ID '{cid}' returned by AI in scoring output")

        # Check score presence and range
        score_val = item.get("overall_score")
        if score_val is None:
            raise ScoringError(f"Candidate '{cid}' is missing 'overall_score'")
        try:
            numeric_score = round(float(score_val))
            if not (0 <= numeric_score <= 100):
                raise ScoringError(
                    f"Invalid overall_score '{score_val}' for candidate '{cid}'. Must be between 0 and 100."
                )
        except (ValueError, TypeError, OverflowError) as e:
            raise ScoringError(
                f"Invalid non-numeric overall_score '{score_val}' for candidate '{cid}': {e}"
            )

        # Check explanation (match_reason)
        match_reason = item.get("match_reason")
        if not match_reason or not str(match_reason).strip():
            raise ScoringError(f"Missing explanation for candidate '{cid}': 'match_reason' cannot be empty")

        # Check evidence
        evidence = item.get("evidence")
        if not evidence or not isinstance(evidence, list) or len(evidence) == 0:
            raise ScoringError(f"Missing evidence for candidate '{cid}': every candidate must have evidence explaining the score")

        for ev in evidence:
            if not isinstance(ev, dict):
                raise ScoringError(f"Malformed evidence item for candidate '{cid}': expected object")
            if not ev.get("field") or not str(ev.get("field")).strip():
                raise ScoringError(f"Candidate '{cid}' evidence item has an empty 'field'")
            if ev.get("value") is None or not str(ev.get("value")).strip():
                raise ScoringError(f"Candidate '{cid}' evidence item has an empty 'value'")
            if not ev.get("explanation") or not str(ev.get("explanation")).strip():
                raise ScoringError(f"Candidate '{cid}' evidence item has an empty 'explanation'")

        try:
            score = CandidateScore.model_validate(item)
        except Exception as e:
            raise ScoringError(f"Invalid candidate score for '{cid}': {e}") from e

        seen_ids.add(cid)
        validated_scores.append(score)

    missing_ids = expected_ids - seen_ids
    if missing_ids:
        raise ScoringError(
            f"AI output is missing scores for candidates: {sorted(list(missing_ids))}"
        )

    return validated_scores


# ─── Refinement ─────────────────────────────────────────────────────────────

class RefinementChange(BaseModel):
    """A single change made during refinement."""
    description: str = Field(min_length=1, description="Description of the change made")

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Change description cannot be empty")
        return v.strip()


class RefinementChanges(BaseModel):
    """Collection of changes made during refinement."""
    changes: list[str] = Field(min_length=1, description="List of change descriptions")

    @field_validator('changes')
    @classmethod
    def validate_changes(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("changes cannot be empty")
        cleaned = [item.strip() for item in v if isinstance(item, str) and item.strip()]
        if not cleaned:
            raise ValueError("changes must contain at least one non-empty string")
        return cleaned


class RefinementResponse(BaseModel):
    """LLM-generated adjustments to filters and rubric based on recruiter feedback."""
    updated_filters: ObjectiveFilters
    updated_rubric: FitRubric
    changes_made: list[str] = Field(min_length=1, description="Human-readable list of what changed and why")
    reasoning: str = Field(min_length=1, description="Brief explanation of the refinement logic")

    @field_validator('changes_made')
    @classmethod
    def validate_changes_made(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("changes_made cannot be empty")
        cleaned = [c.strip() for c in v if isinstance(c, str) and c.strip()]
        if not cleaned:
            raise ValueError("changes_made must contain at least one non-empty description")
        return cleaned

    @field_validator('reasoning')
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("reasoning cannot be empty")
        return v.strip()


# Alias for semantic clarity
RefinementResult = RefinementResponse


# ─── API Request/Response Models ────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(description="Free-text recruiter search query")


class SearchResponse(BaseModel):
    filters: ObjectiveFilters
    rubric: FitRubric
    candidates: list[CandidateScore]
    candidate_profiles: list[CandidateProfile]
    total_filtered: int = Field(description="How many candidates passed objective filters")
    total_pool: int = Field(description="Total candidates in the pool")
    is_near_miss: bool = Field(default=False, description="Whether near-miss fallback candidates are being returned")


class RefineRequest(BaseModel):
    feedback: str = Field(default="", description="Recruiter's natural language feedback")
    current_filters: ObjectiveFilters
    current_rubric: FitRubric
    shown_candidates: list[CandidateScore] = Field(description="The candidates that were shown")
    shown_profiles: list[CandidateProfile] = Field(description="The profiles that were shown")
    thumbs: dict[str, bool] = Field(default_factory=dict, description="Per-candidate thumbs up (True) / down (False) by candidate_id")


class RefineResponse(BaseModel):
    filters: ObjectiveFilters
    rubric: FitRubric
    candidates: list[CandidateScore]
    candidate_profiles: list[CandidateProfile]
    changes_made: list[str]
    reasoning: str
    total_filtered: int
    total_pool: int
    is_near_miss: bool = Field(default=False, description="Whether near-miss fallback candidates are being returned")


class FreezeRequest(BaseModel):
    filters: ObjectiveFilters
    rubric: FitRubric
    candidates: list[CandidateScore]
    candidate_profiles: list[CandidateProfile]


class FreezeResponse(BaseModel):
    filters: ObjectiveFilters
    rubric: FitRubric
    candidates: list[CandidateScore]
    candidate_profiles: list[CandidateProfile]
    frozen: bool = True
