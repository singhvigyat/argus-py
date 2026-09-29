from datetime import datetime

from app.aggregator.conflict_detector import detect_conflicts
from app.aggregator.issue_verifier import verify_issues
from app.logging_config import get_logger
from app.models.schemas import (
    Artifacts,
    ConflictReport,
    IssueVerification,
    PersonaAnalysis,
    ScreenshotSet,
    UXReport,
    VerificationResult,
    VerificationSummary,
    Viewport,
)

logger = get_logger(__name__)


def attach_verification(
    analyses: list[PersonaAnalysis],
    verification_results: list[VerificationResult],
) -> tuple[list[PersonaAnalysis], VerificationSummary]:
    results_by_key: dict[str, list[VerificationResult]] = {}
    for result in verification_results:
        key = f"{result.personaId}::{result.issueElementId}"
        results_by_key.setdefault(key, []).append(result)

    sanitized: list[PersonaAnalysis] = []
    for analysis in analyses:
        filtered_issues = []
        for issue in analysis.issues:
            key = f"{analysis.personaId}::{issue.elementId}"
            queue = results_by_key.get(key, [])
            verification = queue.pop(0) if queue else None

            if verification and verification.verdict == "element_not_found":
                continue

            if verification:
                issue = issue.model_copy(
                    update={
                        "verification": IssueVerification(
                            verdict=verification.verdict if verification.verdict != "element_not_found" else "unverified",
                            evidence=verification.evidence,
                            note=verification.note,
                        )
                    }
                )
            else:
                issue = issue.model_copy(
                    update={
                        "verification": IssueVerification(
                            verdict="unverified",
                            note="No verifier record found. Kept as non-blocking subjective issue.",
                        )
                    }
                )
            filtered_issues.append(issue)

        sanitized.append(analysis.model_copy(update={"issues": filtered_issues}))

    total = sum(len(a.issues) for a in analyses)
    element_not_found = sum(1 for r in verification_results if r.verdict == "element_not_found")
    summary = VerificationSummary(
        verified=sum(1 for r in verification_results if r.verdict == "verified"),
        unverified=sum(1 for r in verification_results if r.verdict == "unverified"),
        elementNotFound=element_not_found,
        removedIssueCount=element_not_found,
        totalIssueCount=total,
        removedIssueRatio=(element_not_found / total) if total else 0.0,
    )

    if element_not_found:
        removed = [
            f"{r.personaId}:{r.issueElementId}"
            for r in verification_results
            if r.verdict == "element_not_found"
        ]
        logger.warning("Removed %d hallucinated issue(s): %s", element_not_found, ", ".join(removed))

    if summary.removedIssueRatio > 0.2:
        logger.warning(
            "%.1f%% of issues removed as element_not_found — persona agents may be hallucinating IDs",
            summary.removedIssueRatio * 100,
        )

    return sanitized, summary


def extract_major_issues(analyses: list[PersonaAnalysis], limit: int = 8) -> list[str]:
    issues: list[str] = []
    for analysis in analyses:
        for issue in analysis.issues:
            issues.append(f"[{analysis.personaName}] {issue.observation}")
            if len(issues) >= limit:
                return issues
    return issues


def compute_severity_score(analyses: list[PersonaAnalysis]) -> float:
    if not analyses:
        return 0.0
    return round(sum(a.overallScore for a in analyses) / len(analyses), 1)


def assemble_report(
    job_id: str,
    url: str,
    viewport: Viewport,
    analyses: list[PersonaAnalysis],
    screenshots: ScreenshotSet,
    artifacts: Artifacts,
    analysis_time_ms: int,
    selected_personas: list[str],
    verification_results: list[VerificationResult],
    verification_summary: VerificationSummary,
    conflict_report: ConflictReport,
) -> UXReport:
    return UXReport(
        jobId=job_id,
        url=url,
        status="complete",
        createdAt=datetime.utcnow(),
        completedAt=datetime.utcnow(),
        viewport=viewport,
        screenshots=screenshots,
        selectedPersonas=selected_personas,
        personaInsights=analyses,
        conflicts=conflict_report.conflicts,
        conflictReport=conflict_report,
        summary=(
            f"Generated analysis across {len(analyses)} personas and found "
            f"{conflict_report.totalConflicts} cross-persona conflicts."
        ),
        majorIssues=extract_major_issues(analyses),
        recommendations=[],
        verificationResults=verification_results,
        verificationSummary=verification_summary,
        severityScore=compute_severity_score(analyses),
        analysisTime=analysis_time_ms,
        artifacts=artifacts,
    )


def create_pending_report(
    job_id: str,
    url: str,
    viewport: Viewport,
    selected_personas: list[str],
) -> UXReport:
    return UXReport(
        jobId=job_id,
        url=url,
        status="pending",
        viewport=viewport,
        selectedPersonas=selected_personas,
    )
