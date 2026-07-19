"""Semantic similarity engine for resume and job description matching."""

from __future__ import annotations

import logging

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SimilarityEngineError(Exception):
    """Raised when similarity scoring cannot be completed."""


class SimilarityEngine:
    """Calculate semantic similarity between resume and job description text."""

    def __init__(self, model_name: str, logger: logging.Logger | None = None) -> None:
        self.model_name = model_name
        self.logger = logger or logging.getLogger(__name__)
        self._model = self._load_model(model_name)

    def calculate_similarity(
        self,
        resume_text: str,
        job_description_text: str,
    ) -> float:
        """
        Calculate a percentage similarity score between two text inputs.

        Args:
            resume_text: Normalized resume text.
            job_description_text: Normalized job description text.

        Returns:
            Similarity percentage between 0 and 100.

        Raises:
            SimilarityEngineError: If either input is empty or scoring fails.
        """
        if not resume_text.strip():
            raise SimilarityEngineError("Resume text cannot be empty for similarity scoring.")
        if not job_description_text.strip():
            raise SimilarityEngineError(
                "Job description text cannot be empty for similarity scoring."
            )

        semantic_score = self._semantic_similarity(resume_text, job_description_text)
        lexical_score = self._tfidf_similarity(resume_text, job_description_text)

        final_score = (semantic_score * 0.75) + (lexical_score * 0.25)
        bounded_score = max(0.0, min(100.0, final_score))
        self.logger.info("Similarity score calculated successfully: %.2f", bounded_score)
        return round(bounded_score, 2)

    def _load_model(self, model_name: str) -> SentenceTransformer:
        """Load the sentence transformer model once during initialization."""
        try:
            return SentenceTransformer(model_name)
        except Exception as exc:
            self.logger.exception(
                "Failed to load sentence transformer model '%s': %s",
                model_name,
                exc,
            )
            raise SimilarityEngineError(
                f"Unable to load sentence transformer model '{model_name}'."
            ) from exc

    def _semantic_similarity(self, resume_text: str, job_description_text: str) -> float:
        """Compute embedding-based cosine similarity as a percentage."""
        try:
            embeddings = self._model.encode(
                [resume_text, job_description_text],
                normalize_embeddings=True,
            )
            score = float(np.dot(embeddings[0], embeddings[1])) * 100.0
            return max(0.0, min(100.0, score))
        except Exception as exc:
            self.logger.exception("Semantic similarity calculation failed: %s", exc)
            raise SimilarityEngineError("Semantic similarity calculation failed.") from exc

    def _tfidf_similarity(self, resume_text: str, job_description_text: str) -> float:
        """Compute lexical overlap using TF-IDF cosine similarity."""
        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            matrix = vectorizer.fit_transform([resume_text, job_description_text])
            score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0] * 100.0
            return max(0.0, min(100.0, float(score)))
        except Exception as exc:
            self.logger.exception("TF-IDF similarity calculation failed: %s", exc)
            raise SimilarityEngineError("TF-IDF similarity calculation failed.") from exc
