"""Patient chart schema — structured clinical input from the physician."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Demographics(BaseModel):
    age: Optional[int] = None
    sex: Literal["M", "F", "other", "unknown"] = "unknown"
    pregnancy_status: Optional[bool] = None
    comorbidities: list[str] = Field(default_factory=list)


class VitalSigns(BaseModel):
    temperature_c: Optional[float] = None
    heart_rate_bpm: Optional[int] = None
    blood_pressure: Optional[str] = None   # "120/80"
    respiratory_rate: Optional[int] = None
    spo2_percent: Optional[float] = None


class PatientChart(BaseModel):
    demographics: Demographics = Field(default_factory=Demographics)
    chief_complaint: str = ""
    symptoms: list[str] = Field(default_factory=list)
    physical_findings: str = ""
    vital_signs: Optional[VitalSigns] = None
    lab_results: str = ""
    imaging: str = ""
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    additional_notes: str = ""
    language: Literal["en", "es"] = "en"

    def to_clinical_text(self) -> str:
        """Serialize chart to structured English text for NER and prompt injection."""
        lines: list[str] = []

        # Demographics
        demo = self.demographics
        demo_parts: list[str] = []
        if demo.age is not None:
            demo_parts.append(f"{demo.age}yo")
        if demo.sex in ("M", "F"):
            demo_parts.append(demo.sex)
        if demo.comorbidities:
            demo_parts.append("PMH: " + ", ".join(demo.comorbidities))
        if demo_parts:
            lines.append("## Demographics")
            lines.append(" | ".join(demo_parts))

        # Chief Complaint
        if self.chief_complaint:
            lines.append("## Chief Complaint")
            lines.append(self.chief_complaint)

        # Symptoms
        if self.symptoms:
            lines.append("## Symptoms")
            lines.append(", ".join(self.symptoms))

        # Physical Findings
        if self.physical_findings:
            lines.append("## Physical Findings")
            lines.append(self.physical_findings)

        # Vital Signs
        vs = self.vital_signs
        if vs:
            vs_parts: list[str] = []
            if vs.temperature_c is not None:
                vs_parts.append(f"T {vs.temperature_c}°C")
            if vs.heart_rate_bpm is not None:
                vs_parts.append(f"HR {vs.heart_rate_bpm}")
            if vs.blood_pressure:
                vs_parts.append(f"BP {vs.blood_pressure}")
            if vs.respiratory_rate is not None:
                vs_parts.append(f"RR {vs.respiratory_rate}")
            if vs.spo2_percent is not None:
                vs_parts.append(f"SpO2 {vs.spo2_percent}%")
            if vs_parts:
                lines.append("## Vital Signs")
                lines.append(", ".join(vs_parts))

        # Labs
        if self.lab_results:
            lines.append("## Lab Results")
            lines.append(self.lab_results)

        # Imaging
        if self.imaging:
            lines.append("## Imaging")
            lines.append(self.imaging)

        # Medications
        if self.current_medications:
            lines.append("## Current Medications")
            lines.append(", ".join(self.current_medications))

        # Allergies
        if self.allergies:
            lines.append("## Allergies")
            lines.append(", ".join(self.allergies))

        # Additional notes
        if self.additional_notes:
            lines.append("## Additional Notes")
            lines.append(self.additional_notes)

        return "\n".join(lines)

    @classmethod
    def from_free_text(cls, raw: str, language: Literal["en", "es"] = "en") -> "PatientChart":
        """Create a PatientChart from unstructured free text (goes into additional_notes)."""
        return cls(additional_notes=raw.strip(), language=language)

    def summary_for_prompt(self) -> str:
        """One-line summary for use in prompt context windows."""
        parts: list[str] = []
        if self.demographics.age:
            parts.append(f"{self.demographics.age}yo {self.demographics.sex}")
        if self.chief_complaint:
            parts.append(self.chief_complaint[:100])
        if self.demographics.comorbidities:
            parts.append("PMH: " + ", ".join(self.demographics.comorbidities[:3]))
        return " | ".join(parts) if parts else "No demographics provided"
