"""Vertex AI provider — calls Vertex AI REST API with service account credentials.

Uses google-auth + httpx (transitive deps of google-generativeai, no extra install).
"""

from __future__ import annotations

import os
import time
from typing import Any

import google.auth.transport.requests
import httpx
from google.oauth2 import service_account

from .base import ExtractionError, ExtractionUsage, LLMProvider

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class VertexAIProvider(LLMProvider):
    name = "vertex-ai"

    def __init__(self, model_name: str | None = None):
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        if not cred_path or not os.path.exists(cred_path):
            raise ExtractionError(
                "GOOGLE_APPLICATION_CREDENTIALS is not set or file not found"
            )
        self._credentials = service_account.Credentials.from_service_account_file(
            cred_path, scopes=_SCOPES
        )
        self.project = os.getenv("GOOGLE_CLOUD_PROJECT") or self._credentials.project_id or ""
        if not self.project:
            raise ExtractionError("GOOGLE_CLOUD_PROJECT is not set")
        self.location = os.getenv("VERTEX_LOCATION", "us-central1")
        self.model_name = model_name or os.getenv("VERTEX_MODEL", "gemini-2.5-flash")
        self.name = self.model_name

    # ── Private helpers ──────────────────────────────────────────

    def _refresh_token(self) -> str:
        auth_req = google.auth.transport.requests.Request()
        self._credentials.refresh(auth_req)
        return self._credentials.token

    @staticmethod
    def _base_url(location: str) -> str:
        if location == "global":
            return "https://aiplatform.googleapis.com/"
        return f"https://{location}-aiplatform.googleapis.com/"

    def _request(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0,
        max_tokens: int = 8192,
    ) -> dict[str, Any]:
        token = self._refresh_token()
        url = (
            f"{self._base_url(self.location)}v1beta1/"
            f"projects/{self.project}/locations/{self.location}/"
            f"publishers/google/models/{self.model_name}:generateContent"
        )
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=120,
        )
        if resp.status_code != 200:
            raise ExtractionError(
                f"Vertex AI API error ({resp.status_code}): {resp.text}"
            )
        return resp.json()

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> str:
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return parts[0].get("text", "") if parts else ""

    # ── LLMProvider interface ────────────────────────────────────

    def query(self, prompt: str, system: str = "") -> str:
        usage = ExtractionUsage()
        t0 = time.perf_counter()
        try:
            data = self._request(prompt, system=system)
        except Exception as e:
            raise ExtractionError(f"Vertex AI query failed: {e}") from e
        finally:
            usage.latency_ms = int((time.perf_counter() - t0) * 1000)

        raw = self._parse_response(data)
        meta = data.get("usageMetadata", {})
        usage.input_tokens = meta.get("promptTokenCount", 0)
        usage.output_tokens = meta.get("candidatesTokenCount", 0)
        usage.cost_usd = self.estimate_cost_usd(usage.input_tokens, usage.output_tokens)
        usage.raw_response = raw
        self.last_usage = usage
        return raw

    def extract_features(
        self,
        article_text: str,
        indicator_id: str,
        feature_spec: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        prompt = self.build_prompt(article_text, indicator_id, feature_spec)
        usage = ExtractionUsage()
        t0 = time.perf_counter()
        try:
            data = self._request(
                prompt,
                system="Output ONLY valid JSON. No prose, no markdown fences.",
            )
        except Exception as e:
            raise ExtractionError(f"Vertex AI extract failed: {e}") from e
        finally:
            usage.latency_ms = int((time.perf_counter() - t0) * 1000)

        raw = self._parse_response(data)
        usage.raw_response = raw
        meta = data.get("usageMetadata", {})
        usage.input_tokens = meta.get("promptTokenCount", 0)
        usage.output_tokens = meta.get("candidatesTokenCount", 0)
        usage.cost_usd = self.estimate_cost_usd(usage.input_tokens, usage.output_tokens)
        self.last_usage = usage
        return self.parse_json_response(raw)

    def estimate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0  # Vertex AI billing varies by contract; omit to keep simple.
