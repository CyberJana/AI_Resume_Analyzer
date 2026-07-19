"""Tests for skill extraction and recommendation components."""

from __future__ import annotations

from analyzer.recommendation import RecommendationEngine
from analyzer.skills_extractor import SkillExtractor


def test_skill_extractor_finds_normalized_skills() -> None:
    """Skill aliases should map to canonical normalized skill names."""
    extractor = SkillExtractor()
    text = """
    Built Python 3 applications with Streamlit, scikit-learn, AWS, and PostgreSQL.
    Used GitHub Actions for CI/CD and deployed containerized services with Docker.
    """

    skills = extractor.extract_skills(text)

    assert "python" in skills
    assert "streamlit" in skills
    assert "scikit-learn" in skills
    assert "aws" in skills
    assert "sql" in skills
    assert "docker" in skills
    assert "ci/cd" in skills
    assert "git" in skills


def test_skill_extractor_counts_skill_frequency() -> None:
    """Repeated skill mentions should be reflected in frequency output."""
    extractor = SkillExtractor()
    text = "Python APIs with Python data pipelines and SQL reporting in Python."

    frequencies = extractor.extract_skill_frequency(text)

    assert frequencies["python"] >= 3
    assert frequencies["sql"] >= 1


def test_skill_comparison_returns_matched_missing_and_additional() -> None:
    """Skill comparison should separate matched, missing, and additional skills."""
    comparison = SkillExtractor.compare_skills(
        resume_skills={"python", "streamlit", "docker"},
        job_skills={"python", "aws", "docker", "sql"},
    )

    assert comparison["matched"] == ["docker", "python"]
    assert comparison["missing"] == ["aws", "sql"]
    assert comparison["additional"] == ["streamlit"]


def test_recommendation_engine_generates_strengths_and_improvements() -> None:
    """Recommendations should reflect missing skills and ATS/similarity gaps."""
    engine = RecommendationEngine()
    result = engine.generate(
        resume_text=(
            "Professional Summary\n"
            "Python developer with analytics experience.\n"
            "Built dashboards and internal tools."
        ),
        resume_skills={"python", "streamlit"},
        job_skills={"python", "streamlit", "sql", "aws", "docker"},
        similarity_score=62.0,
        ats_score=58.0,
    )

    assert result["recommended_skills"] == ["aws", "docker", "sql"]
    assert any("aligns with the role" in item for item in result["strengths"])
    assert any("ATS compatibility" in item for item in result["improvements"])
    assert any("quantified achievements" in item for item in result["improvements"])
