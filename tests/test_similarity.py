"""Tests for similarity and ATS scoring components."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from analyzer.ats_score import ATSScorer
from analyzer.similarity_engine import SimilarityEngine, SimilarityEngineError


class _MockSentenceTransformer:
    """Simple deterministic embedding stub for tests."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def encode(
        self,
        texts: list[str],
        normalize_embeddings: bool = True,
    ) -> np.ndarray:
        if "python streamlit sql machine learning" in texts[0]:
            return np.array(
                [
                    [0.90, 0.10, 0.20],
                    [0.88, 0.11, 0.19],
                ]
            )

        return np.array(
            [
                [0.95, 0.02, 0.01],
                [0.05, 0.91, 0.03],
            ]
        )


@patch("analyzer.similarity_engine.SentenceTransformer", _MockSentenceTransformer)
def test_similarity_engine_returns_high_score_for_related_texts() -> None:
    """Related resume and JD content should yield a strong similarity score."""
    engine = SimilarityEngine(model_name="all-MiniLM-L6-v2")

    score = engine.calculate_similarity(
        resume_text="python streamlit sql machine learning dashboards analytics",
        job_description_text="python streamlit sql machine learning engineer role",
    )

    assert 70.0 <= score <= 100.0


@patch("analyzer.similarity_engine.SentenceTransformer", _MockSentenceTransformer)
def test_similarity_engine_returns_lower_score_for_different_texts() -> None:
    """Unrelated texts should produce a lower similarity score."""
    engine = SimilarityEngine(model_name="all-MiniLM-L6-v2")

    score = engine.calculate_similarity(
        resume_text="graphic design branding adobe illustrator photoshop",
        job_description_text="backend python api development docker kubernetes",
    )

    assert 0.0 <= score < 60.0


@patch("analyzer.similarity_engine.SentenceTransformer", _MockSentenceTransformer)
def test_similarity_engine_rejects_empty_resume_text() -> None:
    """Empty resume text should raise a scoring error."""
    engine = SimilarityEngine(model_name="all-MiniLM-L6-v2")

    with pytest.raises(SimilarityEngineError):
        engine.calculate_similarity("", "python backend engineer")


def test_ats_scorer_returns_weighted_breakdown() -> None:
    """ATS scorer should return a bounded total and named factor breakdown."""
    scorer = ATSScorer()
    resume_text = """
    Jane Doe
    jane.doe@example.com
    +1 555 234 5678
    linkedin.com/in/janedoe

    Professional Summary
    Python developer with experience building Streamlit dashboards.

    Experience
    - Built machine learning pipelines
    - Improved reporting automation by 40%

    Education
    Bachelor of Technology

    Technical Skills
    Python, Streamlit, SQL, AWS
    """

    result = scorer.score_resume(
        resume_text=resume_text,
        resume_skills={"python", "streamlit", "sql", "aws"},
        job_skills={"python", "streamlit", "sql", "docker"},
    )

    assert 0.0 <= result["ats_score"] <= 100.0
    assert set(result["breakdown"]) == {
        "keyword_match",
        "section_completeness",
        "contact_information",
        "formatting_readability",
    }
    assert result["breakdown"]["contact_information"] == 100.0
