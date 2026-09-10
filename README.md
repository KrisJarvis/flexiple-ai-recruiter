# AI Recruiter — Candidate Sourcing & Refinement Loop

This is my submission for the Flexiple Engineering Challenge. It's a full-stack tool that turns free-text recruiting requests into structured searches, filters real candidate profiles, scores them using Google Gemini, and lets you iteratively refine the shortlist through natural language conversation or thumbs up/down feedback.

---

## Quick Setup

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm**
- A **Google Gemini API Key** (you can grab a free one from [Google AI Studio](https://aistudio.google.com/apikey))

---

### 1. API Key Setup

The backend expects your Gemini API key in an environment variable named:

```bash
GEMINI_API_KEY
```

You can either put it in a `.env` file in the `backend/` folder (recommended), or export it directly in your terminal.

**Using `.env`:**
```bash
cd backend
cp .env.example .env
```
Then open `backend/.env` and paste your key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

*(Optional: you can also set `GEMINI_MODEL=gemini-2.5-flash-lite` if you want to override the default model).*

---

### 2. Run the Backend

```bash
cd backend

# Create & activate a virtual environment
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

The backend runs on `http://localhost:8000`. You can check `http://localhost:8000/api/health` to confirm it sees your API key.

---

### 3. Run the Frontend

Open a second terminal window:

```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173** in your browser. (The Vite dev server automatically proxies `/api` calls to port 8000).

---

### 4. Run the Tests

I wrote 74 unit tests covering the deterministic filtering logic, LLM score validation, multi-key ranking, and error recovery:

```bash
cd backend
python -m unittest discover -s tests -v
```

All 74 tests run in about 0.05 seconds with zero external network calls (LLM responses are mocked for testing).

---

## Decisions: What I Prioritised, What I Cut, and Why

When building an AI recruiting tool, the biggest danger is building a demo that looks flashy but produces untrustworthy results. Here is how I approached the trade-offs:

### What I Prioritised

1. **Deterministic Python filtering (The LLM never touches `profiles.json` directly)**
   - **Why**: LLMs are probabilistic. If you ask an LLM to read 48 candidates and pick the ones with 4–7 years of experience who worked at a startup, it will occasionally hallucinate candidate backgrounds, bend experience limits, or completely invent IDs.
   - **How it works**: Gemini's only job in step 1 is to translate free-text into a clean Pydantic `ObjectiveFilters` model. Pure Python code then filters `profiles.json`. If a candidate doesn't match the hard requirements, they never reach the scoring phase. Python guarantees zero hallucinated candidates, zero skipped filters, and zero mutations to `profiles.json`.

2. **Authoritative Python ranking (Don't trust the LLM's sort order)**
   - **Why**: Gemini is great at evaluating nuanced fit and writing explanations, but terrible at returning reliable, stable sort orders across retries.
   - **How it works**: Gemini scores each candidate from 0–100 and breaks down criteria. But the final ordering is strictly decided by Python using a deterministic multi-key sort: `overall_score DESC`, then `sum of criterion scores DESC`, then `match_tier DESC`, and finally `candidate_id ASC` as a stable tie-breaker.

3. **Strict output validation & recoverable errors**
   - **Why**: Silent failures or broken JSON ruin the recruiter experience.
   - **How it works**: Every LLM response is validated through Pydantic. If Gemini returns invalid scores (e.g. out of 0–100 range), misses a candidate ID, or duplicates one, the system catches it, retries once with the existing client mechanism, and if it still fails, raises a clean recoverable error. Crucially: a failed refinement request returns an HTTP 422 error without erasing the recruiter's active candidate shortlist.

4. **Concrete evidence citations over generic praise**
   - **Why**: Generic AI praise like *"Candidate is a great cultural fit with strong communication"* is useless to a hiring manager.
   - **How it works**: The scoring prompt explicitly forces the model to cite exact profile fields and values (e.g. `field: "skills"`, `value: "AWS RDS"`, `explanation: "Directly matches database requirement"`).

---

### What I Cut

1. **Vector embeddings / Vector databases (Pinecone, Chroma, etc.)**
   - **Why I cut it**: For a local dataset of 48 profiles, vector search is massive overkill that actually hurts precision. Vector similarity often matches on semantic "vibe" and ignores hard constraints (for example, matching a junior with 1 year of experience because their bio mentions "excited about senior architecture"). In-memory deterministic Boolean filtering runs in under 1ms, costs zero dollars, and is 100% accurate.

2. **Complex multi-agent orchestrations / autonomous agent loops**
   - **Why I cut it**: Setting up 3 or 4 autonomous agents debating each other adds 15–20 seconds of latency, burns API tokens, and introduces tons of flaky failure points. A lean, predictable 2-step pipeline (`Parse Query → Python Filter → Score & Rank`) delivers results in 2–3 seconds with predictable quality.

3. **Dynamic code execution / LLM-generated SQL**
   - **Why I cut it**: Letting an LLM generate arbitrary queries or executable code on the fly opens the door to prompt injection and runtime crashes. Having the LLM output a structured JSON schema that maps to tested Python functions is dramatically safer and easier to debug.

4. **Unnecessary UI redesigns**
   - **Why I cut it**: The existing UI layout was already solid, responsive, and easy to use. Instead of spending time redesigning layouts or changing CSS styles, I focused 100% on the core engineering: rock-solid filtering, accurate scoring, tie-breaking, and resilient error recovery.

---

## Where the LLM Prompts Live

All prompts used by the app are kept in a dedicated, readable file in the backend:

📁 **[`backend/prompts.py`](backend/prompts.py)**

I kept them separated from application logic so they are easy to inspect, test, and iterate on:

1. **`parse_query_prompt(query)`**
   - Takes raw recruiter text (e.g., *"RDS developers in Bangalore with 4-7 years experience at startups"*) and extracts:
     - `ObjectiveFilters`: required/preferred skills, experience bounds, location aliases (Bangalore/Bengaluru), company types (startup/scaleup/enterprise/agency), target companies, and title keywords.
     - `FitRubric`: a 1-sentence role summary, 3–5 weighted criteria (1–5 scale), dealbreakers, and positive signals.

2. **`score_candidates_prompt(rubric_json, candidates_json)`**
   - Takes the rubric and the filtered candidates.
   - Evaluates each candidate, assigns an overall score (0–100), per-criterion scores (0–10), and match tier (`strong_match`, `moderate_match`, `weak_match`).
   - Requires concrete evidence items citing actual profile values (skills, previous employers, years).
   - Strict instructions to score only and all passed candidates, with no hallucinated IDs.

3. **`refine_search_prompt(...)`**
   - Takes the current filters, rubric, shown candidates (numbered 1 to N), natural language feedback, and thumbs up/down reactions.
   - Detects patterns (e.g., if the user says *"1 is too junior"*, it inspects candidate #1 and nudges `min_years_experience` up).
   - Returns updated filters, updated rubric, and a list of human-readable `changes_made` explaining what changed and why.

---

## Try These Sample Searches

Here are a few queries that highlight the filtering, scoring, and refinement loop:

1. **Initial Search**:
   > *"RDS developers with 4-7 years of experience who have worked at startups, for a role based in Bangalore"*
   - Watch the AI extract `required_skills: ["RDS"]`, `min_years_experience: 4`, `max_years_experience: 7`, `locations: ["Bangalore", "Bengaluru"]`, and `company_types: ["startup"]`.
   - The candidates shown are filtered deterministically, then scored and ranked.

2. **Refinement Examples**:
   - *"1 is too junior, 2 and 4 are closer to what I want"*
   - *"Location doesn't matter anymore, but they must have Postgres experience"*
   - *"Prefer people from scaleups rather than early startups"*

3. **Freeze**:
   - Once satisfied, hit **Freeze Search** to lock the results and copy a clean summary or download the candidate JSON.
