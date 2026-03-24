from collections import Counter
from datetime import datetime

from app.aggregator.conflict_detector import detect_conflicts
from app.aggregator.issue_verifier import verify_issues
from app.logging_config import get_logger
from app.models.schemas import (
    Artifacts,
    ConflictReport,
    IssueVerification,
    PersonaAnalysis,
    ReportSummary,
    ScreenshotSet,
    UIStructure,
    UXReport,
    VerificationResult,
    VerificationSummary,
    Viewport,
)

logger = get_logger(__name__)


def _attach_verification(
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
                            verdict=verification.verdict,
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


async def assemble_report(
    report_id: str,
    url: str,
    viewport: Viewport,
    analyses: list[PersonaAnalysis],
    ui_structure: UIStructure,
    screenshots: ScreenshotSet,
    artifacts: Artifacts,
    analysis_time_ms: int,
    selected_personas: list[str],
) -> UXReport:
    verification_results = verify_issues(analyses, ui_structure)
    sanitized, verification_summary = _attach_verification(analyses, verification_results)
    conflict_report = await detect_conflicts(sanitized)

    all_issues = [issue for a in sanitized for issue in a.issues]
    verified_ids = {
        r.issueElementId
        for r in verification_results
        if r.verdict == "verified"
    }
    section_counts = Counter(issue.section for issue in all_issues)
    top_section = section_counts.most_common(1)[0][0] if section_counts else "unknown"
    avg_score = sum(a.overallScore for a in sanitized) / len(sanitized) if sanitized else 0.0

    return UXReport(
        id=report_id,
        url=url,
        status="complete",
        createdAt=datetime.utcnow(),
        completedAt=datetime.utcnow(),
        viewport=viewport,
        summary=ReportSummary(
            overallScore=round(avg_score, 1),
            totalIssues=len(all_issues),
            criticalIssues=sum(1 for i in all_issues if i.severity == "critical"),
            verifiedIssues=sum(1 for i in all_issues if i.elementId in verified_ids),
            totalConflicts=conflict_report.totalConflicts,
            topSection=top_section,
        ),
        personaAnalyses=sanitized,
        conflicts=conflict_report.conflicts,
        conflictReport=conflict_report,
        verificationResults=verification_results,
        verificationSummary=verification_summary,
        artifacts=artifacts,
        screenshots=screenshots,
        selectedPersonas=selected_personas,
        analysisTimeMs=analysis_time_ms,
    )


def create_pending_report(report_id: str, url: str, viewport: Viewport, selected_personas: list[str]) -> UXReport:
    return UXReport(
        id=report_id,
        url=url,
        status="pending",
        viewport=viewport,
        selectedPersonas=selected_personas,
    )
