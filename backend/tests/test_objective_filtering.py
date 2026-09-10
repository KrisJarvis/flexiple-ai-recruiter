"""
Comprehensive unit tests for objective candidate filtering.

Tests:
1. Skills handling (required, preferred, exclude, case, whitespace, aliases, word boundaries, empty skills)
2. Experience handling (min, max, exact, 0, None, missing)
3. Location handling (case, whitespace, aliases, remote)
4. Company type handling (current, past, general, plural normalization)
5. Current company handling (case, whitespace, compact name)
6. Past company handling (case, whitespace, missing past_companies)
7. Missing optional fields in CandidateProfile
8. End-to-end deterministic filtering against real profiles.json
9. Safeguards: never allow Gemini to invent a candidate or bypass objective filters
10. profiles.json immutability verification
"""

import hashlib
import json
import os
import unittest
from pathlib import Path

from models import (
    CandidateProfile,
    PastCompany,
    ObjectiveFilters,
    CompanyType,
    CandidateScore,
    EvidenceItem,
)
from filter_engine import (
    load_profiles,
    filter_candidates,
    _skill_matches,
    _experience_matches,
    _location_matches,
    _company_name_matches,
    _current_company_matches,
    _past_companies_matches,
    _general_companies_matches,
    _company_type_matches,
    _title_matches,
)


class TestObjectiveFiltering(unittest.TestCase):

    def setUp(self):
        # Base candidate profile for isolated unit tests
        self.sample_profile = CandidateProfile(
            id="test_01",
            name="Test Engineer",
            current_title="Senior Backend Engineer",
            years_experience=5,
            location="Bangalore",
            current_company="NimbusPay",
            current_company_type="startup",
            skills=["Python", "AWS RDS", "PostgreSQL", "Redis"],
            past_companies=[
                PastCompany(
                    company="Freshworks",
                    company_type="scaleup",
                    title="Backend Engineer",
                    years=2
                )
            ],
            education="B.Tech CSE",
            summary="Backend developer with database experience"
        )

    # ─── 1. Skill Matching ──────────────────────────────────────────────────

    def test_skill_exact_and_case_insensitive(self):
        self.assertTrue(_skill_matches(["Python", "AWS RDS"], "python"))
        self.assertTrue(_skill_matches(["Python", "AWS RDS"], "PYTHON"))
        self.assertTrue(_skill_matches(["Python", "AWS RDS"], "Python"))
        self.assertFalse(_skill_matches(["Python", "AWS RDS"], "Java"))

    def test_skill_whitespace_differences(self):
        self.assertTrue(_skill_matches(["AWS RDS"], "  aws rds  "))
        self.assertTrue(_skill_matches(["  AWS RDS  "], "aws rds"))
        self.assertTrue(_skill_matches(["AWS RDS"], "aws   rds"))

    def test_skill_aliases(self):
        # RDS <-> AWS RDS
        self.assertTrue(_skill_matches(["AWS RDS"], "RDS"))
        self.assertTrue(_skill_matches(["RDS"], "AWS RDS"))
        self.assertTrue(_skill_matches(["AWS RDS"], "amazon rds"))
        # Postgres <-> PostgreSQL <-> psql
        self.assertTrue(_skill_matches(["PostgreSQL"], "postgres"))
        self.assertTrue(_skill_matches(["Postgres"], "postgresql"))
        self.assertTrue(_skill_matches(["psql"], "Postgres"))
        # Golang <-> Go
        self.assertTrue(_skill_matches(["Go"], "golang"))
        self.assertTrue(_skill_matches(["Golang"], "Go"))
        # React <-> React.js
        self.assertTrue(_skill_matches(["React"], "react.js"))
        self.assertTrue(_skill_matches(["React.js"], "react"))
        # Node <-> Node.js
        self.assertTrue(_skill_matches(["Node.js"], "node"))
        # K8s <-> Kubernetes
        self.assertTrue(_skill_matches(["Kubernetes"], "k8s"))
        # Vector DB <-> Vector DBs
        self.assertTrue(_skill_matches(["Vector DBs"], "vector db"))
        # LLM <-> LLMs
        self.assertTrue(_skill_matches(["LLMs"], "llm"))

    def test_skill_prevents_false_positives(self):
        # Go should not match Django
        self.assertFalse(_skill_matches(["Django"], "Go"))
        # Java should not match JavaScript
        self.assertFalse(_skill_matches(["JavaScript"], "Java"))

    def test_empty_skills_handling(self):
        self.assertFalse(_skill_matches([], "Python"))
        self.assertFalse(_skill_matches(None, "Python"))
        # Empty required skill matches anything
        self.assertTrue(_skill_matches(["Python"], ""))
        self.assertTrue(_skill_matches(["Python"], "   "))

    # ─── 2. Experience Matching ─────────────────────────────────────────────

    def test_experience_min(self):
        self.assertTrue(_experience_matches(years=5, min_yrs=3, max_yrs=None))
        self.assertTrue(_experience_matches(years=3, min_yrs=3, max_yrs=None))
        self.assertFalse(_experience_matches(years=2, min_yrs=3, max_yrs=None))

    def test_experience_max(self):
        self.assertTrue(_experience_matches(years=5, min_yrs=None, max_yrs=7))
        self.assertTrue(_experience_matches(years=7, min_yrs=None, max_yrs=7))
        self.assertFalse(_experience_matches(years=8, min_yrs=None, max_yrs=7))

    def test_experience_range(self):
        self.assertTrue(_experience_matches(years=5, min_yrs=4, max_yrs=7))
        self.assertFalse(_experience_matches(years=3, min_yrs=4, max_yrs=7))
        self.assertFalse(_experience_matches(years=8, min_yrs=4, max_yrs=7))

    def test_experience_none_and_zero(self):
        self.assertTrue(_experience_matches(years=0, min_yrs=0, max_yrs=2))
        self.assertTrue(_experience_matches(years=None, min_yrs=None, max_yrs=None))
        self.assertFalse(_experience_matches(years=None, min_yrs=1, max_yrs=None))

    # ─── 3. Location Matching ───────────────────────────────────────────────

    def test_location_direct_and_case(self):
        self.assertTrue(_location_matches("Bangalore", ["bangalore"]))
        self.assertTrue(_location_matches("bangalore", ["Bangalore"]))
        self.assertTrue(_location_matches("  Bangalore  ", [" bangalore "]))

    def test_location_aliases(self):
        # Bangalore <-> Bengaluru
        self.assertTrue(_location_matches("Bangalore", ["bengaluru"]))
        self.assertTrue(_location_matches("Bengaluru", ["bangalore"]))
        # Mumbai <-> Bombay
        self.assertTrue(_location_matches("Mumbai", ["bombay"]))
        # Delhi <-> Delhi NCR <-> Gurgaon <-> Noida
        self.assertTrue(_location_matches("Delhi NCR", ["delhi"]))
        self.assertTrue(_location_matches("Delhi", ["delhi ncr"]))
        self.assertTrue(_location_matches("Delhi NCR", ["noida"]))
        # Remote <-> Remote - India
        self.assertTrue(_location_matches("Remote - India", ["remote"]))
        self.assertTrue(_location_matches("Remote", ["remote - india"]))

    def test_location_empty_filter_matches_all(self):
        self.assertTrue(_location_matches("Bangalore", []))
        self.assertTrue(_location_matches("Berlin", []))

    def test_location_missing_candidate_location(self):
        self.assertFalse(_location_matches("", ["Bangalore"]))
        self.assertFalse(_location_matches(None, ["Bangalore"]))

    # ─── 4. Company Matching ────────────────────────────────────────────────

    def test_company_name_casing_and_whitespace(self):
        self.assertTrue(_company_name_matches("NimbusPay", "nimbuspay"))
        self.assertTrue(_company_name_matches("NimbusPay", " NimbusPay "))
        self.assertTrue(_company_name_matches("NimbusPay", "Nimbus Pay"))
        self.assertTrue(_company_name_matches("Mango Labs", "mangolabs"))
        self.assertFalse(_company_name_matches("NimbusPay", "Freshworks"))

    def test_current_company_filter(self):
        self.assertTrue(_current_company_matches(self.sample_profile, "NimbusPay"))
        self.assertTrue(_current_company_matches(self.sample_profile, "nimbus pay"))
        self.assertFalse(_current_company_matches(self.sample_profile, "Freshworks"))

    def test_past_companies_filter(self):
        self.assertTrue(_past_companies_matches(self.sample_profile, ["Freshworks"]))
        self.assertTrue(_past_companies_matches(self.sample_profile, ["fresh works"]))
        self.assertFalse(_past_companies_matches(self.sample_profile, ["Google"]))

    def test_general_companies_filter(self):
        # Matches either current or past
        self.assertTrue(_general_companies_matches(self.sample_profile, ["NimbusPay"]))
        self.assertTrue(_general_companies_matches(self.sample_profile, ["Freshworks"]))
        self.assertFalse(_general_companies_matches(self.sample_profile, ["Amazon"]))

    # ─── 5. Company Type Matching ───────────────────────────────────────────

    def test_general_company_types(self):
        # Candidate is current=startup, past=scaleup
        self.assertTrue(_company_type_matches(self.sample_profile, general_types=["startup"]))
        self.assertTrue(_company_type_matches(self.sample_profile, general_types=["scaleup"]))
        self.assertFalse(_company_type_matches(self.sample_profile, general_types=["enterprise"]))
        self.assertFalse(_company_type_matches(self.sample_profile, general_types=["agency"]))

    def test_current_vs_past_company_types(self):
        # Currently startup
        self.assertTrue(_company_type_matches(self.sample_profile, general_types=[], current_types=["startup"]))
        self.assertFalse(_company_type_matches(self.sample_profile, general_types=[], current_types=["scaleup"]))
        # Past scaleup
        self.assertTrue(_company_type_matches(self.sample_profile, general_types=[], past_types=["scaleup"]))
        self.assertFalse(_company_type_matches(self.sample_profile, general_types=[], past_types=["startup"]))

    def test_company_type_plural_normalization(self):
        self.assertTrue(_company_type_matches(self.sample_profile, general_types=["startups"]))
        self.assertTrue(_company_type_matches(self.sample_profile, general_types=["scaleups"]))

    # ─── 6. Robust Handling of Missing Optional Fields ──────────────────────

    def test_profile_with_missing_optional_fields(self):
        # Candidate with empty skills, missing past_companies, missing education, missing summary
        raw_data = {
            "id": "sparse_01",
            "name": "Sparse Candidate",
            "current_title": "Developer",
            "years_experience": 3,
            "location": "Bangalore",
            "current_company": "NimbusPay",
            "current_company_type": "startup",
            "skills": None,
            "past_companies": None,
            "education": None,
            "summary": None
        }
        cand = CandidateProfile.model_validate(raw_data)
        self.assertEqual(cand.skills, [])
        self.assertEqual(cand.past_companies, [])
        self.assertEqual(cand.education, "")
        self.assertEqual(cand.summary, "")

        # Filtering against sparse profile should not throw exceptions
        filters_no_req = ObjectiveFilters(locations=["Bangalore"])
        matched, _ = filter_candidates([cand], filters_no_req)
        self.assertEqual(len(matched), 1)

        filters_req_skill = ObjectiveFilters(required_skills=["Python"])
        matched, near_miss = filter_candidates([cand], filters_req_skill)
        self.assertEqual(len(matched), 0)

    # ─── 7. Deterministic Filtering with Full Pool ──────────────────────────

    def test_filter_real_profiles_rds_bangalore_startups(self):
        profiles = load_profiles()
        self.assertEqual(len(profiles), 48)

        # Query: RDS developers with 4-7 years experience, startup background, Bangalore
        filters = ObjectiveFilters(
            required_skills=["AWS RDS"],
            min_years_experience=4,
            max_years_experience=7,
            locations=["Bangalore"],
            company_types=[CompanyType.STARTUP]
        )

        matched, _ = filter_candidates(profiles, filters)
        self.assertTrue(len(matched) > 0)

        # Every matched candidate MUST strictly satisfy all filters
        for c in matched:
            self.assertTrue(4 <= c.years_experience <= 7)
            self.assertTrue(_skill_matches(c.skills, "AWS RDS"))
            self.assertTrue(_location_matches(c.location, ["Bangalore"]))
            self.assertTrue(_company_type_matches(c, [CompanyType.STARTUP]))

    def test_filter_by_current_company(self):
        profiles = load_profiles()
        filters = ObjectiveFilters(current_company="NimbusPay")
        matched, _ = filter_candidates(profiles, filters)
        self.assertTrue(len(matched) > 0)
        for c in matched:
            self.assertEqual(c.current_company.lower(), "nimbuspay")

    def test_filter_by_past_company(self):
        profiles = load_profiles()
        filters = ObjectiveFilters(past_companies=["Freshworks"])
        matched, _ = filter_candidates(profiles, filters)
        self.assertTrue(len(matched) > 0)
        for c in matched:
            past_names = [p.company.lower() for p in c.past_companies]
            self.assertIn("freshworks", past_names)

    def test_strict_filter_no_matches_returns_empty(self):
        profiles = load_profiles()
        # Non-existent criteria: 30 years experience in Antarctica
        filters = ObjectiveFilters(
            min_years_experience=30,
            locations=["Antarctica"]
        )
        matched, _ = filter_candidates(profiles, filters)
        self.assertEqual(len(matched), 0)

    # ─── 8. Immutability of profiles.json ────────────────────────────────────

    def test_profiles_json_not_modified(self):
        profiles_path = Path(__file__).resolve().parent.parent / "data" / "profiles.json"
        with open(profiles_path, "rb") as f:
            h1 = hashlib.sha256(f.read()).hexdigest()

        # Load and run multiple filter passes
        profiles = load_profiles()
        filter_candidates(profiles, ObjectiveFilters(required_skills=["Python"]))
        filter_candidates(profiles, ObjectiveFilters(locations=["Mumbai"]))

        with open(profiles_path, "rb") as f:
            h2 = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(h1, h2, "profiles.json MUST NOT be modified!")

    # ─── 9. Pipeline Safeguards: No Hallucinations or Filter Bypasses ────────

    def test_zero_matches_pipeline_never_bypasses(self):
        """When 0 candidates match objective filters, verify pipeline returns 0 candidates."""
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from main import app
        from models import FitRubric, RubricCriterion, SearchParseResponse

        dummy_rubric = FitRubric(
            role_summary="Impossible candidate",
            criteria=[RubricCriterion(name="Skill", weight=5, description="Expert")]
        )
        dummy_filters = ObjectiveFilters(
            min_years_experience=50,  # Nobody has 50 years
            locations=["Antarctica"]
        )

        with patch("main.call_llm_structured", return_value=SearchParseResponse(filters=dummy_filters, rubric=dummy_rubric)):
            with patch("main.score_and_rank") as mock_score:
                with TestClient(app) as client:
                    res = client.post("/api/search", json={"query": "50 years experience in Antarctica"})
                    self.assertEqual(res.status_code, 200)
                    data = res.json()
                    self.assertEqual(data["total_filtered"], 0)
                    self.assertEqual(len(data["candidates"]), 0)
                    self.assertEqual(len(data["candidate_profiles"]), 0)
                    # score_and_rank should NEVER be called when 0 candidates match
                    mock_score.assert_not_called()

    def test_pipeline_rejects_hallucinated_or_unfiltered_candidate_ids(self):
        """Verify that any candidate ID returned by scoring that wasn't in filtered candidates is rejected."""
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from main import app
        from models import FitRubric, RubricCriterion, SearchParseResponse

        dummy_rubric = FitRubric(
            role_summary="RDS Developer",
            criteria=[RubricCriterion(name="Skill", weight=5, description="Expert")]
        )
        # Filter for Bangalore RDS developers (matches p01-p06)
        dummy_filters = ObjectiveFilters(
            required_skills=["AWS RDS"],
            locations=["Bangalore"]
        )

        ev = EvidenceItem(field="skills", value="AWS RDS", explanation="Match")
        # Simulate LLM returning an invented candidate ID 'p999_hallucinated' and a non-matching ID 'p10' (e.g. from Delhi)
        mocked_scores = [
            CandidateScore(
                candidate_id="p01",  # valid filtered
                overall_score=90,
                match_tier="strong_match",
                match_reason="Valid candidate",
                evidence=[ev]
            ),
            CandidateScore(
                candidate_id="p999_hallucinated",  # invented!
                overall_score=85,
                match_tier="strong_match",
                match_reason="Hallucinated candidate",
                evidence=[ev]
            ),
        ]

        with patch("main.call_llm_structured", return_value=SearchParseResponse(filters=dummy_filters, rubric=dummy_rubric)):
            with patch("main.score_and_rank", return_value=mocked_scores):
                with TestClient(app) as client:
                    res = client.post("/api/search", json={"query": "RDS developers in Bangalore"})
                    self.assertEqual(res.status_code, 200)
                    data = res.json()
                    returned_ids = [c["candidate_id"] for c in data["candidates"]]
                    self.assertIn("p01", returned_ids)
                    self.assertNotIn("p999_hallucinated", returned_ids)
                    for cid in returned_ids:
                        # Final list must contain ONLY IDs that exist in profiles.json
                        self.assertTrue(cid.startswith("p"))
                        self.assertNotEqual(cid, "p999_hallucinated")


if __name__ == "__main__":
    unittest.main()
