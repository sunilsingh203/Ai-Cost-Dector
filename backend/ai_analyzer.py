import json
import os
from typing import Any

import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError


class AIAnalyzerError(Exception):
    pass


class Issue(BaseModel):
    resource_name: str
    resource_type: str
    issue_type: str = Field(
        description="e.g. over-provisioned, unused, misconfigured, wrong-tier"
    )
    severity: str = Field(description="high, medium, or low")
    explanation: str
    fix_command: str | None = None


class AnalysisResult(BaseModel):
    summary: str
    issues: list[Issue]
    estimated_savings: str


def _build_prompt(resource_group: str, resources: list[dict[str, Any]]) -> str:
    resources_json = json.dumps(resources, separators=(",", ":"))
    return f"""You are an Azure cloud cost optimization expert. Analyze these Azure resources
from resource group \"{resource_group}\".

Return JSON with this exact structure:
{{
  "summary": "Brief overall assessment of cost health",
  "issues": [
    {{
      "resource_name": "name of the Azure resource",
      "resource_type": "Azure resource type",
      "issue_type": "over-provisioned | unused | misconfigured | wrong-tier | other",
      "severity": "high | medium | low",
      "explanation": "Why this is a cost concern",
      "fix_command": "Azure CLI command or null"
    }}
  ],
  "estimated_savings": "Rough monthly savings estimate, e.g. '$50-100/month' or 'Minimal savings expected'"
}}

If there are no issues, return an empty issues array and a summary.
Do not invent resources not in the list.

Resources: {resources_json}"""


def analyze_resources(
    resource_group: str, resources: list[dict[str, Any]]
) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise AIAnalyzerError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    try:
        response = model.generate_content(
            _build_prompt(resource_group, resources),
            generation_config=genai.GenerationConfig(
                temperature=0.2,
            ),
        )
    except Exception as exc:
        raise AIAnalyzerError(f"Gemini API request failed: {exc}") from exc

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise AIAnalyzerError("Gemini returned an empty response.")

    try:
        parsed = json.loads(raw_text)
        result = AnalysisResult.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AIAnalyzerError(
            f"Failed to parse Gemini analysis response: {exc}"
        ) from exc

    return result.model_dump()
