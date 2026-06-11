# RDTII AI Mapper — Architecture

## What This System Does

UN ESCAP RDTII 2.1 AI Mapper — extracts structured policy indicator mappings from legal texts (PDFs, URLs) and scores them against the Regional Digital Trade Integration Index 2.1 framework (12 pillars, ~50+ indicators).

---

## Current Pipeline (Single-Agent)

```
Crawl URL / upload PDF   →  crawler.py             (Playwright + stealth)
Extract text             →  pdf_reader/__init__.py  (per-page PyMuPDF + Tesseract/OpenAI OCR)
Chunk                    →  chunker.py              (regex_legal_chunker)
Classify indicators      →  classifier.py           (keyword array matching — anti-hallucination layer)
Extract features         →  providers/              (LLM call per chunk × indicator)
Verify                   →  verification.py         (verbatim_quote substring check)
Score                    →  scoring/                (deterministic Python per pillar)
```

### Provider Abstraction (`ai-service/providers/`)

| File | Role |
|---|---|
| `base.py` | `LLMProvider` ABC — `extract_features()`, `extract_batch()`, `build_prompt()`, `parse_json_response()` |
| `__init__.py` | Lazy registry: gemini, claude, llama-3-local, openai, deepseek, groq, together, openrouter, mistral |
| `llama_local.py` | llama-cpp-python (loads GGUF files directly — NOT Ollama) |
| `openai_compatible.py` | OpenAI-API compatible endpoint (Ollama will slot in here) |

**Key env vars:** `RDTII_LLM_PROVIDER`, `LLAMA_MODEL_PATH`, `EXTRACT_SIDECAR_URL`, `SIDECAR_API_KEY`

### Extract Sidecar (`extract_sidecar/`)

Rust service with SHA-256 cache for file extraction. FastAPI calls `POST /extract-text` and falls back to local `pdf_reader` if `EXTRACT_SIDECAR_URL` is not set.

---

## Why We're Moving to MAS

Two problems with the current single-agent design:

1. **Structural mismatch** — the system produces a flat JSON of features, but RDTII 2.1 requires a 10-field research entry *per Act per indicator*. Singapore indicator 6.1 alone maps to 4 separate Acts. Current system collapses them into one.

2. **Model switch** — teammates are training a 12B Ollama model fine-tuned on RDTII 2.1 data. A proper agent layer is needed to host it alongside cloud providers.

---

## Target Output Schema (RDTII 2.1 — 10 Fields)

Reference dataset: `[5th June] Dataset- RDTII 2.1 data collection practice assignment.xlsx`
Example entries: Singapore indicator 6.1, Malaysia indicator 7.3, India indicator 5.3

| # | Field | Description |
|---|---|---|
| 1 | Pillar_ID | e.g. `6.0` |
| 2 | Indicator_ID | e.g. `6.1` |
| 3 | Cat_Score | Sum of raw scores, capped at 1 |
| 4 | Raw Score | `0` / `0.5` / `1` per exact scoring criteria |
| 5 | Act and/or practice | Title of the regulation/law |
| 6 | Coverage | `"Horizontal"` or specific sector name |
| 7 | Impact or comments | Multi-paragraph legal analysis explaining the score |
| 8 | Timeframe | Enactment + amendment dates |
| 9 | References | Primary source URLs (official gov) + secondary sources |
| 10 | Note | Internal researcher notes |

**First concrete step:** Update `ai-service/schemas.py` `IndicatorMapping` to reflect these 10 fields before any agent work begins.

---

## New MAS Architecture

### Agent Map

```
Chunk
  └─► [Classifier]          existing keyword router — keep as-is
        └─► [Extractor Agent]    finds Act titles + verbatim quotes  ← 12B Ollama
              └─► [Analyst Agent]     writes Impact/Comments field
                    └─► [Scorer Agent]      applies scoring criteria → Raw Score  ← deterministic Python
                          └─► [Verifier Agent]   checks quote is real substring, URLs exist
```

### Agent vs Provider Split

- `providers/` = model adapters ("how to talk to a model") — **keep as-is**
- `agents/` = role + system prompt + behavior ("what this model does") — **new layer**

These are different concerns. Mixing them is the mistake most MAS implementations make early.

### New Directory Structure

```
ai-service/agents/
  base.py          # Agent ABC: role, system_prompt, provider: LLMProvider, async run()
  extractor.py     # promotes current _run_extraction logic
  critic.py        # evidence quality verification
  orchestrator.py  # async coordinator — build LAST (needs 2+ agents first)
```

---

## Ollama Integration

Teammates' 12B model is served via Ollama (OpenAI-compatible REST API at `http://localhost:11434/v1`).

**Approach:** Add `OllamaProvider` to `openai_compatible.py` with `base_url` pointing to the Ollama endpoint. Register as `"ollama"` in `_LAZY_REGISTRY` in `providers/__init__.py`.

```
OLLAMA_BASE_URL   (default: http://localhost:11434/v1)
OLLAMA_MODEL      (default: llama3)
```

Note: `llama_local.py` uses `llama-cpp-python` to load GGUF files directly — that is a different path from Ollama. Do not confuse them.

---

## Build Order

| Step | Task | Notes |
|---|---|---|
| 1 | `providers/ollama.py` | Unblock teammates — ~20 lines |
| 2 | `schemas.py` update | New 10-field `IndicatorMapping` |
| 3 | `agents/base.py` | `Agent` ABC |
| 4 | `agents/extractor.py` | Migrate `_run_extraction` |
| 5 | `agents/critic.py` | Evidence quality check |
| 6 | `agents/orchestrator.py` | Build last |
