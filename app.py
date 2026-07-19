"""Streamlit entry point for the AI Resume Analyzer application."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from analyzer.ats_score import ATSScorer
from analyzer.jd_parser import JobDescriptionParser
from analyzer.recommendation import RecommendationEngine
from analyzer.report_generator import PDFReportGenerator
from analyzer.resume_parser import ResumeParser
from analyzer.similarity_engine import SimilarityEngine
from analyzer.skills_extractor import SkillExtractor
from analyzer.text_preprocessing import TextPreprocessor
from analyzer.utils import AppConfig, AppLogger, ensure_directories, load_app_config


st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


class ResumeAnalyzerApp:
    """Coordinates UI rendering and analysis workflows."""

    def __init__(self) -> None:
        self.config: AppConfig = load_app_config()
        ensure_directories(
            [
                self.config.report_output_dir,
                self.config.log_dir,
                self.config.sample_data_dir,
            ]
        )
        self.logger = AppLogger(self.config.log_level, self.config.log_dir).get_logger(
            "ai_resume_analyzer"
        )
        self.resume_parser = ResumeParser(logger=self.logger)
        self.jd_parser = JobDescriptionParser(logger=self.logger)
        self.preprocessor = TextPreprocessor(
            spacy_model=self.config.spacy_model,
            logger=self.logger,
        )
        self.skill_extractor = SkillExtractor(logger=self.logger)
        self.similarity_engine = SimilarityEngine(
            model_name=self.config.sentence_transformer_model,
            logger=self.logger,
        )
        self.ats_scorer = ATSScorer(logger=self.logger)
        self.recommendation_engine = RecommendationEngine(logger=self.logger)
        self.report_generator = PDFReportGenerator(logger=self.logger)

    def run(self) -> None:
        """Render the full Streamlit application."""
        self._render_header()
        self._render_sidebar()

        uploaded_file, job_description = self._render_inputs()
        if not uploaded_file or not job_description.strip():
            self._render_welcome_state()
            return

        try:
            analysis_result = self._analyze_resume(uploaded_file, job_description)
            self._render_results(analysis_result)
        except Exception as exc:  # pragma: no cover - UI fallback
            self.logger.exception("Resume analysis failed: %s", exc)
            st.error(
                "The resume could not be analyzed. Please check the file and try again."
            )

    def _render_header(self) -> None:
        """Render the page title and introduction."""
        st.title("AI Resume Analyzer")
        st.caption(
            "Upload a resume, paste a job description, and receive an AI-assisted fit"
            " analysis with ATS insights, skill coverage, and improvement guidance."
        )

    def _render_sidebar(self) -> None:
        """Render sidebar controls and application details."""
        with st.sidebar:
            st.header("Configuration")
            st.write(f"**spaCy model:** `{self.config.spacy_model}`")
            st.write(
                f"**Sentence model:** `{self.config.sentence_transformer_model}`"
            )
            st.write(
                f"**Supported files:** `{', '.join(self.config.supported_extensions)}`"
            )
            st.write(f"**Max resume size:** `{self.config.max_resume_size_mb} MB`")
            st.divider()
            st.subheader("Analysis coverage")
            st.markdown(
                "- Resume-job similarity\n"
                "- ATS compatibility\n"
                "- Matched vs missing skills\n"
                "- Strengths and recommendations\n"
                "- Downloadable PDF report"
            )

    def _render_inputs(self) -> tuple[Any | None, str]:
        """Render main analysis inputs."""
        left_col, right_col = st.columns(2)

        with left_col:
            uploaded_file = st.file_uploader(
                "Upload Resume",
                type=self.config.supported_extensions,
                help="Supported formats: PDF and DOCX.",
            )

        with right_col:
            job_description = st.text_area(
                "Paste Job Description",
                height=280,
                placeholder=(
                    "Paste the target role description here, including required"
                    " skills, responsibilities, and qualifications."
                ),
            )

        return uploaded_file, job_description

    def _render_welcome_state(self) -> None:
        """Render onboarding content before analysis starts."""
        st.info("Upload a resume and provide a job description to start analysis.")

        feature_col, workflow_col = st.columns(2)
        with feature_col:
            st.subheader("What you get")
            st.markdown(
                "- Match score\n"
                "- ATS score\n"
                "- Matched skills\n"
                "- Missing skills\n"
                "- Recommendations\n"
                "- PDF report"
            )
        with workflow_col:
            st.subheader("Recommended flow")
            st.markdown(
                "1. Upload a tailored resume\n"
                "2. Paste a job description\n"
                "3. Review the analysis dashboard\n"
                "4. Download the report"
            )

    def _analyze_resume(self, uploaded_file: Any, job_description: str) -> dict[str, Any]:
        """Execute the end-to-end resume analysis pipeline."""
        self._validate_uploaded_file(uploaded_file)

        resume_text = self.resume_parser.extract_text(
            file_name=uploaded_file.name,
            file_bytes=uploaded_file.getvalue(),
        )
        parsed_job_description = self.jd_parser.parse(job_description)

        cleaned_resume = self.preprocessor.clean_text(resume_text)
        cleaned_job_description = self.preprocessor.clean_text(parsed_job_description.raw_text)

        resume_doc = self.preprocessor.process(cleaned_resume)
        job_doc = self.preprocessor.process(cleaned_job_description)

        resume_skills = self.skill_extractor.extract_skills(resume_doc.normalized_text)
        job_skills = self.skill_extractor.extract_skills(job_doc.normalized_text)

        similarity_score = self.similarity_engine.calculate_similarity(
            resume_text=resume_doc.normalized_text,
            job_description_text=job_doc.normalized_text,
        )
        ats_result = self.ats_scorer.score_resume(
            resume_text=resume_text,
            resume_skills=resume_skills,
            job_skills=job_skills,
        )
        recommendation_result = self.recommendation_engine.generate(
            resume_text=resume_text,
            resume_skills=resume_skills,
            job_skills=job_skills,
            similarity_score=similarity_score,
            ats_score=ats_result["ats_score"],
        )

        report_payload = {
            "file_name": uploaded_file.name,
            "resume_text": resume_text,
            "job_description": parsed_job_description.raw_text,
            "similarity_score": similarity_score,
            "ats_score": ats_result["ats_score"],
            "matched_skills": sorted(resume_skills & job_skills),
            "missing_skills": sorted(job_skills - resume_skills),
            "recommended_skills": recommendation_result["recommended_skills"],
            "strengths": recommendation_result["strengths"],
            "improvements": recommendation_result["improvements"],
            "ats_breakdown": ats_result["breakdown"],
        }
        report_bytes = self.report_generator.generate_report(report_payload)

        return {
            "file_name": uploaded_file.name,
            "resume_skills": sorted(resume_skills),
            "job_skills": sorted(job_skills),
            "matched_skills": sorted(resume_skills & job_skills),
            "missing_skills": sorted(job_skills - resume_skills),
            "similarity_score": similarity_score,
            "ats_result": ats_result,
            "recommendation_result": recommendation_result,
            "report_bytes": report_bytes,
        }

    def _validate_uploaded_file(self, uploaded_file: Any) -> None:
        """Validate size and extension of the uploaded resume file."""
        suffix = Path(uploaded_file.name).suffix.lower().replace(".", "")
        if suffix not in self.config.supported_extensions:
            raise ValueError(f"Unsupported file type: {suffix}")

        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > self.config.max_resume_size_mb:
            raise ValueError(
                "Uploaded file exceeds the maximum allowed size of "
                f"{self.config.max_resume_size_mb} MB."
            )

    def _render_results(self, analysis_result: dict[str, Any]) -> None:
        """Render analysis metrics, charts, insights, and download action."""
        similarity_score = analysis_result["similarity_score"]
        ats_score = analysis_result["ats_result"]["ats_score"]
        matched_skills = analysis_result["matched_skills"]
        missing_skills = analysis_result["missing_skills"]
        recommended_skills = analysis_result["recommendation_result"][
            "recommended_skills"
        ]

        metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
        metric_col_1.metric("Match Score", f"{similarity_score:.1f}%")
        metric_col_2.metric("ATS Score", f"{ats_score:.1f}%")
        metric_col_3.metric("Matched Skills", str(len(matched_skills)))

        chart_col, summary_col = st.columns([1.2, 1])
        with chart_col:
            st.subheader("Skill Coverage")
            coverage_df = pd.DataFrame(
                [
                    {"Category": "Matched Skills", "Count": len(matched_skills)},
                    {"Category": "Missing Skills", "Count": len(missing_skills)},
                    {
                        "Category": "Recommended Skills",
                        "Count": len(recommended_skills),
                    },
                ]
            )
            chart = px.bar(
                coverage_df,
                x="Category",
                y="Count",
                color="Category",
                text="Count",
                title="Skill Coverage Overview",
            )
            chart.update_layout(showlegend=False, height=420)
            st.plotly_chart(chart, use_container_width=True)

        with summary_col:
            st.subheader("Key Insights")
            st.markdown(
                f"**Matched skills:** {', '.join(matched_skills) if matched_skills else 'None'}"
            )
            st.markdown(
                f"**Missing skills:** {', '.join(missing_skills) if missing_skills else 'None'}"
            )
            st.markdown(
                "**Recommended additions:** "
                f"{', '.join(recommended_skills) if recommended_skills else 'None'}"
            )

        insight_col_1, insight_col_2 = st.columns(2)
        with insight_col_1:
            st.subheader("Resume Strengths")
            strengths = analysis_result["recommendation_result"]["strengths"]
            if strengths:
                for strength in strengths:
                    st.success(strength)
            else:
                st.info("No notable strengths were identified from the current inputs.")

        with insight_col_2:
            st.subheader("Improvement Recommendations")
            improvements = analysis_result["recommendation_result"]["improvements"]
            if improvements:
                for improvement in improvements:
                    st.warning(improvement)
            else:
                st.info("No major improvement suggestions were generated.")

        st.subheader("ATS Breakdown")
        ats_df = pd.DataFrame(
            [
                {"Metric": key.replace("_", " ").title(), "Score": value}
                for key, value in analysis_result["ats_result"]["breakdown"].items()
            ]
        )
        st.dataframe(ats_df, use_container_width=True, hide_index=True)

        self._render_download_button(
            file_name=analysis_result["file_name"],
            report_bytes=analysis_result["report_bytes"],
        )

    def _render_download_button(self, file_name: str, report_bytes: bytes) -> None:
        """Render a PDF download button for the generated report."""
        output_name = f"{Path(file_name).stem}_analysis_report.pdf"
        st.download_button(
            label="Download Analysis Report (PDF)",
            data=io.BytesIO(report_bytes),
            file_name=output_name,
            mime="application/pdf",
            use_container_width=True,
        )


def main() -> None:
    """Application entry point."""
    app = ResumeAnalyzerApp()
    app.run()


if __name__ == "__main__":
    main()
