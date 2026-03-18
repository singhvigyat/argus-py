import json
import re
from pathlib import Path

from app.ai.gemini import analyze_image_with_gemini
from app.logging_config import get_logger
from app.models.schemas import Persona, PersonaAnalysis, UXIssue, UIStructure, Viewport

logger = get_logger(__name__)


def _build_prompt(persona: Persona, ui_structure: UIStructure, validation_errors: str = "") -> str:
    heuristics = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(persona.heuristics))
    goals = "\n".join(f"- {g}" for g in persona.goals)

    base = f"""You are {persona.name}, a {persona.age}-year-old.

Your background: {persona.background}

Your goals when visiting any website:
{goals}

Before listing issues, write 2-4 sentences of honest first-person reasoning about your overall impression of the interface.

You must evaluate the following heuristics:
{heuristics}

You are given:
- A labeled screenshot where every UI element has a numbered badge [N]
- A structured JSON describing each element's tag, text, section, and additional flags

JSON field guide:
- "text": the element's visible text. If this reads "[visual label — see screenshot]" it means the label is drawn INSIDE an image or SVG — look at the screenshot to read it. Do NOT report these elements as having no text.
- "imageOnly": true means the element's content is an image or SVG. Its visual label is visible in the screenshot.
- "ariaLabel": the element's accessible name — treat this as equivalent to visible text.

The UI is divided into the following sections:
{json.dumps(ui_structure.sections, indent=2)}

When evaluating an element, consider its section context.
A small font in a footer note is less severe than a small font in the primary call-to-action.

Rules:
- Every issue you report MUST reference a real element ID from the JSON
- Never invent elements that do not exist in the JSON
- If you cannot find evidence for a claim, do not make the claim
- Write observations in first person: "I noticed..." or "I found it hard to..."
- When you identify a UX issue, reference the element by number, e.g. "Element [6] — the sign-up button"
- CRITICAL: Never report that an image or SVG-based logo/icon is missing a text label based solely on an empty JSON 'text' field.

Respond ONLY with a valid JSON object matching the PersonaAnalysis schema.
No preamble, no explanation, no markdown code fences. Raw JSON only.

Expected JSON Schema:
{{
  "personaId": "{persona.id}",
  "personaName": "{persona.name}",
  "viewport": "desktop",
  "reasoning": "2-4 sentences of thinking before issues list",
  "issues": [
    {{
      "elementId": 123,
      "elementDescription": "brief description",
      "section": "section name",
      "heuristic": "heuristic name",
      "observation": "first person observation",
      "impact": "why this matters for you",
      "severity": "low | medium | high | critical",
      "recommendation": "one concrete fix"
    }}
  ],
  "positives": ["1-3 things you found easy or good"],
  "overallScore": 5
}}

Here is the structured data for every labeled element on this page:
<ui_structure>
{ui_structure.model_dump_json(indent=2)}
</ui_structure>
"""
    if validation_errors:
        base += f"\n\nPrevious attempt failed with errors:\n{validation_errors}\nPlease fix these and return valid JSON."
    return base


def _clean_json_response(raw: str) -> str:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last > first:
        cleaned = cleaned[first : last + 1]
    return cleaned


async def run_persona_agent(
    persona: Persona,
    som_screenshot: bytes,
    ui_structure: UIStructure,
    viewport: Viewport,
    max_retries: int = 3,
) -> PersonaAnalysis | None:
    allowed_ids = {el.id for el in ui_structure.elements}
    validation_errors = ""

    for attempt in range(1, max_retries + 1):
        prompt = _build_prompt(persona, ui_structure, validation_errors)
        try:
            raw = await analyze_image_with_gemini(som_screenshot, prompt)
        except Exception as exc:
            logger.error("[%s] Gemini call failed: %s", persona.name, exc)
            return None

        try:
            parsed = json.loads(_clean_json_response(raw))
        except json.JSONDecodeError:
            validation_errors = "Failed to parse JSON. Return strictly valid JSON."
            logger.warning("[%s] JSON parse failed on attempt %d", persona.name, attempt)
            continue

        if not isinstance(parsed.get("issues"), list):
            validation_errors = "Missing 'issues' array in JSON."
            continue

        invalid_ids: list[int] = []
        for issue in parsed["issues"]:
            eid = issue.get("elementId")
            if not isinstance(eid, int):
                validation_errors = "All issues must have a numeric 'elementId'."
                invalid_ids = [-1]
                break
            if eid not in allowed_ids:
                invalid_ids.append(eid)

        if invalid_ids and invalid_ids != [-1]:
            validation_errors = (
                f"The following element IDs do not exist: [{', '.join(str(i) for i in invalid_ids)}]. "
                "Remove those issues or correct the IDs."
            )
            logger.warning("[%s] Invalid IDs on attempt %d: %s", persona.name, attempt, invalid_ids)
            continue
        if -1 in invalid_ids:
            continue

        logger.info("[%s] Analysis succeeded on attempt %d", persona.name, attempt)
        return PersonaAnalysis(
            personaId=persona.id,
            personaName=persona.name,
            viewport=viewport,
            reasoning=parsed.get("reasoning") or "Reasoning missing.",
            issues=[UXIssue.model_validate(i) for i in parsed.get("issues") or []],
            positives=parsed.get("positives") or [],
            overallScore=float(parsed.get("overallScore", 5)),
        )

    logger.error("[%s] Failed after %d retries", persona.name, max_retries)
    return PersonaAnalysis(
        personaId=persona.id,
        personaName=persona.name,
        viewport=viewport,
        reasoning="Analysis failed due to repeated validation errors.",
        issues=[],
        positives=[],
        overallScore=5.0,
    )


async def load_som_screenshot(job_dir: Path, viewport: Viewport) -> bytes:
    som_path = job_dir / f"som-{viewport}.png"
    if som_path.exists():
        return som_path.read_bytes()
    return (job_dir / f"{viewport}.png").read_bytes()
