"""Recommendation engine for resume improvement insights."""

from __future__ import annotations

import logging


class RecommendationError(Exception):
    """Raised when recommendation generation fails."""


class RecommendationEngine:
    """Generate strengths, missing skill guidance, and improvement recommendations."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def generate(
        self,
        resume_text: str,
        resume_skills: set[str],
        job_skills: set[str],
        similarity_score: float,
        ats_score: float,
    ) -> dict[str, list[str]]:
        """
        Generate recommendation outputs for the analysis dashboard.

        Args:
            resume_text: Original resume text.
            resume_skills: Skills extracted from the resume.
            job_skills: Skills extracted from the job description.
            similarity_score: Resume-job match score.
            ats_score: ATS compatibility score.

        Returns:
            Dictionary containing strengths, improvements, and recommended skills.
        """
        if not resume_text.strip():
            raise RecommendationError("Resume text cannot be empty for recommendations.")

        matched_skills = sorted(resume_skills & job_skills)
        missing_skills = sorted(job_skills - resume_skills)
        recommended_skills = self._prioritize_missing_skills(missing_skills)

        strengths = self._build_strengths(
            resume_text=resume_text,
            matched_skills=matched_skills,
            similarity_score=similarity_score,
            ats_score=ats_score,
        )
        improvements = self._build_improvements(
            resume_text=resume_text,
            missing_skills=missing_skills,
            similarity_score=similarity_score,
            ats_score=ats_score,
        )

        self.logger.info("Recommendation insights generated successfully.")
        return {
            "strengths": strengths,
            "improvements": improvements,
            "recommended_skills": recommended_skills,
        }

    @staticmethod
    def _prioritize_missing_skills(missing_skills: list[str]) -> list[str]:
        """Return the top missing skills to focus on first."""
        return missing_skills[:10]

    def _build_strengths(
        self,
        resume_text: str,
        matched_skills: list[str],
        similarity_score: float,
        ats_score: float,
    ) -> list[str]:
        """Generate resume strengths from coverage and structure indicators."""
        strengths: list[str] = []

        if matched_skills:
            strengths.append(
                f"The resume already aligns with the role in these areas: {', '.join(matched_skills[:8])}."
            )

        if similarity_score >= 75:
            strengths.append(
                "The resume shows strong semantic alignment with the target job description."
            )
        elif similarity_score >= 60:
            strengths.append(
                "The resume demonstrates moderate alignment with the target role requirements."
            )

        if ats_score >= 75:
            strengths.append(
                "The resume appears reasonably ATS-friendly based on structure, contact details, and keyword coverage."
            )

        if self._contains_quantified_impact(resume_text):
            strengths.append(
                "The resume includes measurable outcomes, which strengthens credibility and impact."
            )

        return strengths

    def _build_improvements(
        self,
        resume_text: str,
        missing_skills: list[str],
        similarity_score: float,
        ats_score: float,
    ) -> list[str]:
        """Generate targeted improvement suggestions."""
        improvements: list[str] = []

        if missing_skills:
            improvements.append(
                "Add or emphasize these missing skills where relevant: "
                f"{', '.join(missing_skills[:10])}."
            )

        if similarity_score < 70:
            improvements.append(
                "Tailor the summary and experience sections more closely to the target role using job-specific language."
            )

        if ats_score < 70:
            improvements.append(
                "Improve ATS compatibility by ensuring standard section headings, clear formatting, and stronger keyword alignment."
            )

        if not self._contains_quantified_impact(resume_text):
            improvements.append(
                "Add quantified achievements such as percentages, revenue impact, delivery speed, or scale metrics."
            )

        if not self._contains_summary_section(resume_text):
            improvements.append(
                "Include a concise professional summary that highlights domain expertise, tools, and target role alignment."
            )

        return improvements

    @staticmethod
    def _contains_quantified_impact(text: str) -> bool:
        """Detect whether the resume contains numeric evidence of impact."""
        return any(character.isdigit() for character in text)

    @staticmethod
    def _contains_summary_section(text: str) -> bool:
        """Detect common professional summary headings."""
        normalized_text = text.lower()
        return any(
            heading in normalized_text
            for heading in ("summary", "professional summary", "profile", "objective")
        )
