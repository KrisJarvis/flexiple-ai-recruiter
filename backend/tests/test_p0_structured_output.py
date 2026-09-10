"""
Unit and integration tests for P0 fixes:
- LLM structured output validation via Pydantic
- Experience min/max, company_type values, score ranges
- Candidate IDs, duplicate candidates, missing candidates
- Retry once on malformed/incomplete output
- Clean structured error on persistent failure
"""

import unittest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from models import (
    CompanyType,
    ObjectiveFilters,
    RubricCriterion,
    FitRubric,
    EvidenceItem,
    CriterionScore,
    CandidateScore,
    validate_candidate_scores_batch,
    RefinementChange,
    RefinementChanges,
    RefinementResponse,
    SearchParseResponse,
)
from llm_service import call_llm, call_llm_structured, LLMValidationError


class TestP0StructuredOutput(unittest.TestCase):

    def test_schema_rejection_falls_back_to_json_mode(self):
        """A model that rejects response_schema still completes the request safely."""
        response = MagicMock()
        response.text = '{"ok": true}'
        client = MagicMock()
        client.models.generate_content.side_effect = [
            Exception("400 INVALID_ARGUMENT: unsupported response schema"),
            response,
        ]

        with patch("llm_service.get_client", return_value=client):
            result = call_llm(
                "Return a JSON object.",
                response_schema={"type": "object"},
            )

        self.assertEqual(result, '{"ok": true}')
        self.assertEqual(client.models.generate_content.call_count, 2)
        first_config = client.models.generate_content.call_args_list[0].kwargs["config"]
        second_config = client.models.generate_content.call_args_list[1].kwargs["config"]
        self.assertIsNotNone(first_config.response_schema)
        self.assertIsNone(second_config.response_schema)

    # ─── 1. ObjectiveFilters Validation ─────────────────────────────────────

    def test_objective_filters_valid(self):
        filters = ObjectiveFilters(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
            min_years_experience=3,
            max_years_experience=7,
            locations=["Bangalore"],
            company_types=["startup", "scaleup"],
            title_keywords=["Backend"],
            exclude_skills=["Java"]
        )
        self.assertEqual(filters.min_years_experience, 3)
        self.assertEqual(filters.max_years_experience, 7)
        self.assertEqual(filters.company_types, [CompanyType.STARTUP, CompanyType.SCALEUP])

    def test_objective_filters_negative_min_experience(self):
        with self.assertRaises(ValidationError) as ctx:
            ObjectiveFilters(min_years_experience=-1)
        self.assertIn("min_years_experience cannot be negative", str(ctx.exception))

    def test_objective_filters_negative_max_experience(self):
        with self.assertRaises(ValidationError) as ctx:
            ObjectiveFilters(max_years_experience=-5)
        self.assertIn("max_years_experience cannot be negative", str(ctx.exception))

    def test_objective_filters_min_greater_than_max(self):
        with self.assertRaises(ValidationError) as ctx:
            ObjectiveFilters(min_years_experience=8, max_years_experience=4)
        self.assertIn("cannot be greater than max_years_experience", str(ctx.exception))

    def test_objective_filters_invalid_company_type(self):
        with self.assertRaises(ValidationError) as ctx:
            ObjectiveFilters(company_types=["government", "startup"])
        self.assertIn("Invalid company_type 'government'", str(ctx.exception))

    # ─── 2. FitRubric & RubricCriterion Validation ──────────────────────────

    def test_rubric_criterion_valid(self):
        crit = RubricCriterion(name="System Design", weight=4, description="Scalable architectures")
        self.assertEqual(crit.weight, 4)

    def test_rubric_criterion_invalid_weight(self):
        with self.assertRaises(ValidationError):
            RubricCriterion.model_validate({"name": "System Design", "weight": 6, "description": "Scalable architectures"})
        with self.assertRaises(ValidationError):
            RubricCriterion.model_validate({"name": "System Design", "weight": 0, "description": "Scalable architectures"})

    def test_rubric_criterion_empty_name_or_desc(self):
        with self.assertRaises(ValidationError):
            RubricCriterion(name="   ", weight=3, description="valid")
        with self.assertRaises(ValidationError):
            RubricCriterion(name="Valid", weight=3, description="")

    def test_fit_rubric_empty_criteria(self):
        with self.assertRaises(ValidationError) as ctx:
            FitRubric(role_summary="Role", criteria=[])
        self.assertIn("criteria", str(ctx.exception))
        self.assertTrue("at least 1 item" in str(ctx.exception) or "criteria cannot be empty" in str(ctx.exception))

    def test_fit_rubric_empty_role_summary(self):
        crit = RubricCriterion(name="Tech", weight=3, description="Desc")
        with self.assertRaises(ValidationError) as ctx:
            FitRubric(role_summary="", criteria=[crit])
        self.assertIn("role_summary", str(ctx.exception))

    # ─── 3. EvidenceItem & CriterionScore & CandidateScore Validation ───────

    def test_evidence_item_valid(self):
        ev = EvidenceItem(field="skills", value=["Python", "Postgres"], explanation="Matches required stack")
        self.assertIn("Python, Postgres", ev.value)

    def test_evidence_item_empty_value(self):
        with self.assertRaises(ValidationError):
            EvidenceItem(field="skills", value="", explanation="Matches required stack")
        with self.assertRaises(ValidationError):
            EvidenceItem(field="skills", value=None, explanation="Matches required stack")

    def test_criterion_score_range(self):
        cs = CriterionScore(criterion_name="Domain", score=8, comment="Strong experience")
        self.assertEqual(cs.score, 8)

        with self.assertRaises(ValidationError):
            CriterionScore.model_validate({"criterion_name": "Domain", "score": 11, "comment": "Too high"})
        with self.assertRaises(ValidationError):
            CriterionScore.model_validate({"criterion_name": "Domain", "score": -1, "comment": "Too low"})

    def test_candidate_score_range(self):
        ev = EvidenceItem(field="skills", value="Python", explanation="Strong match")
        score = CandidateScore(
            candidate_id="c1",
            overall_score=85,
            match_tier="strong_match",
            match_reason="Experienced engineer",
            evidence=[ev]
        )
        self.assertEqual(score.overall_score, 85)

        with self.assertRaises(ValidationError):
            CandidateScore.model_validate({
                "candidate_id": "c1",
                "overall_score": 105,
                "match_tier": "strong_match",
                "match_reason": "Experienced engineer",
                "evidence": [ev.model_dump()]
            })

        with self.assertRaises(ValidationError):
            CandidateScore.model_validate({
                "candidate_id": "c1",
                "overall_score": -5,
                "match_tier": "strong_match",
                "match_reason": "Experienced engineer",
                "evidence": [ev.model_dump()]
            })

    def test_candidate_score_empty_evidence(self):
        with self.assertRaises(ValidationError):
            CandidateScore(
                candidate_id="c1",
                overall_score=85,
                match_tier="strong_match",
                match_reason="Experienced engineer",
                evidence=[]
            )

    def test_candidate_score_invalid_tier(self):
        ev = EvidenceItem(field="skills", value="Python", explanation="Strong match")
        with self.assertRaises(ValidationError):
            CandidateScore(
                candidate_id="c1",
                overall_score=85,
                match_tier="perfect_match",  # invalid tier
                match_reason="Experienced engineer",
                evidence=[ev]
            )

    # ─── 4. Batch Scoring Validation (IDs, Duplicates, Missing) ────────────

    def test_validate_candidate_scores_batch_success(self):
        expected_ids = {"c1", "c2"}
        ev = {"field": "skills", "value": "Python", "explanation": "Direct match"}
        raw_scores = [
            {
                "candidate_id": "c1",
                "overall_score": 85,
                "match_tier": "strong_match",
                "match_reason": "Good match",
                "evidence": [ev],
                "criterion_scores": []
            },
            {
                "candidate_id": "c2",
                "overall_score": 65,
                "match_tier": "moderate_match",
                "match_reason": "Decent match",
                "evidence": [ev],
                "criterion_scores": []
            }
        ]
        validated = validate_candidate_scores_batch(raw_scores, expected_ids)
        self.assertEqual(len(validated), 2)

    def test_validate_candidate_scores_batch_missing(self):
        expected_ids = {"c1", "c2", "c3"}
        ev = {"field": "skills", "value": "Python", "explanation": "Direct match"}
        raw_scores = [
            {
                "candidate_id": "c1",
                "overall_score": 85,
                "match_tier": "strong_match",
                "match_reason": "Good match",
                "evidence": [ev],
                "criterion_scores": []
            }
        ]
        with self.assertRaises(ValueError) as ctx:
            validate_candidate_scores_batch(raw_scores, expected_ids)
        self.assertIn("missing scores for candidates", str(ctx.exception))

    def test_validate_candidate_scores_batch_duplicate(self):
        expected_ids = {"c1", "c2"}
        ev = {"field": "skills", "value": "Python", "explanation": "Direct match"}
        raw_scores = [
            {
                "candidate_id": "c1",
                "overall_score": 85,
                "match_tier": "strong_match",
                "match_reason": "Good match",
                "evidence": [ev],
                "criterion_scores": []
            },
            {
                "candidate_id": "c1",  # duplicate!
                "overall_score": 75,
                "match_tier": "strong_match",
                "match_reason": "Duplicate",
                "evidence": [ev],
                "criterion_scores": []
            }
        ]
        with self.assertRaises(ValueError) as ctx:
            validate_candidate_scores_batch(raw_scores, expected_ids)
        self.assertIn("Duplicate candidate ID", str(ctx.exception))

    def test_validate_candidate_scores_batch_unexpected_id(self):
        expected_ids = {"c1", "c2"}
        ev = {"field": "skills", "value": "Python", "explanation": "Direct match"}
        raw_scores = [
            {
                "candidate_id": "c1",
                "overall_score": 85,
                "match_tier": "strong_match",
                "match_reason": "Good match",
                "evidence": [ev],
                "criterion_scores": []
            },
            {
                "candidate_id": "c999_hallucinated",
                "overall_score": 70,
                "match_tier": "moderate_match",
                "match_reason": "Hallucination",
                "evidence": [ev],
                "criterion_scores": []
            }
        ]
        with self.assertRaises(ValueError) as ctx:
            validate_candidate_scores_batch(raw_scores, expected_ids)
        self.assertIn("not in the expected candidate batch", str(ctx.exception))

    # ─── 5. Refinement Models Validation ────────────────────────────────────

    def test_refinement_models(self):
        filters = ObjectiveFilters(required_skills=["React"])
        crit = RubricCriterion(name="Frontend", weight=5, description="React expertise")
        rubric = FitRubric(role_summary="Frontend Dev", criteria=[crit])

        ref = RefinementResponse(
            updated_filters=filters,
            updated_rubric=rubric,
            changes_made=["Added React as required skill"],
            reasoning="Recruiter requested frontend emphasis"
        )
        self.assertEqual(len(ref.changes_made), 1)

        # Empty changes_made should fail
        with self.assertRaises(ValidationError):
            RefinementResponse(
                updated_filters=filters,
                updated_rubric=rubric,
                changes_made=[],
                reasoning="Valid reasoning"
            )

        # Empty reasoning should fail
        with self.assertRaises(ValidationError):
            RefinementResponse(
                updated_filters=filters,
                updated_rubric=rubric,
                changes_made=["Changed x"],
                reasoning="   "
            )

    # ─── 6. Retry Mechanism (call_llm_structured) ───────────────────────────

    def test_call_llm_structured_retry_success(self):
        """Test that if attempt 1 returns malformed output, it retries and succeeds on attempt 2."""
        call_count = 0

        def mock_call_llm_json(prompt, temperature=0.3):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt returns invalid data (min > max experience)
                return {
                    "filters": {"min_years_experience": 10, "max_years_experience": 2},
                    "rubric": {"role_summary": "Test", "criteria": [{"name": "C", "weight": 3, "description": "D"}]}
                }
            else:
                # Second attempt returns valid data
                return {
                    "filters": {"min_years_experience": 2, "max_years_experience": 10},
                    "rubric": {"role_summary": "Test", "criteria": [{"name": "C", "weight": 3, "description": "D"}]}
                }

        with patch("llm_service.call_llm_json", side_effect=mock_call_llm_json):
            result = call_llm_structured(
                prompt="dummy prompt",
                validator_fn=lambda raw: SearchParseResponse.model_validate(raw),
                context_desc="test retry"
            )

        self.assertEqual(call_count, 2)
        self.assertEqual(result.filters.min_years_experience, 2)
        self.assertEqual(result.filters.max_years_experience, 10)

    def test_call_llm_structured_retry_failure(self):
        """Test that if both attempts fail validation, a clean LLMValidationError is raised."""
        call_count = 0

        def mock_call_llm_json(prompt, temperature=0.3):
            nonlocal call_count
            call_count += 1
            return {
                "filters": {"min_years_experience": 10, "max_years_experience": 2},  # invalid
                "rubric": {"role_summary": "Test", "criteria": []}  # empty criteria
            }

        with patch("llm_service.call_llm_json", side_effect=mock_call_llm_json):
            with self.assertRaises(LLMValidationError) as ctx:
                call_llm_structured(
                    prompt="dummy prompt",
                    validator_fn=lambda raw: SearchParseResponse.model_validate(raw),
                    context_desc="test retry failure"
                )

        self.assertEqual(call_count, 2)
        self.assertIn("Invalid test retry failure from AI after retry", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
