"""PDF report generation for resume analysis results."""

from __future__ import annotations

import io
import logging
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class ReportGenerationError(Exception):
    """Raised when the analysis report cannot be generated."""


class PDFReportGenerator:
    """Generate a PDF summary report for a resume analysis result."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.styles = self._build_styles()

    def generate_report(self, payload: dict[str, Any]) -> bytes:
        """
        Generate a PDF report from an analysis payload.

        Args:
            payload: Analysis data used to build the PDF.

        Returns:
            PDF bytes.
        """
        self._validate_payload(payload)

        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
            title="AI Resume Analyzer Report",
        )

        story: list[Any] = []
        story.extend(self._build_header(payload))
        story.extend(self._build_score_summary(payload))
        story.extend(self._build_skill_sections(payload))
        story.extend(self._build_ats_breakdown(payload))
        story.extend(self._build_list_section("Resume Strengths", payload["strengths"]))
        story.extend(
            self._build_list_section(
                "Improvement Recommendations",
                payload["improvements"],
            )
        )

        try:
            document.build(story)
        except Exception as exc:
            self.logger.exception("PDF report generation failed: %s", exc)
            raise ReportGenerationError("Failed to generate PDF report.") from exc

        self.logger.info("PDF report generated successfully.")
        return buffer.getvalue()

    def _validate_payload(self, payload: dict[str, Any]) -> None:
        """Validate required analysis fields before building a report."""
        required_fields = {
            "file_name",
            "job_description",
            "similarity_score",
            "ats_score",
            "matched_skills",
            "missing_skills",
            "recommended_skills",
            "strengths",
            "improvements",
            "ats_breakdown",
        }
        missing_fields = required_fields - payload.keys()
        if missing_fields:
            raise ReportGenerationError(
                "Missing fields for report generation: "
                f"{', '.join(sorted(missing_fields))}."
            )

    def _build_styles(self) -> dict[str, ParagraphStyle]:
        """Create custom paragraph styles used in the PDF."""
        stylesheet = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "CustomTitle",
                parent=stylesheet["Title"],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#1f3c88"),
                spaceAfter=12,
            ),
            "heading": ParagraphStyle(
                "CustomHeading",
                parent=stylesheet["Heading2"],
                fontSize=13,
                leading=16,
                textColor=colors.HexColor("#0f172a"),
                spaceBefore=10,
                spaceAfter=8,
            ),
            "body": ParagraphStyle(
                "CustomBody",
                parent=stylesheet["BodyText"],
                fontSize=10,
                leading=14,
                spaceAfter=6,
            ),
            "bullet": ParagraphStyle(
                "CustomBullet",
                parent=stylesheet["BodyText"],
                fontSize=10,
                leading=14,
                leftIndent=14,
                bulletIndent=4,
                spaceAfter=4,
            ),
        }

    def _build_header(self, payload: dict[str, Any]) -> list[Any]:
        """Build the report heading content."""
        return [
            Paragraph("AI Resume Analyzer Report", self.styles["title"]),
            Paragraph(
                f"<b>Resume File:</b> {payload['file_name']}",
                self.styles["body"],
            ),
            Spacer(1, 0.12 * inch),
        ]

    def _build_score_summary(self, payload: dict[str, Any]) -> list[Any]:
        """Build the high-level score summary table."""
        data = [
            ["Metric", "Score"],
            ["Resume-Job Match", f"{payload['similarity_score']:.2f}%"],
            ["ATS Compatibility", f"{payload['ats_score']:.2f}%"],
        ]

        table = Table(data, colWidths=[3.2 * inch, 2.2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3c88")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        return [
            Paragraph("Score Summary", self.styles["heading"]),
            table,
            Spacer(1, 0.16 * inch),
        ]

    def _build_skill_sections(self, payload: dict[str, Any]) -> list[Any]:
        """Build matched, missing, and recommended skill sections."""
        story: list[Any] = [Paragraph("Skill Analysis", self.styles["heading"])]
        story.extend(
            self._build_inline_list_paragraph(
                "Matched Skills",
                payload["matched_skills"],
            )
        )
        story.extend(
            self._build_inline_list_paragraph(
                "Missing Skills",
                payload["missing_skills"],
            )
        )
        story.extend(
            self._build_inline_list_paragraph(
                "Recommended Skills",
                payload["recommended_skills"],
            )
        )
        story.append(Spacer(1, 0.12 * inch))
        return story

    def _build_ats_breakdown(self, payload: dict[str, Any]) -> list[Any]:
        """Build the ATS breakdown table section."""
        rows = [["ATS Factor", "Score"]]
        for key, value in payload["ats_breakdown"].items():
            rows.append([key.replace("_", " ").title(), f"{value:.2f}%"])

        table = Table(rows, colWidths=[3.2 * inch, 2.2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ]
            )
        )

        return [
            Paragraph("ATS Breakdown", self.styles["heading"]),
            table,
            Spacer(1, 0.16 * inch),
        ]

    def _build_list_section(self, title: str, items: list[str]) -> list[Any]:
        """Build a titled bulleted list section."""
        story: list[Any] = [Paragraph(title, self.styles["heading"])]

        if not items:
            story.append(Paragraph("No items available.", self.styles["body"]))
            return story

        for item in items:
            story.append(Paragraph(item, self.styles["bullet"], bulletText="•"))

        story.append(Spacer(1, 0.08 * inch))
        return story

    def _build_inline_list_paragraph(self, label: str, items: list[str]) -> list[Any]:
        """Build a label/value paragraph for comma-separated skill lists."""
        joined_items = ", ".join(items) if items else "None"
        return [
            Paragraph(
                f"<b>{label}:</b> {joined_items}",
                self.styles["body"],
            )
        ]
