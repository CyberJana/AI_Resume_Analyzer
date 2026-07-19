"""Tests for parsing and preprocessing components."""

from __future__ import annotations

import io

import pytest
from docx import Document

from analyzer.jd_parser import JobDescriptionParser, JobDescriptionParsingError
from analyzer.resume_parser import ResumeParser, ResumeParsingError
from analyzer.text_preprocessing import ProcessedText, TextPreprocessor


def _build_docx_bytes(paragraphs: list[str]) -> bytes:
    """Create an in-memory DOCX document for parser tests."""
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_resume_parser_extracts_text_from_docx() -> None:
    """DOCX resumes should be parsed into normalized plain text."""
    parser = ResumeParser()
    content = _build_docx_bytes(
        [
            "Jane Doe",
            "Python Developer",
            "Built Streamlit dashboards and NLP pipelines.",
        ]
    )

    extracted_text = parser.extract_text("resume.docx", content)

    assert "Jane Doe" in extracted_text
    assert "Python Developer" in extracted_text
    assert "NLP pipelines" in extracted_text


def test_resume_parser_rejects_unsupported_extension() -> None:
    """Unsupported file types should raise a parsing error."""
    parser = ResumeParser()

    with pytest.raises(ResumeParsingError):
        parser.extract_text("resume.txt", b"plain text")


def test_resume_parser_rejects_empty_file() -> None:
    """Empty uploaded files should be rejected."""
    parser = ResumeParser()

    with pytest.raises(ResumeParsingError):
        parser.extract_text("resume.docx", b"")


def test_job_description_parser_extracts_sections() -> None:
    """Known JD sections should be separated into structured lists."""
    parser = JobDescriptionParser()
    job_description = """
    Responsibilities:
    - Build ML-powered applications
    - Collaborate with product and engineering teams

    Qualifications:
    - 3+ years of Python experience
    - Experience with Streamlit and AWS
    """

    parsed = parser.parse(job_description)

    assert parsed.raw_text
    assert "build ml-powered applications" in parsed.normalized_text
    assert parsed.responsibilities == [
        "Build ML-powered applications",
        "Collaborate with product and engineering teams",
    ]
    assert parsed.qualifications == [
        "3+ years of Python experience",
        "Experience with Streamlit and AWS",
    ]
    assert "python" in parsed.keywords


def test_job_description_parser_rejects_empty_input() -> None:
    """Empty job descriptions should raise a parsing error."""
    parser = JobDescriptionParser()

    with pytest.raises(JobDescriptionParsingError):
        parser.parse("   ")


def test_text_preprocessor_cleans_and_processes_text() -> None:
    """Text preprocessing should normalize tokens and preserve sentences."""
    preprocessor = TextPreprocessor(spacy_model="en_core_web_sm")
    raw_text = """
    Experienced Python developer with 5 years of experience.
    Built data pipelines, dashboards, and NLP services using Streamlit.
    """

    cleaned_text = preprocessor.clean_text(raw_text)
    processed = preprocessor.process(cleaned_text)

    assert isinstance(processed, ProcessedText)
    assert "python" in processed.normalized_text
    assert "developer" in processed.tokens
    assert any("Streamlit" in sentence for sentence in processed.sentences)
    assert "\r" not in cleaned_text
