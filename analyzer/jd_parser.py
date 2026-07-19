"""Job description parsing utilities."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedJobDescription:
    """Structured representation of a job description."""

    raw_text: str
    normalized_text: str
    responsibilities: list[str] = field(default_factory=list)
    qualifications: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


class JobDescriptionParsingError(Exception):
    """Raised when the job description is invalid or cannot be parsed."""


class JobDescriptionParser:
    """Parse free-form job descriptions into structured components."""

    RESPONSIBILITY_HEADERS = (
        "responsibilities",
        "key responsibilities",
        "what you will do",
        "your responsibilities",
        "role responsibilities",
    )
    QUALIFICATION_HEADERS = (
        "qualifications",
        "requirements",
        "preferred qualifications",
        "basic qualifications",
        "what we are looking for",
        "skills required",
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def parse(self, raw_text: str) -> ParsedJobDescription:
        """
        Parse a raw job description into structured sections.

        Args:
            raw_text: The job description provided by the user.

        Returns:
            ParsedJobDescription with normalized text and extracted sections.

        Raises:
            JobDescriptionParsingError: If the input is empty or invalid.
        """
        normalized_text = self._normalize_text(raw_text)
        if not normalized_text:
            self.logger.error("Job description parsing failed because the input was empty.")
            raise JobDescriptionParsingError("Job description cannot be empty.")

        lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
        responsibilities = self._extract_section_items(lines, self.RESPONSIBILITY_HEADERS)
        qualifications = self._extract_section_items(lines, self.QUALIFICATION_HEADERS)
        keywords = self._extract_keywords(normalized_text)

        self.logger.info("Job description parsed successfully.")
        return ParsedJobDescription(
            raw_text=normalized_text,
            normalized_text=normalized_text.lower(),
            responsibilities=responsibilities,
            qualifications=qualifications,
            keywords=keywords,
        )

    @staticmethod
    def _normalize_text(raw_text: str) -> str:
        """Normalize whitespace and bullet characters."""
        if raw_text is None:
            return ""

        cleaned = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = re.sub(r"[•▪◦●]", "-", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        lines = [line.strip() for line in cleaned.splitlines()]
        return "\n".join(line for line in lines if line).strip()

    def _extract_section_items(
        self,
        lines: list[str],
        known_headers: tuple[str, ...],
    ) -> list[str]:
        """Extract list items following known section headers."""
        collected_items: list[str] = []
        in_target_section = False

        for line in lines:
            normalized_line = line.lower().rstrip(":")

            if normalized_line in known_headers:
                in_target_section = True
                continue

            if in_target_section and self._looks_like_header(normalized_line):
                break

            if in_target_section:
                cleaned_item = self._clean_section_line(line)
                if cleaned_item:
                    collected_items.append(cleaned_item)

        return collected_items

    @staticmethod
    def _looks_like_header(line: str) -> bool:
        """Infer whether a line looks like a new section header."""
        if not line:
            return False

        words = line.split()
        if len(words) > 6:
            return False

        return line.endswith(":") or all(word.isalpha() for word in words)

    @staticmethod
    def _clean_section_line(line: str) -> str:
        """Clean a bullet or numbered list item."""
        cleaned = re.sub(r"^[-*]\s+", "", line.strip())
        cleaned = re.sub(r"^\d+[\).\s-]+", "", cleaned)
        return cleaned.strip()

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract lightweight candidate keywords from the job description."""
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}", text.lower())
        seen: set[str] = set()
        keywords: list[str] = []

        for token in tokens:
            if len(token) < 3:
                continue
            if token in seen:
                continue
            seen.add(token)
            keywords.append(token)

        return keywords
