# 🏛️ SENTINEL

> **"Where Code Meets Law."** > Transforming 100 pages of unstructured trade regulations into actionable, mapped JSON data.

An open-source AI concept prototype built for the **UN Global Hackathon: AI for Digital Trade Regulatory Analysis**.

## 🎯 The Mission
Global digital trade is hindered by fragmented data localization and privacy laws. Traditional manual legal review is no longer scalable. **SENTINEL** is a hybrid extraction engine designed to automatically discover, extract, and map complex digital trade regulations against all 12 pillars of the **UNESCAP Regional Digital Trade Integration Index (RDTII 2.1)**.

## ⚙️ Hybrid Architecture (The Engine)
To eliminate LLM "hallucinations" in legal contexts, we employ a deterministic + probabilistic hybrid approach:
1. **Deterministic Anchoring:** Regex & Python to precisely slice legal PDFs by articles/clauses.
2. **Semantic Extraction:** NLP/LLM API to extract specific compliance obligations.
3. **Structured Mapping:** Pydantic & JSON Schema to force LLM outputs into strict RDTII-compliant data structures.
4. **Transparency UI (Audit View):** React frontend linking JSON outputs directly to highlighted source text in the original PDF.

## 👥 The Squad
We are a cross-disciplinary strike team from Maynooth University:
- **Dong** (Tech Leader & Architect): Orchestrated the foundational system framework and end-to-end development workflow, providing critical cross-disciplinary guidance bridging legal compliance and technical execution.
- **Katie** (Legal Leader): A legal scholar with native-level proficiency in both English and Chinese. Serves as the ultimate legal authority, directing regulatory logic, resolving linguistic conflicts, and ensuring PDPA compliance.
- **Chenming** (Full-Stack & AI Engineer): Spearheaded the stunning frontend UI design, while deeply integrating the RAG pipeline, LLM interactions, and PostgreSQL database workflows.
- **Abel** (Backend Engineer): Lead developer for the robust backend infrastructure, building the core Python extraction pipelines and anti-bot crawler engine.
- **Rujing** (Project Coordinator): Manages cross-functional liaison, external communications, and technical documentation, ensuring seamless project execution.

---
*Disclaimer: The outputs of this tool are for conceptual demonstration and research purposes only, not formal legal advice.*

