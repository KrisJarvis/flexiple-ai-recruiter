"""
End-to-end test of the search flow against the FastAPI backend with live Gemini API.
Tests:
1. /api/health
2. /api/search with a real recruiter query
3. /api/refine with recruiter feedback
4. Validates that the returned structured models, candidates, and filters conform to schema
"""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app, ALL_PROFILES, load_profiles

def run_live_test():
    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/api/health")
        print("Health status:", res.status_code, res.json())
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert res.json()["profiles_loaded"] > 0
        assert res.json()["api_key_configured"] is True

        # 2. Search query test
        query = "RDS developers with 4-7 years of experience who have worked at startups, for a role based in Bangalore"
        print(f"\nSubmitting search query: {query}")
        search_res = client.post("/api/search", json={"query": query})
        print("Search status code:", search_res.status_code)
        
        if search_res.status_code != 200:
            print("Search failed with response:", search_res.text)
            sys.exit(1)
        
        data = search_res.json()
        print("\n--- Validated Search Response ---")
        print("Filters:", data["filters"])
        print("Rubric role_summary:", data["rubric"]["role_summary"])
        print("Rubric criteria count:", len(data["rubric"]["criteria"]))
        print("Total filtered:", data["total_filtered"])
        print("Total pool:", data["total_pool"])
        print("Scored candidates count:", len(data["candidates"]))
        
        assert len(data["candidates"]) > 0, "Expected at least 1 scored candidate"
        top_cand = data["candidates"][0]
        print(f"Top candidate: ID={top_cand['candidate_id']}, score={top_cand['overall_score']}, tier={top_cand['match_tier']}")
        print(f"Match reason: {top_cand['match_reason']}")
        print(f"Evidence items count: {len(top_cand['evidence'])}")
        assert 0 <= top_cand["overall_score"] <= 100
        assert len(top_cand["evidence"]) > 0
        
        # 3. Refine test
        print("\nSubmitting refinement...")
        refine_payload = {
            "feedback": "Prefer candidates with more startup experience and strong SQL skills",
            "current_filters": data["filters"],
            "current_rubric": data["rubric"],
            "shown_candidates": data["candidates"],
            "shown_profiles": data["candidate_profiles"],
            "thumbs": {top_cand["candidate_id"]: True}
        }
        refine_res = client.post("/api/refine", json=refine_payload)
        print("Refine status code:", refine_res.status_code)
        
        if refine_res.status_code != 200:
            print("Refine failed with response:", refine_res.text)
            sys.exit(1)
            
        refine_data = refine_res.json()
        print("\n--- Validated Refine Response ---")
        print("Changes made:", refine_data["changes_made"])
        print("Reasoning:", refine_data["reasoning"])
        print("Re-scored candidates count:", len(refine_data["candidates"]))
        assert len(refine_data["changes_made"]) > 0
        assert len(refine_data["candidates"]) > 0
        
        print("\nAll live flow tests PASSED successfully!")

if __name__ == "__main__":
    run_live_test()
