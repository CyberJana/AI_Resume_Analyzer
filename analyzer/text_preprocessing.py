"""Text preprocessing utilities for resume and job description analysis."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import spacy
from spacy.language import Language


@dataclass(slots=True)
class ProcessedText:
    """Normalized NLP-ready text representation."""

    original_text: str
    cleaned_text: str
    normalized_text: str
    tokens: list[str] = field(default_factory=list)
    sentences: list[str] = field(default_factory=list)


class TextPreprocessingError(Exception):
    """Raised when text preprocessing cannot be completed."""


class TextPreprocessor:
    """Clean and normalize text for downstream NLP tasks."""

    DEFAULT_STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "was",
        "were",
        "with",
    }

    def __init__(self, spacy_model: str, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.spacy_model = spacy_model
        self._nlp = self._load_language_model(spacy_model)

    @property
    def nlp(self) -> Language:
        """Return the loaded spaCy language model."""
        return self._nlp

    def clean_text(self, text: str) -> str:
        """
        Clean raw text while preserving semantic content.

        Args:
            text: Raw input text.

        Returns:
            Cleaned text string.
        """
        if text is None:
            return ""

        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = re.sub(r"[^\S\n]+", " ", cleaned)
        cleaned = re.sub(r"[•▪◦●]", " ", cleaned)
        cleaned = re.sub(r"[^\w\s\n+#./-]", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r" {2,}", " ", cleaned)
        lines = [line.strip() for line in cleaned.splitlines()]
        return "\n".join(line for line in lines if line).strip()

    def process(self, text: str) -> ProcessedText:
        """
        Produce cleaned, tokenized, and normalized text artifacts.

        Args:
            text: Clean or raw text to preprocess.

        Returns:
            ProcessedText containing reusable analysis fields.

        Raises:
            TextPreprocessingError: If preprocessing fails.
        """
        cleaned_text = self.clean_text(text)
        if not cleaned_text:
            self.logger.error("Text preprocessing failed because the input was empty.")
            raise TextPreprocessingError("Input text is empty after cleaning.")

        try:
            doc = self._nlp(cleaned_text)
        except Exception as exc:
            self.logger.exception("spaCy processing failed: %s", exc)
            raise TextPreprocessingError("Unable to process text with spaCy.") from exc

        tokens = self._extract_normalized_tokens(doc)
        normalized_text = " ".join(tokens).strip()
        if not normalized_text:
            normalized_text = cleaned_text.lower()

        sentences = self._extract_sentences(doc)

        self.logger.info("Text preprocessing completed successfully.")
        return ProcessedText(
            original_text=text,
            cleaned_text=cleaned_text,
            normalized_text=normalized_text,
            tokens=tokens,
            sentences=sentences,
        )

    def _load_language_model(self, model_name: str) -> Language:
        """Load a spaCy model with explicit error reporting."""
        try:
            return spacy.load(model_name)
        except OSError as exc:
            self.logger.exception("Failed to load spaCy model '%s': %s", model_name, exc)
            raise TextPreprocessingError(
                f"spaCy model '{model_name}' is not installed. "
                "Run 'python -m spacy download en_core_web_sm'."
            ) from exc

    def _extract_normalized_tokens(self, doc: Language) -> list[str]:
        """Extract tokens suitable for scoring and skill matching."""
        normalized_tokens: list[str] = []

        for token in doc:
            if token.is_space or token.is_punct:
                continue

            normalized = token.lemma_.lower().strip()
            if not normalized or normalized == "-pron-":
                normalized = token.text.lower().strip()

            if len(normalized) < 2:
                continue
            if normalized in self.DEFAULT_STOP_WORDS:
                continue
            if normalized.isnumeric():
                continue

            normalized_tokens.append(normalized)

        return normalized_tokens

    @staticmethod
    def _extract_sentences(doc: Language) -> list[str]:
        """Extract cleaned sentence strings from a processed document."""
        sentences: list[str] = []

        for sentence in doc.sents:
            cleaned_sentence = sentence.text.strip()
            if cleaned_sentence:
                sentences.append(cleaned_sentence)

        return sentences
