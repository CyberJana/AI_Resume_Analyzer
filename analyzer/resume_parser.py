"""Resume parsing utilities for supported document formats."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from docx import Document
from PyPDF2 import PdfReader


class ResumeParsingError(Exception):
    """Raised when a resume file cannot be parsed successfully."""


class ResumeParser:
    """Extract plain text content from resume documents."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def extract_text(self, file_name: str, file_bytes: bytes) -> str:
        """
        Extract text from a resume document.

        Args:
            file_name: Original uploaded file name.
            file_bytes: Raw uploaded file content.

        Returns:
            Extracted resume text.

        Raises:
            ResumeParsingError: If the file cannot be parsed or is empty.
        """
        self._validate_input(file_name=file_name, file_bytes=file_bytes)
        extension = Path(file_name).suffix.lower()

        if extension == ".pdf":
            text = self._extract_from_pdf(file_bytes=file_bytes)
        elif extension == ".docx":
            text = self._extract_from_docx(file_bytes=file_bytes)
        else:
            self.logger.error("Unsupported resume file extension received: %s", extension)
            raise ResumeParsingError(f"Unsupported resume file type: {extension}")

        normalized_text = self._normalize_extracted_text(text)
        if not normalized_text:
            self.logger.error("No readable text content found in resume: %s", file_name)
            raise ResumeParsingError("No readable text could be extracted from the resume.")

        self.logger.info("Resume parsed successfully: %s", file_name)
        return normalized_text

    def _validate_input(self, file_name: str, file_bytes: bytes) -> None:
        """Validate basic parser input before extraction."""
        if not file_name.strip():
            self.logger.error("Resume parsing failed because the file name was empty.")
            raise ResumeParsingError("The uploaded resume file name is empty.")

        if not file_bytes:
            self.logger.error("Resume parsing failed because the file content was empty.")
            raise ResumeParsingError("The uploaded resume file is empty.")

        extension = Path(file_name).suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            self.logger.error("Resume parsing failed due to unsupported extension: %s", extension)
            raise ResumeParsingError(
                f"Unsupported file format '{extension}'. Supported formats are PDF and DOCX."
            )

    def _extract_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from a PDF document."""
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            page_text: list[str] = []

            for page_number, page in enumerate(reader.pages, start=1):
                extracted = page.extract_text() or ""
                if extracted.strip():
                    page_text.append(extracted)
                else:
                    self.logger.debug("PDF page %s produced no text.", page_number)

            return "\n".join(page_text)
        except Exception as exc:
            self.logger.exception("PDF resume parsing failed: %s", exc)
            raise ResumeParsingError("The PDF resume could not be parsed.") from exc

    def _extract_from_docx(self, file_bytes: bytes) -> str:
        """Extract text from a DOCX document, including table content."""
        try:
            document = Document(io.BytesIO(file_bytes))
            sections: list[str] = []

            paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
            sections.extend(text for text in paragraphs if text)

            for table in document.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        sections.append(" | ".join(cells))

            return "\n".join(sections)
        except Exception as exc:
            self.logger.exception("DOCX resume parsing failed: %s", exc)
            raise ResumeParsingError("The DOCX resume could not be parsed.") from exc

    @staticmethod
    def _normalize_extracted_text(text: str) -> str:
        """Normalize whitespace from extracted document text."""
        lines = [line.strip() for line in text.splitlines()]
        non_empty_lines = [line for line in lines if line]
        return "\n".join(non_empty_lines).strip()
