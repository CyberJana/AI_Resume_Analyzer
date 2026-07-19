"""ATS compatibility scoring logic for resumes."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable


class ATSScoreError(Exception):
    """Raised when ATS scoring cannot be completed."""


class ATSScorer:
    """Calculate an ATS-style compatibility score for a resume."""

    SECTION_PATTERNS = {
        "summary": re.compile(r"\b(summary|profile|objective)\b", re.IGNORECASE),
        "experience": re.compile(
            r"\b(experience|employment|work history|professional experience)\b",
            re.IGNORECASE,
        ),
        "education": re.compile(r"\b(education|academic background)\b", re.IGNORECASE),
        "skills": re.compile(r"\b(skills|technical skills|core competencies)\b", re.IGNORECASE),
    }

    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"(\+\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}")
    LINKEDIN_PATTERN = re.compile(r"\blinkedin\.com\b", re.IGNORECASE)

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def score_resume(
        self,
        resume_text: str,
        resume_skills: Iterable[str],
        job_skills: Iterable[str],
    ) -> dict[str, float | dict[str, float]]:
        """
        Compute a weighted ATS compatibility score.

        Args:
            resume_text: Original extracted resume text.
            resume_skills: Skills found in the resume.
            job_skills: Skills expected by the job description.

        Returns:
            Dictionary containing overall ATS score and score breakdown.

        Raises:
            ATSScoreError: If resume text is empty.
        """
        if not resume_text.strip():
            raise ATSScoreError("Resume text cannot be empty for ATS scoring.")

        resume_skills_set = {skill.lower() for skill in resume_skills}
        job_skills_set = {skill.lower() for skill in job_skills}

        breakdown = {
            "keyword_match": self._score_keyword_match(resume_skills_set, job_skills_set),
            "section_completeness": self._score_section_completeness(resume_text),
            "contact_information": self._score_contact_information(resume_text),
            "formatting_readability": self._score_formatting_readability(resume_text),
        }

        ats_score = (
            breakdown["keyword_match"] * 0.45
            + breakdown["section_completeness"] * 0.25
            + breakdown["contact_information"] * 0.15
            + breakdown["formatting_readability"] * 0.15
        )

        result = {
            "ats_score": round(max(0.0, min(100.0, ats_score)), 2),
            "breakdown": {key: round(value, 2) for key, value in breakdown.items()},
        }
        self.logger.info("ATS score calculated successfully: %.2f", result["ats_score"])
        return result

    def _score_keyword_match(
        self,
        resume_skills: set[str],
        job_skills: set[str],
    ) -> float:
        """Score the overlap between resume and job skills."""
        if not job_skills:
            return 75.0

        matched_count = len(resume_skills & job_skills)
        return (matched_count / len(job_skills)) * 100.0

    def _score_section_completeness(self, resume_text: str) -> float:
        """Score the presence of common ATS-friendly resume sections."""
        matched_sections = sum(
            1
            for pattern in self.SECTION_PATTERNS.values()
            if pattern.search(resume_text)
        )
        return (matched_sections / len(self.SECTION_PATTERNS)) * 100.0

    def _score_contact_information(self, resume_text: str) -> float:
        """Score the presence of key contact details recruiters expect."""
        checks = [
            bool(self.EMAIL_PATTERN.search(resume_text)),
            bool(self.PHONE_PATTERN.search(resume_text)),
            bool(self.LINKEDIN_PATTERN.search(resume_text)),
        ]
        return (sum(checks) / len(checks)) * 100.0

    def _score_formatting_readability(self, resume_text: str) -> float:
        """Score whether the resume structure looks parser-friendly."""
        score = 100.0
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]

        if len(lines) < 8:
            score -= 20.0

        bullet_count = len(
            re.findall(r"(^|\n)\s*([-*•]|\d+[\).\s])", resume_text, flags=re.MULTILINE)
        )
        if bullet_count < 3:
            score -= 15.0

        average_line_length = (
            sum(len(line) for line in lines) / len(lines) if lines else 0.0
        )
        if average_line_length > 140:
            score -= 15.0

        if re.search(r"\b(table|textbox|graphic)\b", resume_text, re.IGNORECASE):
            score -= 10.0

        return max(40.0, score)
