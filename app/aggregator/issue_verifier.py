from app.models.schemas import PersonaAnalysis, UIStructure, VerificationResult

MIN_TAP_TARGET_SIZE = 44
MIN_READABLE_FONT_SIZE = 14

TAP_TARGET_HEURISTICS = {"tap_target_size"}
TEXT_SIZE_HEURISTICS = {"text_readability", "text_size"}
ARIA_LABEL_HEURISTICS = {"icon_labeling", "focus_visibility"}


def _normalize_heuristic(heuristic: str) -> str:
    return heuristic.strip().lower().replace(" ", "_")


def verify_issues(analyses: list[PersonaAnalysis], ui_structure: UIStructure) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    element_map = {el.id: el for el in ui_structure.elements}

    for analysis in analyses:
        for issue in analysis.issues:
            element = element_map.get(issue.elementId)

            if not element:
                results.append(
                    VerificationResult(
                        issueElementId=issue.elementId,
                        personaId=analysis.personaId,
                        verdict="element_not_found",
                        note=f"Element ID {issue.elementId} does not exist in UI structure",
                    )
                )
                continue

            heuristic = _normalize_heuristic(issue.heuristic)

            if heuristic in TAP_TARGET_HEURISTICS:
                too_small = element.width < MIN_TAP_TARGET_SIZE or element.height < MIN_TAP_TARGET_SIZE
                results.append(
                    VerificationResult(
                        issueElementId=issue.elementId,
                        personaId=analysis.personaId,
                        verdict="verified" if too_small else "unverified",
                        evidence=f"width={element.width}px, height={element.height}px",
                        note=(
                            f"Confirmed: below {MIN_TAP_TARGET_SIZE}px threshold"
                            if too_small
                            else "Element meets minimum size. Claim may be inaccurate."
                        ),
                    )
                )
                continue

            if heuristic in TEXT_SIZE_HEURISTICS:
                too_small = element.fontSize < MIN_READABLE_FONT_SIZE
                results.append(
                    VerificationResult(
                        issueElementId=issue.elementId,
                        personaId=analysis.personaId,
                        verdict="verified" if too_small else "unverified",
                        evidence=f"fontSize={element.fontSize}px",
                        note=(
                            f"Confirmed: below {MIN_READABLE_FONT_SIZE}px readable threshold"
                            if too_small
                            else "Font size is adequate. Subjective claim not supported by data."
                        ),
                    )
                )
                continue

            if heuristic in ARIA_LABEL_HEURISTICS:
                missing = element.tag == "button" and not element.ariaLabel.strip()
                results.append(
                    VerificationResult(
                        issueElementId=issue.elementId,
                        personaId=analysis.personaId,
                        verdict="verified" if missing else "unverified",
                        evidence=f'ariaLabel="{element.ariaLabel}", tag="{element.tag}"',
                        note="Missing aria-label on button" if missing else "Aria label present",
                    )
                )
                continue

            results.append(
                VerificationResult(
                    issueElementId=issue.elementId,
                    personaId=analysis.personaId,
                    verdict="unverified",
                    note="Subjective claim — not measurable from DOM data",
                )
            )

    return results
