"""ChartFileParser — extracts a PatientChart from an uploaded PDF or TXT file.

Reuses SimplePdfExtractor (adapters/scraping/pdf_extractor.py) for PDF text
extraction, then applies regex heuristics to detect common clinical note
sections (Chief Complaint, HPI, Vitals, Labs, etc.).

If no sections are matched (scanned PDF with no selectable text, or
non-standard format), the raw text goes entirely into additional_notes and
extraction_failed is set to True so the API can warn the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from sri_dx.adapters.scraping.pdf_extractor import SimplePdfExtractor
from sri_dx.core.schemas.rag.patient_chart import (
    Demographics,
    PatientChart,
    VitalSigns,
)


# ---------------------------------------------------------------------------
# Section patterns — ordered by priority; each pattern captures the header
# and everything until the next header or end of text.
# ---------------------------------------------------------------------------

_SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("chief_complaint", re.compile(
        r"(?:chief\s+complaint|cc)\s*[:\-]\s*(.+?)(?=\n##|\n[A-Z][A-Za-z\s/]{2,20}[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )),
    ("hpi", re.compile(
        r"(?:history\s+of\s+present\s+illness|hpi|presenting\s+complaint)\s*[:\-]\s*(.+?)(?=\n##|\n[A-Z][A-Za-z\s/]{2,20}[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )),
    ("vitals", re.compile(
        r"(?:vital\s+signs?|vitals?)\s*[:\-]\s*(.+?)(?=\n##|\n[A-Z][A-Za-z\s/]{2,20}[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )),
    ("physical_exam", re.compile(
        r"(?:physical\s+exam(?:ination)?|pe|exam(?:ination)?)\s*[:\-]\s*(.+?)(?=\n##|\n[A-Z][A-Za-z\s/]{2,20}[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )),
    ("labs", re.compile(
        r"(?:lab(?:oratory)?\s+results?|labs?|laboratory)\s*[:\-]\s*(.+?)(?=\n##|\n[A-Z][A-Za-z\s/]{2,20}[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )),
    ("imaging", re.compile(
        r"(?:imaging|radiology|x-ray|ct\s+scan|mri|echo(?:cardiogr(?:am|aphy))?)\s*[:\-]\s*(.+?)(?=\n##|\n[A-Z][A-Za-z\s/]{2,20}[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )),
    ("medications", re.compile(
        r"(?:current\s+med(?:ication)?s?|medications?|meds?)\s*[:\-]\s*(.+?)(?=\n##|\n[A-Z][A-Za-z\s/]{2,20}[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )),
    ("allergies", re.compile(
        r"(?:allerg(?:ies|y)|nkda|drug\s+allerg(?:ies|y))\s*[:\-]?\s*(.+?)(?=\n##|\n[A-Z][A-Za-z\s/]{2,20}[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )),
    ("pmh", re.compile(
        r"(?:past\s+medical\s+hist(?:ory)?|pmh|medical\s+hist(?:ory)?)\s*[:\-]\s*(.+?)(?=\n##|\n[A-Z][A-Za-z\s/]{2,20}[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )),
]

# Vital-sign sub-patterns
_VS_PATTERNS = {
    "hr": re.compile(r"(?:hr|heart\s+rate|pulse)\s*[:\s]*(\d{2,3})", re.IGNORECASE),
    "bp": re.compile(r"(?:bp|blood\s+pressure)\s*[:\s]*(\d{2,3}/\d{2,3})", re.IGNORECASE),
    "rr": re.compile(r"(?:rr|resp(?:iratory)?\s+rate|respirations?)\s*[:\s]*(\d{1,2})", re.IGNORECASE),
    "spo2": re.compile(r"(?:spo2|o2\s*sat|oxygen\s+sat(?:uration)?)\s*[:\s]*(\d{2,3}(?:\.\d)?)\s*%?", re.IGNORECASE),
    "temp": re.compile(r"(?:temp(?:erature)?|t)\s*[:\s]*(\d{2,3}(?:\.\d{1,2})?)\s*°?[CF]?", re.IGNORECASE),
}

# Age / sex quick heuristic (for HPI narrative like "58yo M" or "58-year-old female")
_AGE_SEX = re.compile(
    r"\b(\d{1,3})\s*(?:yo|y/?o|-year-old|-yr-old)\s*(m(?:ale)?|f(?:emale)?|man|woman|boy|girl)\b",
    re.IGNORECASE,
)


@dataclass
class ParseResult:
    chart: PatientChart
    extraction_failed: bool   # True when no text could be extracted (scanned PDF)
    raw_text: str


class ChartFileParser:
    """Parse a PDF or TXT file uploaded by the physician into a PatientChart."""

    _pdf_extractor = SimplePdfExtractor()

    def parse_bytes(self, data: bytes, filename: str) -> ParseResult:
        """
        Entry point. Returns a ParseResult with a PatientChart pre-filled from
        whatever sections could be detected, plus a flag when text extraction
        failed entirely (scanned PDF without selectable text).
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext == "pdf":
            raw_text = self._extract_pdf_text(data)
        else:
            raw_text = self._decode_txt(data)

        if not raw_text.strip():
            return ParseResult(
                chart=PatientChart(),
                extraction_failed=True,
                raw_text="",
            )

        sections = self._extract_sections(raw_text)
        chart = self._to_chart(sections, raw_text)
        extraction_failed = not any(sections.values())
        return ParseResult(chart=chart, extraction_failed=extraction_failed, raw_text=raw_text)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_pdf_text(self, data: bytes) -> str:
        try:
            _title, _sections, body, _meta = self._pdf_extractor.extract("upload", data)
            return body or ""
        except Exception:
            return ""

    @staticmethod
    def _decode_txt(data: bytes) -> str:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    def _extract_sections(self, text: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        for key, pattern in _SECTION_PATTERNS:
            m = pattern.search(text)
            if m:
                sections[key] = m.group(1).strip()
        return sections

    def _to_chart(self, sections: dict[str, str], raw_text: str) -> PatientChart:
        # Chief complaint: prefer CC section, fall back to first line of HPI
        chief_complaint = sections.get("chief_complaint", "")
        if not chief_complaint and sections.get("hpi"):
            first_line = sections["hpi"].split("\n")[0].strip()
            chief_complaint = first_line[:200]

        # Symptoms: split CC + HPI by comma/semicolon/newline into list
        symptom_src = " ".join(filter(None, [
            sections.get("chief_complaint", ""),
            sections.get("hpi", ""),
        ]))
        symptoms = [
            s.strip().lower()
            for s in re.split(r"[,;\n]", symptom_src)
            if s.strip() and len(s.strip()) > 2
        ][:20]  # cap at 20 to keep prompt tight

        # Vital signs
        vitals_text = sections.get("vitals", raw_text)  # fall back to full text for VS
        vital_signs = self._parse_vitals(vitals_text)

        # Demographics: try to detect age/sex from HPI or full text
        demographics = self._parse_demographics(
            sections.get("hpi", "") or sections.get("chief_complaint", "") or raw_text[:500],
            sections.get("pmh", ""),
        )

        # Medications: split by newline or comma
        meds_raw = sections.get("medications", "")
        medications = [
            m.strip()
            for m in re.split(r"[,\n;]", meds_raw)
            if m.strip() and len(m.strip()) > 2
        ] if meds_raw else []

        # Allergies
        allergy_raw = sections.get("allergies", "")
        if allergy_raw.upper().strip() in ("NKDA", "NONE", "NO KNOWN ALLERGIES", "NKA"):
            allergies: list[str] = []
        else:
            allergies = [
                a.strip()
                for a in re.split(r"[,\n;]", allergy_raw)
                if a.strip() and len(a.strip()) > 1
            ]

        # Unmatched text goes to additional_notes only when nothing was detected
        additional_notes = ""
        if not any(sections.values()):
            additional_notes = raw_text.strip()

        return PatientChart(
            demographics=demographics,
            chief_complaint=chief_complaint,
            symptoms=symptoms,
            physical_findings=sections.get("physical_exam", ""),
            vital_signs=vital_signs,
            lab_results=sections.get("labs", ""),
            imaging=sections.get("imaging", ""),
            current_medications=medications,
            allergies=allergies,
            additional_notes=additional_notes,
        )

    @staticmethod
    def _parse_vitals(text: str) -> Optional[VitalSigns]:
        hr = bp = rr = spo2 = temp = None

        m = _VS_PATTERNS["hr"].search(text)
        if m:
            hr = int(m.group(1))

        m = _VS_PATTERNS["bp"].search(text)
        if m:
            bp = m.group(1)

        m = _VS_PATTERNS["rr"].search(text)
        if m:
            rr = int(m.group(1))

        m = _VS_PATTERNS["spo2"].search(text)
        if m:
            val = float(m.group(1))
            spo2 = val if val <= 100 else None

        m = _VS_PATTERNS["temp"].search(text)
        if m:
            val = float(m.group(1))
            # Sanity: body temp range 30–43°C or 86–110°F
            if 30 <= val <= 43:
                temp = val
            elif 86 <= val <= 110:
                temp = round((val - 32) * 5 / 9, 1)  # convert F→C

        if any(v is not None for v in (hr, bp, rr, spo2, temp)):
            return VitalSigns(
                heart_rate_bpm=hr,
                blood_pressure=bp,
                respiratory_rate=rr,
                spo2_percent=spo2,
                temperature_c=temp,
            )
        return None

    @staticmethod
    def _parse_demographics(narrative: str, pmh_text: str) -> Demographics:
        age: Optional[int] = None
        sex: str = "unknown"

        m = _AGE_SEX.search(narrative)
        if m:
            age = int(m.group(1))
            sex_raw = m.group(2).lower()
            if sex_raw in ("m", "male", "man", "boy"):
                sex = "M"
            elif sex_raw in ("f", "female", "woman", "girl"):
                sex = "F"

        # Comorbidities from PMH section — split by comma/newline
        comorbidities = [
            c.strip()
            for c in re.split(r"[,\n;]", pmh_text)
            if c.strip() and len(c.strip()) > 1
        ] if pmh_text else []

        return Demographics(age=age, sex=sex, comorbidities=comorbidities)  # type: ignore[arg-type]
