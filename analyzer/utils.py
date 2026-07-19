"""Shared utilities for configuration, filesystem helpers, and logging."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class AppConfig:
    """Application configuration loaded from environment variables."""

    app_name: str
    app_env: str
    log_level: str
    spacy_model: str
    sentence_transformer_model: str
    report_output_dir: Path
    sample_data_dir: Path
    log_dir: Path
    max_resume_size_mb: int
    supported_extensions: list[str]


class AppLogger:
    """Configure and return application loggers."""

    def __init__(self, log_level: str, log_dir: Path) -> None:
        self.log_level = log_level.upper()
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "app.log"
        self._configured_loggers: set[str] = set()

    def get_logger(self, name: str) -> logging.Logger:
        """
        Return a configured logger instance.

        Args:
            name: Logger name.

        Returns:
            Configured logger.
        """
        ensure_directories([self.log_dir])

        logger = logging.getLogger(name)
        logger.setLevel(self._resolve_level())

        if name in self._configured_loggers:
            return logger

        logger.propagate = False
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setLevel(self._resolve_level())
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(self._resolve_level())
        stream_handler.setFormatter(formatter)

        logger.handlers.clear()
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

        self._configured_loggers.add(name)
        return logger

    def _resolve_level(self) -> int:
        """Resolve the configured logging level safely."""
        return getattr(logging, self.log_level, logging.INFO)


def load_app_config() -> AppConfig:
    """
    Load application configuration from environment variables.

    Returns:
        AppConfig containing normalized runtime settings.
    """
    supported_extensions = _parse_csv_env(
        os.getenv("SUPPORTED_EXTENSIONS", "pdf,docx")
    )

    return AppConfig(
        app_name=os.getenv("APP_NAME", "AI Resume Analyzer"),
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        spacy_model=os.getenv("SPACY_MODEL", "en_core_web_sm"),
        sentence_transformer_model=os.getenv(
            "SENTENCE_TRANSFORMER_MODEL",
            "all-MiniLM-L6-v2",
        ),
        report_output_dir=Path(os.getenv("REPORT_OUTPUT_DIR", "reports")),
        sample_data_dir=Path(os.getenv("SAMPLE_DATA_DIR", "data")),
        log_dir=Path(os.getenv("LOG_DIR", "logs")),
        max_resume_size_mb=int(os.getenv("MAX_RESUME_SIZE_MB", "5")),
        supported_extensions=supported_extensions,
    )


def ensure_directories(paths: Iterable[Path | str]) -> None:
    """
    Create directories if they do not already exist.

    Args:
        paths: Directory paths to create.
    """
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def normalize_whitespace(text: str) -> str:
    """
    Collapse redundant whitespace while preserving single spaces.

    Args:
        text: Source text.

    Returns:
        Whitespace-normalized text.
    """
    return " ".join(text.split()).strip()


def safe_percentage(value: float, decimals: int = 2) -> float:
    """
    Clamp a numeric score to the 0-100 range.

    Args:
        value: Numeric score.
        decimals: Decimal precision for rounding.

    Returns:
        Rounded bounded score.
    """
    return round(max(0.0, min(100.0, value)), decimals)


def _parse_csv_env(value: str) -> list[str]:
    """Parse a comma-separated environment variable into normalized items."""
    return [item.strip().lower() for item in value.split(",") if item.strip()]
