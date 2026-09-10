/**
 * API client for the AI Recruiter backend.
 * All LLM calls happen server-side; this just manages HTTP requests.
 */

const API_BASE = '/api';

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });

    if (!res.ok) {
      let detail = '';
      try {
        const body = await res.json();
        detail = body.detail || JSON.stringify(body);
      } catch {
        detail = await res.text();
      }

      if (res.status === 429) {
        throw new ApiError('Rate limited — please wait a moment and try again.', 429, detail);
      }
      if (res.status === 422) {
        throw new ApiError('The AI returned an unexpected format. Please try again.', 422, detail);
      }
      if (res.status === 502) {
        throw new ApiError(detail || 'AI service error. Please check your API key and try again.', 502, detail);
      }
      throw new ApiError(detail || `Request failed (${res.status})`, res.status, detail);
    }

    return await res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new ApiError('Cannot reach the backend server. Is it running on port 8000?', 0, err.message);
    }
    throw new ApiError(err.message || 'Unknown error', 0, err.message);
  }
}

export async function healthCheck() {
  return request('/health');
}

export async function search(query) {
  return request('/search', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
}

export async function refine({ feedback, currentFilters, currentRubric, shownCandidates, shownProfiles, thumbs }) {
  return request('/refine', {
    method: 'POST',
    body: JSON.stringify({
      feedback,
      current_filters: currentFilters,
      current_rubric: currentRubric,
      shown_candidates: shownCandidates,
      shown_profiles: shownProfiles,
      thumbs: thumbs || {},
    }),
  });
}

export async function freeze({ filters, rubric, candidates, candidateProfiles }) {
  return request('/freeze', {
    method: 'POST',
    body: JSON.stringify({
      filters,
      rubric,
      candidates,
      candidate_profiles: candidateProfiles,
    }),
  });
}

export { ApiError };
