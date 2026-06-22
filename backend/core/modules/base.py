"""Protocol / ABC that every cancer-type diagnosis module must implement."""
from __future__ import annotations

import json as _json
import re as _re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.segmentation import SegmentationResult
    from models.schemas import DiagnosticReport


# A backslash that does NOT begin a valid JSON escape (\" \\ \/ \b \f \n \r \t \u).
# Local/markdown-tuned LLMs love to escape underscores/asterisks ("overall\_impression"),
# which is invalid JSON and makes json.loads choke on otherwise-perfect output.
_BAD_ESCAPE = _re.compile(r'\\([^"\\/bfnrtu])')

# A comma immediately before a closing } or ] (trailing comma) — invalid JSON.
_TRAILING_COMMA = _re.compile(r',(\s*[}\]])')


def _strip_json_comments(s: str) -> str:
    """Remove // line and /* */ block comments that local LLMs inject into JSON,
    without touching '//' that appears inside string values (e.g. URLs). Scans
    character by character tracking double-quoted string state."""
    out: list[str] = []
    i, n, in_str = 0, len(s), False
    while i < n:
        c = s[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:        # keep escaped char verbatim
                out.append(s[i + 1]); i += 2; continue
            if c == '"':
                in_str = False
            i += 1; continue
        if c == '"':
            in_str = True; out.append(c); i += 1; continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":       # // line comment
            i += 2
            while i < n and s[i] not in "\r\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":       # /* block comment */
            i += 2
            while i + 1 < n and not (s[i] == "*" and s[i + 1] == "/"):
                i += 1
            i += 2; continue
        out.append(c); i += 1
    return "".join(out)


def _repair_json(s: str) -> str:
    """Apply every known local-LLM JSON repair: strip comments, drop trailing
    commas, then unescape markdown-escaped punctuation."""
    s = _strip_json_comments(s)
    s = _TRAILING_COMMA.sub(r"\1", s)
    return _BAD_ESCAPE.sub(r"\1", s)


def coerce_json(raw: str) -> Optional[dict]:
    """Best-effort recovery of a JSON object from an LLM reply.

    Handles the common local-LLM failure modes seen in practice:
      • ```json … ``` markdown fences,
      • markdown-escaped punctuation (\\_ , \\* , \\-) that is invalid JSON,
      • // line and /* */ block comments injected into the object,
      • trailing commas before } or ],
      • leading/trailing prose around the object.
    Returns the parsed dict, or None if nothing usable could be recovered.
    """
    if not raw:
        return None
    s = raw.strip()
    for fence in ("```json", "```"):
        if s.startswith(fence):
            s = s[len(fence):]
            if "```" in s:
                s = s[: s.index("```")]
            break
    s = s.strip()

    # Try the raw string and a fully-repaired copy, plus the {...} brace-slice of
    # each (repairs can shift where the outermost braces land).
    bases = [s, _repair_json(s)]
    for b in (s, _repair_json(s)):
        if "{" in b and "}" in b:
            bases.append(b[b.index("{"): b.rindex("}") + 1])

    for cand in bases:
        for attempt in (cand, _repair_json(cand)):
            try:
                data = _json.loads(attempt)
            except _json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
    return None


@dataclass
class SegmentationSpec:
    organ_roi: list[str]              # TotalSegmentator ROI names for organ seg
    lesion_task: Optional[str]        # named TotalSegmentator task, e.g. "liver_lesions"
    tumor_mask_names: list[str] = field(default_factory=list)  # output filenames to look for


# ── Shared structured-differential helpers (used by every cancer module) ───────
# Each candidate diagnosis carries explicit FOR / AGAINST evidence (pros/cons) and
# a likelihood, so the report is verifiable rather than an unranked name list.

DIFFERENTIAL_INSTRUCTIONS = (
    "PRECISION REQUIREMENTS for the differential — be specific, not vague:\n"
    "• Build a RANKED differential (most likely first, 2–4 candidates). For EACH candidate, "
    "give the evidence FOR it (\"supporting_features\") and AGAINST it (\"opposing_features\").\n"
    "• Cite ONLY findings actually present in the image(s) or the quantitative analysis above — "
    "do NOT invent findings. If there is no opposing evidence, write [\"none significant\"].\n"
    "• Set \"likelihood\" to \"high\" / \"moderate\" / \"low\", consistent with the imaging "
    "findings and any quantitative scores/probabilities provided above."
)

# JSON snippet inserted into a module prompt via a plain {DIFFERENTIAL_JSON} field.
# Braces here are LITERAL (the host f-string interpolates this whole string), so do
# not double them.
DIFFERENTIAL_JSON = (
    '  "differential_assessment": [\n'
    '    {\n'
    '      "diagnosis": "Most likely diagnosis",\n'
    '      "likelihood": "high",\n'
    '      "supporting_features": ["a specific finding that argues FOR this diagnosis"],\n'
    '      "opposing_features": ["a finding that argues AGAINST it, or \\"none significant\\""]\n'
    '    },\n'
    '    {\n'
    '      "diagnosis": "Next most likely alternative",\n'
    '      "likelihood": "low",\n'
    '      "supporting_features": ["..."],\n'
    '      "opposing_features": ["..."]\n'
    '    }\n'
    '  ],'
)


def parse_differential(data: dict):
    """Parse `differential_assessment` into List[DifferentialItem] and a flat
    `differential_diagnosis` (derived from the structured form when the model only
    returned the structured one). Returns (items, flat_list)."""
    from models.schemas import DifferentialItem

    items = []
    for item in data.get("differential_assessment", []):
        if not isinstance(item, dict) or not item.get("diagnosis"):
            continue
        lk = item.get("likelihood")
        lk = str(lk).lower().strip() if lk is not None else None
        if lk not in (None, "high", "moderate", "low"):
            lk = None
        items.append(DifferentialItem(
            diagnosis=str(item.get("diagnosis")),
            likelihood=lk,
            supporting_features=[str(f) for f in item.get("supporting_features", []) if f],
            opposing_features=[str(f) for f in item.get("opposing_features", []) if f],
        ))

    flat = data.get("differential_diagnosis", [])
    if not flat and items:
        flat = [d.diagnosis + (f" ({d.likelihood})" if d.likelihood else "") for d in items]
    return items, flat


class DiagnosisModule(ABC):
    cancer_type: str   # e.g. "liver" | "skin" | "lung" | "breast" | "colorectal"
    display_name: str  # human label
    pipeline: str      # "volumetric" | "image"

    def segmentation_spec(self) -> Optional[SegmentationSpec]:
        return None

    def rag_namespace(self) -> str:
        return self.cancer_type

    def rag_query(self, seg: SegmentationResult, modality: str) -> str:
        return f"{self.cancer_type} cancer imaging {modality} diagnosis assessment guidelines"

    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def build_prompt(
        self,
        seg: SegmentationResult,
        modality: str,
        rag_context: str,
        radiomics_summary: str,
        patient_info: Optional[dict],
    ) -> str: ...

    @abstractmethod
    def parse_report(
        self,
        raw: str,
        modality: str,
        rag_used: bool,
        radiomics_summary: str,
    ) -> DiagnosticReport: ...
