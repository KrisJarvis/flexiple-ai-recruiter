"""
LLM Service — Google Gemini client wrapper.

Handles:
- API key validation
- Structured JSON output extraction  
- Retries with exponential backoff for transient failures
- Graceful error handling for rate limits, timeouts, and malformed output
- Response cleaning (strips markdown fences, etc.)
"""

import os
import json
import time
import logging
import sys
from typing import Callable, TypeVar, Any
from pathlib import Path
from dotenv import load_dotenv
from pydantic import ValidationError

# Ensure virtual environment site-packages are on sys.path for IDE analyzers and runtimes
_VENV_SITE_PACKAGES = Path(__file__).resolve().parent / ".venv" / "Lib" / "site-packages"
if _VENV_SITE_PACKAGES.exists() and str(_VENV_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(_VENV_SITE_PACKAGES))

from google import genai  # type: ignore
from google.genai import types  # type: ignore

_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ─── Configuration ──────────────────────────────────────────────────────────

MAX_RETRIES = 4
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
FALLBACK_MODELS = [
    MODEL_NAME,
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
]
# Remove duplicates while preserving order
FALLBACK_MODELS = list(dict.fromkeys(FALLBACK_MODELS))


class LLMError(Exception):
    """Raised when the LLM call fails after all retries."""
    pass


class LLMRateLimitError(LLMError):
    """Raised specifically for rate limit errors."""
    pass


class LLMValidationError(LLMError):
    """Raised when the LLM returns output that fails validation."""
    pass


class ScoringError(LLMValidationError, ValueError):
    """Raised when candidate scoring fails validation (missing/duplicate/unknown candidates, invalid score, missing explanation)."""
    def __init__(self, message: str, recoverable: bool = True):
        super().__init__(message)
        self.recoverable = recoverable


def get_client() -> genai.Client:
    """Create a Gemini client. Raises LLMError if API key is missing."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise LLMError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it with your Google Gemini API key."
        )
    return genai.Client(api_key=api_key)


def clean_response(text: str) -> str:
    """Strip markdown code fences and whitespace from LLM response."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def call_llm(prompt: str, temperature: float = 0.3) -> str:
    """
    Call Gemini with retry logic and error handling.
    
    Returns the raw text response (cleaned of markdown fences).
    Raises LLMError, LLMRateLimitError on failure.
    """
    client = get_client()
    last_error = None

    for attempt in range(MAX_RETRIES):
        model_to_use = FALLBACK_MODELS[min(attempt, len(FALLBACK_MODELS) - 1)]
        try:
            response = client.models.generate_content(
                model=model_to_use,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            
            if not response.text:
                raise LLMError("Gemini returned an empty response")
            
            return clean_response(response.text)

        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # Rate limit or Quota exhaustion — signal clearly and switch to fallback model
            if "429" in str(e) or "rate" in error_str or "quota" in error_str:
                if attempt < MAX_RETRIES - 1:
                    next_model = FALLBACK_MODELS[min(attempt + 1, len(FALLBACK_MODELS) - 1)]
                    delay = RETRY_DELAY_BASE ** attempt
                    logger.warning(
                        f"Rate limited or quota exceeded on '{model_to_use}'. "
                        f"Retrying with '{next_model}' in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
                    )
                    time.sleep(delay)
                    continue
                raise LLMRateLimitError(f"Rate limited after {MAX_RETRIES} attempts: {e}")
            
            # Timeout or transient error — retry
            if "timeout" in error_str or "503" in str(e) or "500" in str(e):
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE ** attempt
                    logger.warning(f"Transient error on '{model_to_use}', retrying in {delay}s: {e}")
                    time.sleep(delay)
                    continue
            
            # Non-retryable error
            raise LLMError(f"Gemini API error: {e}")

    raise LLMError(f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}")


def call_llm_json(prompt: str, temperature: float = 0.3) -> dict | list:
    """
    Call Gemini and parse the response as JSON.
    
    Returns parsed JSON (dict or list).
    Raises LLMValidationError if JSON parsing fails.
    """
    raw = call_llm(prompt, temperature)
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}\nRaw: {raw[:500]}")
        raise LLMValidationError(
            f"The LLM returned invalid JSON. This sometimes happens with complex queries. "
            f"Please try again. Parse error: {e}"
        )


def call_llm_structured(
    prompt: str,
    validator_fn: Callable[[Any], T],
    temperature: float = 0.3,
    context_desc: str = "structured output"
) -> T:
    """
    Call Gemini for structured output with validation and 1-time retry.
    
    1. Calls existing LLM mechanism (call_llm_json)
    2. Runs validator_fn to parse and validate against Pydantic model / rules
    3. If malformed or incomplete, retries once using existing LLM mechanism
    4. Validates again
    5. Raises a clean LLMValidationError or ScoringError if still invalid after retry
    """
    last_error_msg = ""
    
    for attempt in range(2):  # 1 initial attempt + 1 retry
        try:
            raw_json = call_llm_json(prompt, temperature=temperature)
            validated_output = validator_fn(raw_json)
            if attempt > 0:
                logger.info(f"Successfully validated {context_desc} on retry attempt {attempt + 1}")
            return validated_output
        except (LLMValidationError, ValidationError, ValueError, KeyError, json.JSONDecodeError) as e:
            last_error_msg = str(e)
            if attempt == 0:
                logger.warning(
                    f"LLM {context_desc} validation failed on attempt 1: {last_error_msg}. "
                    "Retrying once using existing LLM mechanism..."
                )
                continue
            else:
                logger.error(
                    f"LLM {context_desc} validation failed again after retry. Last error: {last_error_msg}"
                )
                if isinstance(e, ScoringError):
                    raise ScoringError(
                        f"Invalid {context_desc} from AI after retry: {last_error_msg}",
                        recoverable=e.recoverable
                    ) from e
                raise LLMValidationError(
                    f"Invalid {context_desc} from AI after retry: {last_error_msg}"
                ) from e

    raise LLMValidationError(
        f"Invalid {context_desc} from AI: {last_error_msg}"
    )
