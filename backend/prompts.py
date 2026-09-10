"""
LLM Prompt Templates for the AI Recruiter Sourcing Loop.

These prompts are kept in a dedicated module so they are:
1. Easy to read and evaluate (they are part of the assessment).
2. Easy to iterate on without touching service logic.
3. Clearly separated from application code.

Each prompt function returns a string. The calling code is responsible
for sending it to the LLM and parsing the structured response.
"""


def parse_query_prompt(query: str) -> str:
    """
    PROMPT: Free-text → Structured Filters + Fit Rubric
    
    Given a recruiter's natural language search query, extract:
    - Objective filters (skills, experience range, location, company types, title keywords)
    - A subjective fit rubric (what "good" looks like for this role)
    
    Design decisions:
    - We ask the LLM to distinguish required vs preferred skills so filtering isn't too aggressive.
    - We ask for dealbreakers and positive signals to capture nuance beyond the literal query.
    - Rubric criteria get weights (1-5) so the scoring step can produce meaningful rankings.
    - We explicitly instruct the LLM to infer reasonable defaults when the query is vague
      (e.g., if no experience range is stated, don't set one).
    """
    return f"""You are an expert technical recruiter's AI assistant. A recruiter has typed a free-text search query describing who they're looking for. Your job is to extract two things:

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
\"{query}\"

Respond with valid JSON matching this exact structure:
{{
  "filters": {{
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
  }},
  "rubric": {{
    "role_summary": "...",
    "criteria": [
      {{"name": "...", "weight": <1-5>, "description": "..."}}
    ],
    "dealbreakers": ["..."],
    "positive_signals": ["..."]
  }}
}}

Return ONLY the JSON object, no markdown fencing, no extra text."""


def score_candidates_prompt(rubric_json: str, candidates_json: str) -> str:
    """
    PROMPT: Score filtered candidates against the fit rubric.
    
    Design decisions:
    - We send the full rubric and candidate profiles to the LLM.
    - We require evidence items that cite ACTUAL fields from the profile,
      not generic praise. This is explicitly called out in the assessment.
    - We ask for per-criterion scores so the recruiter can see the breakdown.
    - Match tier thresholds: 70+ strong, 40-69 moderate, <40 weak.
    - The match_reason must reference real details from the candidate's profile.
    """
    return f"""You are scoring candidate profiles against a recruiter's fit rubric. For each candidate, evaluate how well they match and provide an honest, evidence-based assessment.

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
  {{
    "candidate_id": "...",
    "overall_score": <0-100>,
    "match_tier": "...",
    "match_reason": "...",
    "evidence": [{{"field": "...", "value": "...", "explanation": "..."}}],
    "criterion_scores": [{{"criterion_name": "...", "score": <0-10>, "comment": "..."}}]
  }}
]

Sort by overall_score descending. Return ONLY the JSON array, no markdown fencing, no extra text."""


def refine_search_prompt(
    current_filters_json: str,
    current_rubric_json: str,
    shown_candidates_json: str,
    feedback: str,
    thumbs_json: str
) -> str:
    """
    PROMPT: Refine filters and rubric based on recruiter feedback.
    
    Design decisions:
    - We provide the full context: current filters, rubric, shown candidates, and feedback.
    - Thumbs up/down per profile gives structured signal; chat feedback gives nuanced signal.
    - We ask the LLM to explain WHAT it changed and WHY, so the recruiter sees the logic.
    - Changes should be conservative — small adjustments, not wholesale rewrites.
    - The LLM should look at patterns: if all thumbs-down candidates share a trait,
      that trait should become a filter or dealbreaker.
    """
    return f"""You are helping a recruiter refine their candidate search. They've seen some profiles and given feedback. Your job is to adjust the search filters and fit rubric based on their feedback.

CURRENT OBJECTIVE FILTERS:
{current_filters_json}

CURRENT FIT RUBRIC:
{current_rubric_json}

CANDIDATES THAT WERE SHOWN (with candidate_number 1 to N, names, and scores):
{shown_candidates_json}

RECRUITER'S FEEDBACK (natural language):
\"{feedback}\"

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
{{
  "updated_filters": {{ ... same structure as current filters ... }},
  "updated_rubric": {{ ... same structure as current rubric ... }},
  "changes_made": [
    "Changed X because Y",
    "Added Z as a dealbreaker because the recruiter rejected candidates with Z"
  ],
  "reasoning": "Brief overall explanation of the refinement strategy"
}}

Return ONLY the JSON object, no markdown fencing, no extra text."""
