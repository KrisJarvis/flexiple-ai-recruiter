"""
Unit tests for the candidate scoring and ranking pipeline.

Verifies:
1. Gemini must score only candidates actually passed to it.
2. Gemini must not create/hallucinate candidates.
3. Candidate IDs must be strictly validated.
4. Scores must be within the defined range (0-100 overall, 0-10 criterion).
5. Every candidate must have evidence and explanation.
6. Python must perform final sorting/ranking (never trust Gemini's order blindly).
7. Handle:
   - missing candidate
   - duplicate candidate
   - unknown candidate ID
   - invalid score
   - missing explanation
   - malformed response
8. If scoring fails, return a structured recoverable error.
9. Do not erase previously valid results when a later scoring request fails.
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from models import (
    CandidateProfile, FitRubric, RubricCriterion,
    CandidateScore, EvidenceItem, CriterionScore,
    validate_candidate_scores_batch,
    ObjectiveFilters, SearchRequest, RefineRequest
)
from scoring_engine import score_and_rank, _rank_candidates
from llm_service import ScoringError, LLMValidationError
from main import app


class TestCandidateScoreValidation(unittest.TestCase):
    """Test strict validation of candidate scores returned by LLM."""

    def setUp(self):
        self.expected_ids = {"cand_001", "cand_002", "cand_003"}
        self.valid_score_item = {
            "candidate_id": "cand_001",
            "overall_score": 88,
            "match_tier": "strong_match",
            "match_reason": "Strong background in distributed systems and Go.",
            "evidence": [
                {
                    "field": "skills",
                    "value": "Go, Distributed Systems, Kubernetes",
                    "explanation": "Directly matches core requirements"
                },
                {
                    "field": "years_experience",
                    "value": 6,
                    "explanation": "Exceeds 4-year requirement"
                }
            ],
            "criterion_scores": [
                {
                    "criterion_name": "Technical Depth",
                    "score": 9,
                    "comment": "Deep Go and distributed systems experience"
                },
                {
                    "criterion_name": "Seniority",
                    "score": 8,
                    "comment": "6 years in relevant roles"
                }
            ]
        }

    def test_valid_batch_validation(self):
        """Valid batch of scores for all expected IDs passes validation."""
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001", overall_score=88),
            dict(self.valid_score_item, candidate_id="cand_002", overall_score=75, match_tier="moderate_match"),
            dict(self.valid_score_item, candidate_id="cand_003", overall_score=60, match_tier="weak_match"),
        ]
        validated = validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertEqual(len(validated), 3)
        self.assertEqual({s.candidate_id for s in validated}, self.expected_ids)

    def test_wrapped_dict_format(self):
        """Supports scores wrapped in a dictionary with key 'scores' or 'candidate_scores'."""
        batch_dict = {
            "scores": [
                dict(self.valid_score_item, candidate_id="cand_001"),
                dict(self.valid_score_item, candidate_id="cand_002"),
                dict(self.valid_score_item, candidate_id="cand_003"),
            ]
        }
        validated = validate_candidate_scores_batch(batch_dict, self.expected_ids)
        self.assertEqual(len(validated), 3)

    # ─── Missing Candidate ──────────────────────────────────────────────────
    def test_missing_candidate_raises_scoring_error(self):
        """Missing an expected candidate raises ScoringError."""
        # Only cand_001 and cand_002 returned, cand_003 is missing
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001"),
            dict(self.valid_score_item, candidate_id="cand_002"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("missing", str(ctx.exception).lower())
        self.assertIn("cand_003", str(ctx.exception))

    # ─── Duplicate Candidate ────────────────────────────────────────────────
    def test_duplicate_candidate_raises_scoring_error(self):
        """Duplicate candidate ID in AI scoring output raises ScoringError."""
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001"),
            dict(self.valid_score_item, candidate_id="cand_001"),  # duplicate
            dict(self.valid_score_item, candidate_id="cand_002"),
            dict(self.valid_score_item, candidate_id="cand_003"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("duplicate", str(ctx.exception).lower())
        self.assertIn("cand_001", str(ctx.exception))

    # ─── Unknown Candidate ID (Hallucinated Candidate) ─────────────────────
    def test_unknown_candidate_id_raises_scoring_error(self):
        """Invented candidate ID not in expected set raises ScoringError."""
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001"),
            dict(self.valid_score_item, candidate_id="cand_002"),
            dict(self.valid_score_item, candidate_id="cand_999_hallucinated"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("unknown candidate id", str(ctx.exception).lower())
        self.assertIn("cand_999_hallucinated", str(ctx.exception))

    # ─── Invalid Score Range ───────────────────────────────────────────────
    def test_invalid_overall_score_negative(self):
        """Negative overall score raises ScoringError."""
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001", overall_score=-5),
            dict(self.valid_score_item, candidate_id="cand_002"),
            dict(self.valid_score_item, candidate_id="cand_003"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("overall_score", str(ctx.exception))

    def test_invalid_overall_score_above_100(self):
        """Overall score exceeding 100 raises ScoringError."""
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001", overall_score=105),
            dict(self.valid_score_item, candidate_id="cand_002"),
            dict(self.valid_score_item, candidate_id="cand_003"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("overall_score", str(ctx.exception))

    def test_invalid_overall_score_non_numeric(self):
        """Non-numeric overall score raises ScoringError."""
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001", overall_score="top_tier"),
            dict(self.valid_score_item, candidate_id="cand_002"),
            dict(self.valid_score_item, candidate_id="cand_003"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("overall_score", str(ctx.exception))

    def test_invalid_criterion_score_range(self):
        """Criterion score outside 0-10 raises ScoringError."""
        bad_item = dict(self.valid_score_item, candidate_id="cand_001")
        bad_item["criterion_scores"] = [
            {"criterion_name": "Technical Depth", "score": 15, "comment": "Out of range"}
        ]
        batch = [
            bad_item,
            dict(self.valid_score_item, candidate_id="cand_002"),
            dict(self.valid_score_item, candidate_id="cand_003"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("criterion score", str(ctx.exception).lower())

    # ─── Missing Explanation ───────────────────────────────────────────────
    def test_missing_match_reason_raises_scoring_error(self):
        """Missing or empty match_reason explanation raises ScoringError."""
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001", match_reason="   "),
            dict(self.valid_score_item, candidate_id="cand_002"),
            dict(self.valid_score_item, candidate_id="cand_003"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("missing explanation", str(ctx.exception).lower())

    # ─── Missing Evidence ──────────────────────────────────────────────────
    def test_missing_evidence_raises_scoring_error(self):
        """Empty evidence list raises ScoringError."""
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001", evidence=[]),
            dict(self.valid_score_item, candidate_id="cand_002"),
            dict(self.valid_score_item, candidate_id="cand_003"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("missing evidence", str(ctx.exception).lower())

    def test_empty_evidence_field_or_explanation_raises_scoring_error(self):
        """Evidence item with empty field or explanation raises ScoringError."""
        bad_ev = [
            {"field": "", "value": "Go", "explanation": "Valid explanation"}
        ]
        batch = [
            dict(self.valid_score_item, candidate_id="cand_001", evidence=bad_ev),
            dict(self.valid_score_item, candidate_id="cand_002"),
            dict(self.valid_score_item, candidate_id="cand_003"),
        ]
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(batch, self.expected_ids)
        self.assertIn("field", str(ctx.exception).lower())

    # ─── Malformed Response ────────────────────────────────────────────────
    def test_malformed_response_none(self):
        """None/null response raises ScoringError."""
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch(None, self.expected_ids)
        self.assertIn("malformed response", str(ctx.exception).lower())

    def test_malformed_response_string(self):
        """String response raises ScoringError."""
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch("Here are your scored candidates", self.expected_ids)
        self.assertIn("malformed response", str(ctx.exception).lower())

    def test_malformed_response_dict_without_candidates(self):
        """Dict lacking candidate array raises ScoringError."""
        with self.assertRaises(ScoringError) as ctx:
            validate_candidate_scores_batch({"status": "success"}, self.expected_ids)
        self.assertIn("malformed response", str(ctx.exception).lower())


class TestPythonAuthoritativeRanking(unittest.TestCase):
    """Test deterministic Python ranking without trusting Gemini's ordering."""

    def _make_score(self, cid: str, score: int, tier: str, crit_scores: list[int] | None = None) -> CandidateScore:
        c_scores = []
        if crit_scores:
            for idx, cs in enumerate(crit_scores):
                c_scores.append(CriterionScore(
                    criterion_name=f"Crit {idx+1}",
                    score=cs,
                    comment="Valid comment"
                ))
        return CandidateScore(
            candidate_id=cid,
            overall_score=score,
            match_tier=tier,
            match_reason="Valid explanation of fit.",
            evidence=[
                EvidenceItem(field="skills", value="Python", explanation="Direct match")
            ],
            criterion_scores=c_scores
        )

    def test_python_ranks_by_overall_score_descending(self):
        """Gemini returning candidates in reverse or shuffled order is reordered by Python."""
        # Low score first, high score last
        input_scores = [
            self._make_score("cand_low", 45, "weak_match"),
            self._make_score("cand_mid", 75, "moderate_match"),
            self._make_score("cand_high", 95, "strong_match"),
        ]
        ranked = _rank_candidates(input_scores)
        ranked_ids = [s.candidate_id for s in ranked]
        self.assertEqual(ranked_ids, ["cand_high", "cand_mid", "cand_low"])
        self.assertEqual([s.overall_score for s in ranked], [95, 75, 45])

    def test_tie_breaking_by_criterion_sum(self):
        """When overall_score is identical, rank by sum of criterion scores descending."""
        # Both overall_score 85, but cand_crit_high has 9+9=18, cand_crit_low has 7+7=14
        input_scores = [
            self._make_score("cand_crit_low", 85, "strong_match", crit_scores=[7, 7]),
            self._make_score("cand_crit_high", 85, "strong_match", crit_scores=[9, 9]),
        ]
        ranked = _rank_candidates(input_scores)
        self.assertEqual([s.candidate_id for s in ranked], ["cand_crit_high", "cand_crit_low"])

    def test_tie_breaking_by_tier_weight(self):
        """When overall_score and criterion_sum are identical, rank by match_tier weight."""
        input_scores = [
            self._make_score("cand_mod", 80, "moderate_match", crit_scores=[8, 8]),
            self._make_score("cand_strong", 80, "strong_match", crit_scores=[8, 8]),
        ]
        ranked = _rank_candidates(input_scores)
        self.assertEqual([s.candidate_id for s in ranked], ["cand_strong", "cand_mod"])

    def test_tie_breaking_by_candidate_id_deterministic(self):
        """When all scores and tiers match, tie-break deterministically by candidate_id ascending."""
        input_scores = [
            self._make_score("cand_z", 80, "strong_match", crit_scores=[8, 8]),
            self._make_score("cand_a", 80, "strong_match", crit_scores=[8, 8]),
            self._make_score("cand_m", 80, "strong_match", crit_scores=[8, 8]),
        ]
        ranked = _rank_candidates(input_scores)
        self.assertEqual([s.candidate_id for s in ranked], ["cand_a", "cand_m", "cand_z"])


class TestScoreAndRankIntegration(unittest.TestCase):
    """Test score_and_rank function with candidate filtering and validation."""

    def setUp(self):
        self.candidates = [
            CandidateProfile(
                id="cand_1",
                name="Alice Dev",
                current_title="Senior Backend Engineer",
                years_experience=6,
                location="San Francisco, CA",
                skills=["Python", "Go", "PostgreSQL"]
            ),
            CandidateProfile(
                id="cand_2",
                name="Bob Eng",
                current_title="Backend Engineer",
                years_experience=4,
                location="Remote",
                skills=["Python", "Django", "MySQL"]
            ),
        ]
        self.rubric = FitRubric(
            role_summary="Backend Engineer with solid Python experience",
            criteria=[
                RubricCriterion(name="Python Depth", description="Experience with Python backend", weight=5)
            ]
        )

    def test_empty_candidates_returns_empty_list(self):
        """Empty input candidate list returns [] without calling LLM."""
        res = score_and_rank([], self.rubric)
        self.assertEqual(res, [])

    @patch("scoring_engine.call_llm_structured")
    def test_score_and_rank_success(self, mock_llm):
        """score_and_rank calls LLM for filtered candidates and returns ranked results."""
        mock_llm.return_value = [
            CandidateScore(
                candidate_id="cand_2",
                overall_score=75,
                match_tier="moderate_match",
                match_reason="Good Python background",
                evidence=[EvidenceItem(field="skills", value="Python", explanation="Core fit")],
                criterion_scores=[CriterionScore(criterion_name="Python Depth", score=7, comment="Solid")]
            ),
            CandidateScore(
                candidate_id="cand_1",
                overall_score=92,
                match_tier="strong_match",
                match_reason="Senior Python and Go expert",
                evidence=[EvidenceItem(field="skills", value="Python, Go", explanation="Extensive fit")],
                criterion_scores=[CriterionScore(criterion_name="Python Depth", score=9, comment="Exceptional")]
            ),
        ]
        results = score_and_rank(self.candidates, self.rubric, top_n=5)
        # Even though LLM returned cand_2 first, Python ranking must put cand_1 first (92 > 75)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].candidate_id, "cand_1")
        self.assertEqual(results[1].candidate_id, "cand_2")
        self.assertEqual(results[0].overall_score, 92)


class TestStructuredRecoverableError(unittest.TestCase):
    """Test API error handling: structured recoverable error and state preservation."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("main.filter_candidates")
    @patch("main.score_and_rank")
    @patch("main.call_llm_structured")
    def test_search_scoring_error_returns_structured_recoverable_response(
        self, mock_parse, mock_score, mock_filter
    ):
        """When scoring fails during search, API returns HTTP 422 with structured recoverable error."""
        from models import SearchParseResponse
        mock_parse.return_value = SearchParseResponse(
            filters=ObjectiveFilters(),
            rubric=FitRubric(
                role_summary="Test role",
                criteria=[RubricCriterion(name="Fit", description="Role fit", weight=3)]
            )
        )
        mock_filter.return_value = ([
            CandidateProfile(id="cand_1", name="Alice", skills=["Python"])
        ], [])
        mock_score.side_effect = ScoringError("Unknown candidate ID 'cand_hallucinated' returned by AI")

        resp = self.client.post("/api/search", json={"query": "Senior backend engineer"})
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data.get("error_type"), "scoring_error")
        self.assertTrue(data.get("recoverable"))
        self.assertIn("scoring failed", data.get("detail", "").lower())

    @patch("main.refine_search")
    @patch("main.filter_candidates")
    @patch("main.score_and_rank")
    def test_refine_scoring_error_preserves_previous_state(
        self, mock_score, mock_filter, mock_refine
    ):
        """When scoring fails during refine, previously valid candidate shortlist and filters are preserved."""
        from models import RefinementResult
        prev_candidate = {
            "candidate_id": "cand_prev",
            "overall_score": 85,
            "match_tier": "strong_match",
            "match_reason": "Previously matched well",
            "evidence": [{"field": "skills", "value": "Python", "explanation": "Prior match"}],
            "criterion_scores": []
        }
        prev_profile = {
            "id": "cand_prev",
            "name": "Jane Prior",
            "current_title": "Backend Engineer",
            "years_experience": 5,
            "location": "New York, NY",
            "current_company": "TechCorp",
            "current_company_type": "Product",
            "skills": ["Python"],
            "past_companies": [],
            "education": "",
            "summary": ""
        }

        mock_refine.return_value = RefinementResult(
            updated_filters=ObjectiveFilters(skills=["Python"]),
            updated_rubric=FitRubric(
                role_summary="Backend Engineer",
                criteria=[RubricCriterion(name="Python", description="Python fit", weight=5)]
            ),
            changes_made=["Prioritized Python"],
            reasoning="Refined based on user thumbs up"
        )
        mock_filter.return_value = ([
            CandidateProfile.model_validate(prev_profile)
        ], [])
        # Scoring fails with ScoringError
        mock_score.side_effect = ScoringError("Malformed response: AI returned empty scoring array")

        payload = {
            "feedback": "More senior candidates",
            "current_filters": {"skills": ["Python"]},
            "current_rubric": {
                "role_summary": "Backend Engineer",
                "criteria": [{"name": "Python", "description": "Python fit", "weight": 5}],
                "dealbreakers": [],
                "positive_signals": []
            },
            "shown_candidates": [prev_candidate],
            "shown_profiles": [prev_profile],
            "thumbs": {"cand_prev": True}
        }

        resp = self.client.post("/api/refine", json=payload)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()

        # Check structured recoverable error fields
        self.assertEqual(data.get("error_type"), "scoring_error")
        self.assertTrue(data.get("recoverable"))
        self.assertIn("preserved", data.get("detail", "").lower())

        # Crucial: Previously valid results MUST NOT be erased!
        self.assertIn("preserved_candidates", data)
        self.assertEqual(len(data["preserved_candidates"]), 1)
        self.assertEqual(data["preserved_candidates"][0]["candidate_id"], "cand_prev")

        self.assertIn("preserved_profiles", data)
        self.assertEqual(len(data["preserved_profiles"]), 1)
        self.assertEqual(data["preserved_profiles"][0]["id"], "cand_prev")

        self.assertIn("preserved_filters", data)
        self.assertIn("preserved_rubric", data)


if __name__ == "__main__":
    unittest.main()
