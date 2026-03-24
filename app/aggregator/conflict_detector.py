import json
import re
from collections import Counter

from app.ai.gemini import analyze_text_with_gemini
from app.logging_config import get_logger
from app.models.schemas import Conflict, ConflictReport, PersonaAnalysis

logger = get_logger(__name__)

SEVERITY_RANK: dict[str, int] = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _pick_most_common(values: list[str]) -> str:
    cleaned = [v.strip() for v in values if v.strip()]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


def detect_severity_conflicts(analyses: list[PersonaAnalysis]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    element_map: dict[int, list[dict]] = {}

    for analysis in analyses:
        for issue in analysis.issues:
            element_map.setdefault(issue.elementId, []).append(
                {
                    "personaId": analysis.personaId,
                    "personaName": analysis.personaName,
                    "severity": issue.severity,
                    "elementDescription": issue.elementDescription,
                    "section": issue.section,
                }
            )

    for element_id, refs in element_map.items():
        by_persona: dict[str, dict] = {}
        for ref in refs:
            current = by_persona.get(ref["personaId"])
            if not current or SEVERITY_RANK[ref["severity"]] > SEVERITY_RANK[current["severity"]]:
                by_persona[ref["personaId"]] = ref

        unique_refs = list(by_persona.values())
        if len(unique_refs) < 2:
            continue

        severities = _unique([r["severity"] for r in unique_refs])
        if len(severities) <= 1:
            continue

        parts = []
        grouped: dict[str, list[str]] = {}
        for ref in unique_refs:
            grouped.setdefault(ref["severity"], []).append(ref["personaName"])
        for severity in sorted(grouped, key=lambda s: SEVERITY_RANK[s], reverse=True):
            parts.append(f"{severity} by {', '.join(_unique(grouped[severity]))}")

        spread = SEVERITY_RANK[max(severities, key=lambda s: SEVERITY_RANK[s])] - SEVERITY_RANK[
            min(severities, key=lambda s: SEVERITY_RANK[s])
        ]
        implication = (
            "Keep this flow, but add stronger guidance and error prevention for users who struggle."
            if spread >= 2
            else "Tune labels and helper cues on this element so more personas interpret it the same way."
        )

        conflicts.append(
            Conflict(
                elementId=element_id,
                elementDescription=_pick_most_common([r["elementDescription"] for r in unique_refs])
                or f"Element {element_id}",
                section=_pick_most_common([r["section"] for r in unique_refs]) or "General",
                conflictType="severity_disagreement",
                personasInvolved=_unique([r["personaName"] for r in unique_refs]),
                summary=f"Element {element_id} has conflicting severity ratings: {' vs '.join(parts)}.",
                designImplication=implication,
            )
        )

    return conflicts


def _clean_json_array(raw: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    first = cleaned.find("[")
    last = cleaned.rfind("]")
    if first != -1 and last > first:
        return cleaned[first : last + 1]
    return cleaned


async def detect_semantic_conflicts(analyses: list[PersonaAnalysis]) -> list[Conflict]:
    stripped = [
        {
            "personaId": a.personaId,
            "personaName": a.personaName,
            "issues": [
                {
                    "elementId": i.elementId,
                    "elementDescription": i.elementDescription,
                    "section": i.section,
                    "severity": i.severity,
                    "observation": i.observation,
                }
                for i in a.issues
            ],
            "positives": a.positives,
        }
        for a in analyses
    ]

    prompt = f"""
You are analyzing UX feedback from 4 different persona agents who evaluated the same webpage.

Here are their analyses:
<analyses>
{json.dumps(stripped, indent=2)}
</analyses>

Your task: identify conflicts where personas have meaningfully opposing views about the same UI element or area.

A conflict exists when:
- One persona lists something as a positive that another persona flags as a medium/high/critical issue
- Two personas describe the same element with opposite sentiments
- One persona finds an element easy/clear, another finds the same element confusing/problematic

Rules:
- Only flag genuine oppositions, not just different priorities
- Every conflict must name the specific personas involved
- If a conflict involves a specific elementId, include it. If general, set elementId to null.
- Do not invent conflicts. If analyses agree, return an empty array.

Respond ONLY with a valid JSON array. No preamble, no markdown fences.

Schema for each conflict object:
{{
  "elementId": number | null,
  "elementDescription": string,
  "section": string,
  "conflictType": "semantic_conflict",
  "personasInvolved": string[],
  "summary": string,
  "designImplication": string
}}
"""

    try:
        response = await analyze_text_with_gemini(prompt)
    except Exception as exc:
        logger.error("Semantic conflict detection failed: %s", exc)
        return []

    try:
        parsed = json.loads(_clean_json_array(response))
        if not isinstance(parsed, list):
            return []

        conflicts: list[Conflict] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            eid = item.get("elementId")
            conflicts.append(
                Conflict(
                    elementId=eid if isinstance(eid, int) else None,
                    elementDescription=str(item.get("elementDescription") or "Shared interface area"),
                    section=str(item.get("section") or "General"),
                    conflictType="semantic_conflict",
                    personasInvolved=[str(p) for p in item.get("personasInvolved", []) if p],
                    summary=str(item.get("summary") or "Opposing feedback detected between personas."),
                    designImplication=str(
                        item.get("designImplication") or "Validate this area with affected user groups."
                    ),
                )
            )
        return conflicts
    except json.JSONDecodeError:
        logger.error("Failed to parse semantic conflict JSON")
        return []


async def detect_conflicts(analyses: list[PersonaAnalysis]) -> ConflictReport:
    severity_conflicts = detect_severity_conflicts(analyses)
    semantic_conflicts = await detect_semantic_conflicts(analyses)
    all_conflicts = severity_conflicts + semantic_conflicts

    element_counts: Counter[int] = Counter()
    for conflict in all_conflicts:
        if conflict.elementId is not None:
            element_counts[conflict.elementId] += 1

    most_contested = element_counts.most_common(1)[0][0] if element_counts else None

    return ConflictReport(
        totalConflicts=len(all_conflicts),
        conflicts=all_conflicts,
        mostContestedElement=most_contested,
    )
