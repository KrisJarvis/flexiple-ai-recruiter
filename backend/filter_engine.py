"""
Filter Engine — Deterministic local filtering against candidate profiles.

This runs the objective filters extracted by the LLM against the candidate
profiles from profiles.json. Pure Python logic — no LLM calls here.

Python is responsible for enforcing objective criteria:
- skills (required, preferred, excluded)
- minimum experience
- maximum experience
- location (with aliases)
- company type (current, past, or either)
- current company
- past company / company type where applicable

Handles:
- case differences
- whitespace differences
- missing optional fields
- empty skills
- missing past_companies
"""

import json
import os
from typing import Any, Optional
from models import CandidateProfile, ObjectiveFilters, CompanyType

# ─── Location aliases for flexible matching ─────────────────────────────────

LOCATION_ALIASES = {
    "bangalore": ["bangalore", "bengaluru"],
    "bengaluru": ["bangalore", "bengaluru"],
    "mumbai": ["mumbai", "bombay"],
    "bombay": ["mumbai", "bombay"],
    "chennai": ["chennai", "madras"],
    "madras": ["chennai", "madras"],
    "delhi": ["delhi", "new delhi", "delhi ncr", "ncr", "gurgaon", "gurugram", "noida"],
    "new delhi": ["delhi", "new delhi", "delhi ncr", "ncr", "gurgaon", "gurugram", "noida"],
    "delhi ncr": ["delhi", "new delhi", "delhi ncr", "ncr", "gurgaon", "gurugram", "noida"],
    "ncr": ["delhi", "new delhi", "delhi ncr", "ncr", "gurgaon", "gurugram", "noida"],
    "gurgaon": ["delhi", "new delhi", "delhi ncr", "ncr", "gurgaon", "gurugram", "noida"],
    "gurugram": ["delhi", "new delhi", "delhi ncr", "ncr", "gurgaon", "gurugram", "noida"],
    "noida": ["delhi", "new delhi", "delhi ncr", "ncr", "gurgaon", "gurugram", "noida"],
    "hyderabad": ["hyderabad", "secunderabad"],
    "kolkata": ["kolkata", "calcutta"],
    "pune": ["pune", "puna"],
    "remote": ["remote", "remote - india", "india remote", "work from home"],
    "remote - india": ["remote", "remote - india", "india remote"],
    "sf": ["san francisco", "sf", "bay area"],
    "san francisco": ["san francisco", "sf", "bay area"],
    "bay area": ["san francisco", "sf", "bay area"],
    "nyc": ["new york", "nyc", "new york city"],
    "new york": ["new york", "nyc", "new york city"],
}

# ─── Skill aliases for canonical matching ───────────────────────────────────

SKILL_ALIASES = {
    "sql": ["sql", "mysql", "postgresql", "postgres", "psql", "sqlite"],
    "postgres": ["postgresql", "postgres", "psql"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "psql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql", "sql"],
    "react": ["react", "react.js", "reactjs"],
    "react.js": ["react", "react.js", "reactjs"],
    "reactjs": ["react", "react.js", "reactjs"],
    "node": ["node", "node.js", "nodejs"],
    "node.js": ["node", "node.js", "nodejs"],
    "nodejs": ["node", "node.js", "nodejs"],
    "next": ["next", "next.js", "nextjs"],
    "next.js": ["next", "next.js", "nextjs"],
    "nextjs": ["next", "next.js", "nextjs"],
    "golang": ["go", "golang"],
    "go": ["go", "golang"],
    "rds": ["rds", "aws rds", "amazon rds"],
    "aws rds": ["rds", "aws rds", "amazon rds"],
    "amazon rds": ["rds", "aws rds", "amazon rds"],
    "vector db": ["vector dbs", "vector db", "vectordb", "vector database", "vector databases"],
    "vector dbs": ["vector dbs", "vector db", "vectordb", "vector database", "vector databases"],
    "vectordb": ["vector dbs", "vector db", "vectordb", "vector database", "vector databases"],
    "llm": ["llms", "llm", "large language model", "large language models"],
    "llms": ["llms", "llm", "large language model", "large language models"],
    "k8s": ["kubernetes", "k8s"],
    "kubernetes": ["kubernetes", "k8s"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "google cloud": ["gcp", "google cloud", "google cloud platform"],
    "typescript": ["typescript", "ts"],
    "ts": ["typescript", "ts"],
    "javascript": ["javascript", "js"],
    "js": ["javascript", "js"],
}

GENERIC_TITLE_WORDS = {
    "engineer", "engineering", "developer", "senior", "lead", "junior", "staff", "principal", "dev"
}

TITLE_SYNONYMS = {
    "developer": ["developer", "engineer", "engineering", "dev"],
    "engineer": ["developer", "engineer", "engineering", "dev"],
    "dev": ["developer", "engineer", "engineering", "dev"],
    "fullstack": ["full stack", "fullstack"],
    "full stack": ["full stack", "fullstack"],
    "frontend": ["front end", "frontend"],
    "front end": ["front end", "frontend"],
    "backend": ["back end", "backend"],
    "back end": ["back end", "backend"],
}


def load_profiles() -> list[CandidateProfile]:
    """Load candidate profiles from the JSON file without modifying it."""
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "data", "profiles.json"),
        os.path.join(os.path.dirname(__file__), "..", "profiles.json"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [CandidateProfile(**p) for p in data]
    
    raise FileNotFoundError(f"profiles.json not found. Tried: {possible_paths}")


# ─── Normalization Helpers ──────────────────────────────────────────────────

def _normalize_str(s: Any) -> str:
    """Normalize string by lowercasing, stripping, and collapsing whitespace."""
    if s is None:
        return ""
    return " ".join(str(s).lower().replace("-", " ").replace("_", " ").split())


def _normalize_skill(s: Any) -> str:
    """Normalize skill name handling hyphens and underscores."""
    if not s:
        return ""
    return " ".join(str(s).lower().replace("-", " ").replace("_", " ").split())


def _normalize_company_type(t: Any) -> str:
    """Normalize company type handling plurals and CompanyType enum."""
    if not t:
        return ""
    val = t.value if hasattr(t, "value") else str(t)
    cleaned = val.lower().strip()
    if cleaned.endswith("s") and cleaned[:-1] in {"startup", "scaleup", "enterprise"}:
        return cleaned[:-1]
    if cleaned == "agencies":
        return "agency"
    return cleaned


# ─── Skill Matching ─────────────────────────────────────────────────────────

def _skill_matches(candidate_skills: Optional[list[str]], required_skill: str) -> bool:
    """
    Check if a candidate has a required skill.
    Handles:
    - empty skills / None (returns False without error)
    - case differences & whitespace differences
    - canonical aliases (e.g. 'RDS' <-> 'AWS RDS', 'Go' <-> 'Golang')
    - prevents false positives (e.g., 'Go' in 'Django', 'Java' in 'JavaScript')
    """
    if not required_skill or not required_skill.strip():
        return True
    if not candidate_skills:
        return False

    req_norm = _normalize_skill(required_skill)
    if not req_norm:
        return True

    # Build alias set for required skill
    req_aliases = set(SKILL_ALIASES.get(req_norm, [req_norm]))
    req_aliases.add(req_norm)
    if req_norm.endswith(".js"):
        req_aliases.add(req_norm[:-3])
    elif req_norm.endswith("js") and len(req_norm) > 2:
        req_aliases.add(req_norm[:-2])

    for skill in candidate_skills:
        if not skill:
            continue
        skill_norm = _normalize_skill(skill)
        if not skill_norm:
            continue

        skill_aliases = set(SKILL_ALIASES.get(skill_norm, [skill_norm]))
        skill_aliases.add(skill_norm)
        if skill_norm.endswith(".js"):
            skill_aliases.add(skill_norm[:-3])
        elif skill_norm.endswith("js") and len(skill_norm) > 2:
            skill_aliases.add(skill_norm[:-2])

        # Exact normalized match or alias intersection
        if req_aliases & skill_aliases:
            return True

        # Full token / word matching within compound skill names
        skill_words = set(skill_norm.split())
        req_words = set(req_norm.split())

        if req_norm in skill_words:
            return True
        if skill_norm in req_words and len(skill_norm) >= 3:
            return True

    return False


# ─── Experience Matching ────────────────────────────────────────────────────

def _experience_matches(
    years: Optional[int],
    min_yrs: Optional[int],
    max_yrs: Optional[int]
) -> bool:
    """
    Check if candidate's experience falls within the min/max range.
    Handles None and missing values safely.
    """
    exp = 0 if years is None else years
    if min_yrs is not None and exp < min_yrs:
        return False
    if max_yrs is not None and exp > max_yrs:
        return False
    return True


# ─── Location Matching ──────────────────────────────────────────────────────

def _location_matches(
    candidate_location: Optional[str],
    filter_locations: list[str]
) -> bool:
    """
    Check if candidate location matches any filter location.
    Handles case differences, whitespace differences, and aliases.
    """
    if not filter_locations:
        return True  # No location filter = match all
    if not candidate_location or not candidate_location.strip():
        return False

    cand_loc = _normalize_str(candidate_location)
    cand_aliases = set(LOCATION_ALIASES.get(cand_loc, [cand_loc]))
    cand_aliases.add(cand_loc)

    for loc in filter_locations:
        if not loc or not loc.strip():
            continue
        loc_norm = _normalize_str(loc)
        
        # Direct match or substring match
        if cand_loc == loc_norm or loc_norm in cand_loc or cand_loc in loc_norm:
            return True
        
        # Alias match
        filter_aliases = set(LOCATION_ALIASES.get(loc_norm, [loc_norm]))
        filter_aliases.add(loc_norm)

        if cand_aliases & filter_aliases:
            return True
        if any(a in cand_loc for a in filter_aliases):
            return True
        if any(ca in loc_norm for ca in cand_aliases):
            return True

    return False


# ─── Company Matching ───────────────────────────────────────────────────────

def _company_name_matches(
    candidate_company: Optional[str],
    target_company: Optional[str]
) -> bool:
    """
    Check if candidate's company name matches target company name.
    Handles case differences, whitespace differences, and compact names
    (e.g., 'NimbusPay' vs 'Nimbus Pay').
    """
    if not target_company or not target_company.strip():
        return True
    if not candidate_company or not candidate_company.strip():
        return False

    cand_norm = _normalize_str(candidate_company)
    target_norm = _normalize_str(target_company)

    if cand_norm == target_norm:
        return True

    cand_compact = cand_norm.replace(" ", "")
    target_compact = target_norm.replace(" ", "")
    if cand_compact == target_compact:
        return True

    if len(target_norm) >= 4 and (target_norm in cand_norm or cand_norm in target_norm):
        return True

    return False


def _current_company_matches(
    profile: CandidateProfile,
    target_company: Optional[str]
) -> bool:
    """Check if candidate's current company matches target."""
    if not target_company or not target_company.strip():
        return True
    return _company_name_matches(profile.current_company, target_company)


def _past_companies_matches(
    profile: CandidateProfile,
    target_past_companies: list[str]
) -> bool:
    """Check if candidate has worked at any of target past companies."""
    if not target_past_companies:
        return True
    past_list = getattr(profile, "past_companies", []) or []
    if not past_list:
        return False

    for target in target_past_companies:
        if not target or not target.strip():
            continue
        if any(_company_name_matches(p.company, target) for p in past_list):
            return True
    return False


def _general_companies_matches(
    profile: CandidateProfile,
    target_companies: list[str]
) -> bool:
    """Check if candidate has worked at target companies (either current or past)."""
    if not target_companies:
        return True
    
    for target in target_companies:
        if not target or not target.strip():
            continue
        # Check current company
        if _company_name_matches(profile.current_company, target):
            return True
        # Check past companies
        past_list = getattr(profile, "past_companies", []) or []
        if any(_company_name_matches(p.company, target) for p in past_list):
            return True
    return False


def _company_type_matches(
    profile: CandidateProfile,
    general_types: list[Any],
    current_types: Optional[list[Any]] = None,
    past_types: Optional[list[Any]] = None
) -> bool:
    """
    Check company type criteria across current and past roles:
    - current_company_types: candidate's current employer must match
    - past_company_types: candidate must have worked at a matching past company
    - general company_types: candidate worked at matching type either currently or in past
    """
    cand_curr_type = _normalize_company_type(profile.current_company_type)
    past_list = getattr(profile, "past_companies", []) or []
    cand_past_types = {_normalize_company_type(p.company_type) for p in past_list if p.company_type}

    # If specific current_company_types specified
    if current_types:
        norm_curr = {_normalize_company_type(t) for t in current_types if t}
        if norm_curr and cand_curr_type not in norm_curr:
            return False

    # If specific past_company_types specified
    if past_types:
        norm_past = {_normalize_company_type(t) for t in past_types if t}
        if norm_past and not (cand_past_types & norm_past):
            return False

    # If general company_types specified (current or past)
    if general_types:
        norm_gen = {_normalize_company_type(t) for t in general_types if t}
        if norm_gen:
            all_types = cand_past_types | ({cand_curr_type} if cand_curr_type else set())
            if not (all_types & norm_gen):
                return False

    return True


# ─── Title Matching ─────────────────────────────────────────────────────────

def _title_matches(
    profile: CandidateProfile,
    title_keywords: list[str]
) -> bool:
    """Check if candidate's current or past titles match title keywords."""
    if not title_keywords:
        return True

    title_lower = _normalize_str(profile.current_title)
    past_list = getattr(profile, "past_companies", []) or []
    all_titles = [title_lower] + [_normalize_str(p.title) for p in past_list if p.title]

    clean_kws = [
        _normalize_str(k) for k in title_keywords 
        if _normalize_str(k)
    ]
    if not clean_kws:
        return True

    specific_kws = [k for k in clean_kws if k not in GENERIC_TITLE_WORDS]
    kws_to_check = specific_kws if specific_kws else clean_kws

    for keyword in kws_to_check:
        aliases = TITLE_SYNONYMS.get(keyword, [keyword])
        matched_any = False
        for alias in aliases:
            if any(alias in t for t in all_titles):
                matched_any = True
                break
        if matched_any:
            return True

    return False


# ─── Master Filtering Function ──────────────────────────────────────────────

def filter_candidates(
    profiles: list[CandidateProfile],
    filters: ObjectiveFilters
) -> tuple[list[CandidateProfile], list[CandidateProfile]]:
    """
    Apply objective filters to candidate profiles deterministically in Python.
    
    Returns:
        (matched, near_misses)
        - matched: candidates that pass ALL objective filters.
        - near_misses: candidates that fail exactly one filter (for diagnostics/fallback).
    """
    matched: list[CandidateProfile] = []
    near_misses: list[CandidateProfile] = []

    for profile in profiles:
        fails = 0

        # 1. Required skills (candidate must have ALL of them)
        if filters.required_skills:
            missing_skills = [
                s for s in filters.required_skills 
                if not _skill_matches(profile.skills, s)
            ]
            if missing_skills:
                fails += 1

        # 2. Experience range (min and/or max)
        if not _experience_matches(
            profile.years_experience,
            filters.min_years_experience,
            filters.max_years_experience
        ):
            fails += 1

        # 3. Location
        if not _location_matches(profile.location, filters.locations):
            fails += 1

        # 4. Current company
        if filters.current_company:
            if not _current_company_matches(profile, filters.current_company):
                fails += 1

        # 5. Target past companies
        if filters.past_companies:
            if not _past_companies_matches(profile, filters.past_companies):
                fails += 1

        # 6. General target companies (current or past)
        if filters.companies:
            if not _general_companies_matches(profile, filters.companies):
                fails += 1

        # 7. Company types (current, past, or general)
        if not _company_type_matches(
            profile,
            general_types=filters.company_types,
            current_types=filters.current_company_types,
            past_types=filters.past_company_types
        ):
            fails += 1

        # 8. Title keywords
        if not _title_matches(profile, filters.title_keywords):
            fails += 1

        # 9. Exclude skills (must NOT have any of them)
        if filters.exclude_skills:
            has_excluded = any(
                _skill_matches(profile.skills, s) for s in filters.exclude_skills
            )
            if has_excluded:
                fails += 1

        if fails == 0:
            matched.append(profile)
        elif fails == 1:
            near_misses.append(profile)

    return matched, near_misses

