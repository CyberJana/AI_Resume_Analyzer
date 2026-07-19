"""Skill extraction utilities for resumes and job descriptions."""

from __future__ import annotations

import logging
import re
from collections import defaultdict


class SkillExtractionError(Exception):
    """Raised when skill extraction cannot be completed."""


class SkillExtractor:
    """Extract normalized skills from free-form resume and job description text."""

    SKILL_ALIASES: dict[str, tuple[str, ...]] = {
        "python": ("python", "python3", "python 3"),
        "java": ("java",),
        "javascript": ("javascript", "js"),
        "typescript": ("typescript", "ts"),
        "c++": ("c++", "cpp"),
        "sql": ("sql", "mysql", "postgresql", "postgres", "sqlite"),
        "nosql": ("nosql", "mongodb", "cassandra", "dynamodb"),
        "html": ("html", "html5"),
        "css": ("css", "css3"),
        "streamlit": ("streamlit",),
        "flask": ("flask",),
        "django": ("django",),
        "fastapi": ("fastapi",),
        "react": ("react", "reactjs", "react.js"),
        "angular": ("angular",),
        "vue": ("vue", "vuejs", "vue.js"),
        "node.js": ("node", "nodejs", "node.js"),
        "pandas": ("pandas",),
        "numpy": ("numpy",),
        "matplotlib": ("matplotlib",),
        "plotly": ("plotly",),
        "scikit-learn": ("scikit-learn", "sklearn"),
        "tensorflow": ("tensorflow",),
        "pytorch": ("pytorch", "torch"),
        "spacy": ("spacy",),
        "nlp": ("nlp", "natural language processing"),
        "machine learning": ("machine learning", "ml"),
        "deep learning": ("deep learning", "dl"),
        "data analysis": ("data analysis", "data analytics"),
        "data visualization": ("data visualization", "visualization"),
        "docker": ("docker",),
        "kubernetes": ("kubernetes", "k8s"),
        "aws": ("aws", "amazon web services"),
        "azure": ("azure",),
        "gcp": ("gcp", "google cloud", "google cloud platform"),
        "git": ("git", "github", "gitlab"),
        "ci/cd": ("ci/cd", "cicd", "continuous integration", "continuous delivery"),
        "rest api": ("rest api", "restful api", "api development"),
        "microservices": ("microservices",),
        "linux": ("linux",),
        "agile": ("agile", "scrum", "kanban"),
        "oop": ("oop", "object oriented programming"),
        "unit testing": ("unit testing", "pytest", "unittest"),
        "data structures": ("data structures",),
        "algorithms": ("algorithms",),
        "problem solving": ("problem solving",),
        "communication": ("communication",),
        "leadership": ("leadership",),
        "teamwork": ("teamwork", "collaboration"),
        "project management": ("project management",),
        "power bi": ("power bi", "powerbi"),
        "tableau": ("tableau",),
        "excel": ("excel", "microsoft excel"),
    }

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self._compiled_patterns = self._build_patterns()

    def extract_skills(self, text: str) -> set[str]:
        """
        Extract a normalized set of skills from input text.

        Args:
            text: Source text from a resume or job description.

        Returns:
            A set of normalized skill names.

        Raises:
            SkillExtractionError: If input text is invalid.
        """
        if text is None:
            raise SkillExtractionError("Input text cannot be None.")

        cleaned_text = self._normalize_text(text)
        if not cleaned_text:
            self.logger.warning("Skill extraction received empty text after normalization.")
            return set()

        matched_skills: set[str] = set()
        for skill_name, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(cleaned_text):
                    matched_skills.add(skill_name)
                    break

        self.logger.info("Extracted %s skills from text.", len(matched_skills))
        return matched_skills

    def extract_skill_frequency(self, text: str) -> dict[str, int]:
        """
        Extract skill mention frequencies from input text.

        Args:
            text: Source text to inspect.

        Returns:
            Dictionary of normalized skill names to mention counts.
        """
        cleaned_text = self._normalize_text(text)
        frequencies: dict[str, int] = defaultdict(int)

        if not cleaned_text:
            return {}

        for skill_name, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(cleaned_text)
                if matches:
                    frequencies[skill_name] += len(matches)

        return dict(sorted(frequencies.items(), key=lambda item: (-item[1], item[0])))

    @staticmethod
    def compare_skills(
        resume_skills: set[str],
        job_skills: set[str],
    ) -> dict[str, list[str]]:
        """Compare resume and job skills into matched and missing groups."""
        matched = sorted(resume_skills & job_skills)
        missing = sorted(job_skills - resume_skills)
        additional = sorted(resume_skills - job_skills)

        return {
            "matched": matched,
            "missing": missing,
            "additional": additional,
        }

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for phrase-based matching."""
        normalized = text.lower()
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[^\w\s+#./-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _build_patterns(self) -> dict[str, list[re.Pattern[str]]]:
        """Compile regex patterns for all known skills and aliases."""
        compiled_patterns: dict[str, list[re.Pattern[str]]] = {}

        for canonical_skill, aliases in self.SKILL_ALIASES.items():
            compiled_patterns[canonical_skill] = [
                self._compile_skill_pattern(alias) for alias in aliases
            ]

        return compiled_patterns

    @staticmethod
    def _compile_skill_pattern(skill_alias: str) -> re.Pattern[str]:
        """Compile a boundary-aware regex for a skill alias."""
        escaped_alias = re.escape(skill_alias.lower())
        pattern = rf"(?<!\w){escaped_alias}(?!\w)"
        return re.compile(pattern, re.IGNORECASE)
