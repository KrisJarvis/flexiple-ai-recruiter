# LLM Prompts — AI Recruiter Sourcing & Refinement Loop

This document outlines all prompt templates used across the application.

In the codebase, these prompts live in:  
📁 **[`backend/prompts.py`](backend/prompts.py)**

---

## Architecture Overview

The system uses three specialized prompts to power the sourcing loop:

```
[ Recruiter Free-Text Query ]
              │
              ▼
   1. Query Parsing Prompt (parse_query_prompt)
              │
              ├─► Objective Filters ──► [ Deterministic Python Filtering ]
              │                                      │
              └─► Fit Rubric                         ▼
                        │                   [ Filtered Candidates ]
                        │                            │
                        └─────────────┬──────────────┘
                                      │
                                      ▼
                        2. Scoring Prompt (score_candidates_prompt)
                                      │
                                      ▼
                        [ Scored Candidates + Citations ]
                                      │
                                      ▼
                        [ Python Authoritative Ranking ]
                                      │
                                      ▼
   3. Refinement Prompt (refine_search_prompt) ◄── [ Recruiter Feedback / Thumbs ]
```

---

## 1. Query Parsing Prompt (`parse_query_prompt`)

- **File**: `backend/prompts.py`
- **Function**: `parse_query_prompt(query: str) -> str`
- **Role**: Takes raw natural language from the recruiter and translates it into two clean, structured outputs:
  1. **Objective Filters**: Deterministic parameters to filter `profiles.json` in Python (`required_skills`, `min_years_experience`, `max_years_experience`, `locations`, `company_types`, `current_company`, `past_companies`, `title_keywords`).
  2. **Fit Rubric**: A subjective scoring rubric with a role summary, 3–5 weighted criteria (1–5 scale), dealbreakers, and positive signals.

### Prompt Template

```
You are an expert technical recruiter's AI assistant. A recruiter has typed a free-text search query describing who they're looking for. Your job is to extract two things:

1. **Objective Filters** — structured, deterministic criteria to filter a candidate database:
   - `required_skills`: Skills the candidate MUST have. Only include skills explicitly mentioned or very strongly implied. Be specific (e.g., "AWS RDS" not just "AWS").
   - `preferred_skills`: Skills that would be nice to have but aren't dealbreakers.
   - `min_years_experience`: Minimum years of experience (null if not specified).
   - `max_years_experience`: Maximum years of experience (null if not specified).
   - `locations`: Preferred locations. Include common aliases (e.g., both "Bangalore" and "Bengaluru").
   - `company_types`: What kind of companies the candidate should have worked at (current or past). Valid values: "startup", "scaleup", "enterprise", "agency". Only include if mentioned.
   - `current_company`: Specific company name if recruiter explicitly requires the candidate to currently work there (null if not specified).
   - `companies`: Target companies (current or past) if recruiter mentions companies without specifying current vs past (empty array if not specified).
   - `past_companies`: Target past company names if recruiter explicitly mentions past employers or ex-employees (e.g. "ex-Freshworks") (empty array if not specified).
   - `current_company_types`: If recruiter specifically specifies current company type (e.g. "currently at a startup") (empty array if not specified).
   - `past_company_types`: If recruiter specifically specifies past company type (e.g. "worked at a scaleup in the past") (empty array if not specified).
   - `title_keywords`: Keywords to match against job titles (e.g., "backend", "frontend", "fullstack").
   - `exclude_skills`: Skills to explicitly exclude (only if the query mentions exclusions).

2. **Subjective Fit Rubric** — what "good" looks like beyond the literal filters:
   - `role_summary`: A one-line summary of the ideal candidate profile.
   - `criteria`: 3-5 scoring criteria, each with:
     - `name`: Short name (e.g., "Domain Expertise", "Startup DNA")
     - `weight`: Importance from 1 (nice-to-have) to 5 (critical)
     - `description`: What good looks like for this criterion — be specific to this role.
   - `dealbreakers`: Things that would automatically disqualify a candidate (only if inferable from the query).
   - `positive_signals`: Strong indicators that a candidate is a great fit.

IMPORTANT RULES:
- Only extract what's in the query or strongly implied. Don't hallucinate requirements.
- If the query doesn't mention experience range, set min/max to null.
- If the query doesn't mention company types, leave the array empty.
- Be generous with skill matching — "RDS" should match "AWS RDS", "Amazon RDS", etc.
- Think about what the recruiter REALLY wants, not just the literal words.

RECRUITER'S QUERY:
"{query}"

Respond with valid JSON matching this exact structure:
{
  "filters": {
    "required_skills": ["..."],
    "preferred_skills": ["..."],
    "min_years_experience": <number or null>,
    "max_years_experience": <number or null>,
    "locations": ["..."],
    "company_types": ["..."],
    "current_company": <string or null>,
    "companies": ["..."],
    "past_companies": ["..."],
    "current_company_types": ["..."],
    "past_company_types": ["..."],
    "title_keywords": ["..."],
    "exclude_skills": ["..."]
  },
  "rubric": {
    "role_summary": "...",
    "criteria": [
      {"name": "...", "weight": <1-5>, "description": "..."}
    ],
    "dealbreakers": ["..."],
    "positive_signals": ["..."]
  }
}

Return ONLY the JSON object, no markdown fencing, no extra text.
```

### Key Design Decisions
- **Separating Required vs Preferred Skills**: Asking for both prevents the deterministic filter from over-filtering when a recruiter says *"Node.js developer, TypeScript is a plus"*.
- **Location Aliasing**: The prompt instructs the LLM to provide aliases (e.g. both `Bangalore` and `Bengaluru`) so string normalization matches candidate profiles reliably.
- **Explicit Range Extraction**: If experience isn't mentioned, the model returns `null` so Python doesn't invent a constraint.

---

## 2. Candidate Scoring Prompt (`score_candidates_prompt`)

- **File**: `backend/prompts.py`
- **Function**: `score_candidates_prompt(rubric_json: str, candidates_json: str) -> str`
- **Role**: Scores the pre-filtered candidates against the generated rubric, assigning overall scores, criterion breakdowns, match tiers, and profile evidence citations.

### Prompt Template

```
You are scoring candidate profiles against a recruiter's fit rubric. For each candidate, evaluate how well they match and provide an honest, evidence-based assessment.

FIT RUBRIC:
{rubric_json}

CANDIDATE PROFILES TO SCORE:
{candidates_json}

For EACH candidate, produce a score object with:
- `candidate_id`: The candidate's ID from the profile.
- `overall_score`: A weighted score from 0-100 based on the rubric criteria weights.
- `match_tier`: "strong_match" (70-100), "moderate_match" (40-69), or "weak_match" (0-39).
- `match_reason`: ONE sentence explaining why this candidate does or doesn't match. MUST cite specific details from their profile (company names, specific skills, years, titles). Do NOT use generic phrases like "strong background" without specifics.
- `evidence`: An array of 2-4 evidence items, each with:
  - `field`: The exact profile field name (e.g., "skills", "years_experience", "current_company", "past_companies", "education", "summary")
  - `value`: The ACTUAL value from the candidate's profile (e.g., "AWS RDS" not "relevant database skills")
  - `explanation`: How this specific value relates to the rubric requirements.
- `criterion_scores`: For each rubric criterion, a score (0-10) with a brief comment.

CRITICAL RULES:
- You must score ONLY and ALL candidates provided in CANDIDATE PROFILES TO SCORE. Do not omit any candidate. Do not invent any candidates or return IDs not in the list. Do not duplicate candidates.
- `overall_score` MUST be an integer between 0 and 100 inclusive.
- Each criterion score MUST be an integer between 0 and 10 inclusive.
- Every candidate MUST have a non-empty `match_reason` and at least 1 valid `evidence` item explaining the score.
- Every evidence item MUST cite a real field and real value from the candidate's profile. Never fabricate data.
- The match_reason MUST mention specific names, skills, or numbers from the profile.
- Be honest about gaps — if a candidate is missing key skills, say so.
- Score relatively: the best candidate should be clearly distinguishable from weaker ones.
- If a candidate triggers a dealbreaker, their score should be very low regardless of other strengths.

Respond with a JSON array of score objects:
[
  {
    "candidate_id": "...",
    "overall_score": <0-100>,
    "match_tier": "...",
    "match_reason": "...",
    "evidence": [{"field": "...", "value": "...", "explanation": "..."}],
    "criterion_scores": [{"criterion_name": "...", "score": <0-10>, "comment": "..."}]
  }
]

Sort by overall_score descending. Return ONLY the JSON array, no markdown fencing, no extra text.
```

### Key Design Decisions
- **Anti-Hallucination Constraints**: Explicitly forbids inventing IDs or dropping candidates. Python validates the response batch against the input IDs.
- **Mandatory Concrete Evidence**: The prompt requires `field` and `value` directly from the candidate's profile, preventing empty praise like "Great candidate".
- **Bounded Integer Scores**: Explicit 0–100 overall score and 0–10 criterion scores simplify Pydantic validation and downstream ranking.

---

## 3. Search Refinement Prompt (`refine_search_prompt`)

- **File**: `backend/prompts.py`
- **Function**: `refine_search_prompt(...) -> str`
- **Role**: Adjusts filters and rubric based on the recruiter's conversation feedback and per-profile thumbs reactions.

### Prompt Template

```
You are helping a recruiter refine their candidate search. They've seen some profiles and given feedback. Your job is to adjust the search filters and fit rubric based on their feedback.

CURRENT OBJECTIVE FILTERS:
{current_filters_json}

CURRENT FIT RUBRIC:
{current_rubric_json}

CANDIDATES THAT WERE SHOWN (with candidate_number 1 to N, names, and scores):
{shown_candidates_json}

RECRUITER'S FEEDBACK (natural language):
"{feedback}"

PER-PROFILE REACTIONS (thumbs up=true, thumbs down=false):
{thumbs_json}

INSTRUCTIONS:
1. Analyze the feedback and thumbs reactions to understand what the recruiter wants MORE of and LESS of.
   NOTE: If the recruiter refers to candidates by number (e.g., "1 is too junior", "candidate 2 and 4 are good"), match them directly to `candidate_number` (1, 2, 3, etc.) or `candidate_name`.
2. Look for PATTERNS in rejected candidates (too junior? wrong skills? wrong company type?) and adjust filters accordingly.
3. Look for PATTERNS in accepted candidates (what do they have in common?) and reinforce those in the rubric.
4. Make CONSERVATIVE adjustments — don't completely rewrite the filters or rubric, just nudge them.
5. Explain every change you make and why. The recruiter needs to understand your reasoning.

WHAT YOU CAN CHANGE:
- Add/remove required or preferred skills
- Adjust experience range
- Add/remove locations
- Add/remove company types (current, past, or general)
- Add/remove current company, target companies, or past companies
- Adjust title keywords
- Modify rubric criteria weights
- Add/remove dealbreakers or positive signals
- Adjust criterion descriptions to be more/less specific

Respond with valid JSON:
{
  "updated_filters": { ... same structure as current filters ... },
  "updated_rubric": { ... same structure as current rubric ... },
  "changes_made": [
    "Changed X because Y",
    "Added Z as a dealbreaker because the recruiter rejected candidates with Z"
  ],
  "reasoning": "Brief overall explanation of the refinement strategy"
}

Return ONLY the JSON object, no markdown fencing, no extra text.
```

### Key Design Decisions
- **Candidate Number Mapping**: When recruiters say *"1 is too junior, 2 and 4 are good"*, candidates are indexed `1..N` so the LLM reliably resolves relative references.
- **Dual Signal Fusion**: Combines binary thumbs up/down with free-form chat feedback.
- **Conservative Changes**: Instructs the LLM to nudge filters rather than wipe out the entire search.
- **Transparency**: Requires a `changes_made` array that the frontend UI surfaces directly to the user so they understand why results shifted.
